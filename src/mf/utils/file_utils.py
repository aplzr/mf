from __future__ import annotations

import json
import os
import platform
import stat
import subprocess
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from fnmatch import fnmatch
from functools import partial
from importlib.resources import files
from operator import attrgetter
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from mf.constants import FD_BINARIES

from .config_utils import (
    get_validated_search_paths,
    parse_timedelta_str,
    read_config,
)
from .console import console, print_error, print_info, print_ok, print_warn
from .normalizers import normalize_pattern


def get_cache_dir() -> Path:
    """Return path to the cache directory.

    Platform aware with fallback to ~/.cache.

    Returns:
        Path: Cache directory.
    """
    cache_dir = (
        Path(
            os.environ.get(
                "LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME",
                Path.home() / ".cache",
            ),
        )
        / "mf"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)

    return cache_dir


def get_search_cache_file() -> Path:
    """Return path to the search cache file.

    Returns:
        Path: Location of the JSON search cache file.
    """
    return get_cache_dir() / "last_search.json"


def get_library_cache_file() -> Path:
    """Return path to the library cache file.

    Returns:
        Path: Location of the JSON library cache file.
    """
    return get_cache_dir() / "library.json"


def save_search_results(pattern: str, results: list[FileResult]) -> None:
    """Persist search results to cache.

    Args:
        pattern (str): Search pattern used.
        results (list[FileResult]): Search results.
    """
    cache_data = {
        "pattern": pattern,
        "timestamp": datetime.now().isoformat(),
        "results": [result.file.as_posix() for result in results],
    }

    cache_file = get_search_cache_file()

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)


def load_search_results() -> tuple[str, list[FileResult], datetime]:
    """Load cached search results.

    Raises:
        typer.Exit: If cache is missing or invalid.

    Returns:
        tuple[str, list[FileResult], datetime]: Pattern, results, timestamp.
    """
    cache_file = get_search_cache_file()
    try:
        with open(cache_file, encoding="utf-8") as f:
            cache_data = json.load(f)

        pattern = cache_data["pattern"]
        results = [FileResult(Path(path_str)) for path_str in cache_data["results"]]
        timestamp = datetime.fromisoformat(cache_data["timestamp"])

        return pattern, results, timestamp
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        print_error(
            "Cache is empty or doesn't exist. "
            "Please run 'mf find <pattern>' or 'mf new' first."
        )
        raise typer.Exit(1) from e


def print_search_results(title: str, results: list[FileResult]):
    """Render a table of search results.

    Args:
        title (str): Title displayed above table.
        results (list[FileResult]): Search results.
    """
    max_index_width = len(str(len(results))) if results else 1
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("#", style="cyan", width=max_index_width, justify="right")
    table.add_column("File", style="green", overflow="fold")
    table.add_column("Location", style="blue", overflow="fold")

    for idx, result in enumerate(results, start=1):
        table.add_row(str(idx), result.file.name, str(result.file.parent))

    panel = Panel(
        table, title=f"[bold]{title}[/bold]", title_align="left", padding=(1, 1)
    )
    console.print()
    console.print(panel)


def get_result_by_index(index: int) -> FileResult:
    """Retrieve result by index.

    Args:
        index (int): Index of desired file.

    Raises:
        typer.Exit: If index not found or file no longer exists.

    Returns:
        FileResult: File for the given index.
    """
    pattern, results, _ = load_search_results()

    try:
        result = results[index - 1]
    except IndexError as e:
        console.print(
            f"Index {index} not found in last search results (pattern: '{pattern}'). "
            f"Valid indices: 1-{len(results)}.",
            style="red",
        )
        raise typer.Exit(1) from e

    if not result.file.exists():
        print_error(f"File no longer exists: {result.file}.")

    return result


def load_library_cache() -> list[FileResult]:
    """Load cached library metadata. Rebuilds the cache if it has expired.

    Raises:
        typer.Exit: Cache empty or doesn't exist.

    Returns:
        list[FileResult]: Cached file paths.
    """
    if is_cache_expired():
        results = rebuild_library_cache()
    else:
        try:
            with open(get_library_cache_file(), encoding="utf-8") as f:
                cache_data = json.load(f)

            results = [FileResult(Path(path_str)) for path_str in cache_data["files"]]
        except (json.JSONDecodeError, KeyError):
            print_warn("Cache corrupted.")
            results = rebuild_library_cache()

    return results


def is_cache_expired() -> bool:
    """Check if the library cache is older than the configured cache interval.

    Args:
        cache_timestamp (datetime): Last cache timestamp.

    Returns:
        bool: True if cache has expired, False otherwise.
    """
    cache_file = get_library_cache_file()

    if not cache_file.exists():
        return True

    cache_timestamp = datetime.fromtimestamp(cache_file.stat().st_mtime)
    cache_interval = get_library_cache_interval()

    if cache_interval.total_seconds() == 0:
        # Cache set to never expire
        return False

    return datetime.now() - cache_timestamp > get_library_cache_interval()


def use_library_cache() -> bool:
    """Check if library cache is configured.

    Returns:
        bool: True if library cache should be used, False otherwise.
    """
    return read_config()["cache_library"]


def get_library_cache_interval() -> timedelta:
    """Get the library cache interval from the configuration.

    Returns:
        timedelta: Interval after which cache is rebuilt.
    """
    return parse_timedelta_str(read_config()["library_cache_interval"])


def get_fd_binary() -> Path:
    """Resolve path to packaged fd binary.

    Raises:
        RuntimeError: Unsupported platform / architecture.

    Returns:
        Path: Path to fd executable bundled with the package.
    """
    system = platform.system().lower()
    machine_raw = platform.machine().lower()

    # Normalize common architecture aliases
    if machine_raw in {"amd64", "x86-64", "x86_64"}:
        machine = "x86_64"
    elif machine_raw in {"arm64", "aarch64"}:
        machine = "arm64"
    else:
        machine = machine_raw

    binary_name = FD_BINARIES.get((system, machine))

    if not binary_name:
        raise RuntimeError(f"Unsupported platform: {system}-{machine}")

    bin_path = files("mf").joinpath("bin", binary_name)
    bin_path = Path(str(bin_path))

    if system in ("linux", "darwin"):
        current_perms = bin_path.stat().st_mode

        if not (current_perms & stat.S_IXUSR):
            bin_path.chmod(current_perms | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return bin_path


def filter_scan_results(
    results: list[FileResult],
    pattern: str,
    media_extensions: set[str],
    match_extensions: bool,
) -> list[FileResult]:
    """Filter search results.

    Args:
        results (list[FileResult]): Paths, optionally paired with
            mtimes.
        pattern (str): Glob pattern to match filenames against.
        media_extensions (set[str]): Media extensions to match against.
        match_extensions (bool): Whether to match media extensions or not.

    Returns:
        list[FileResult]: Filtered results.
    """
    if not results:
        return []

    # Filter by extension
    if match_extensions and media_extensions:
        results = [
            result
            for result in results
            if result.file.suffix.lower() in media_extensions
        ]

    # Filter by pattern
    if pattern != "*":
        results = [
            result
            for result in results
            if fnmatch(result.file.name.lower(), pattern.lower())
        ]

    return results


def sort_scan_results(results: list[FileResult]) -> list[FileResult]:
    """Sort combined results from all search paths.

    Sorts by modification time if it is available (FileResult.mtime is not None),
    otherwise alphabetically.

    Args:
        results (list[FileResult]): List of files, optionally paired with mtimes.

    Returns:
        list[FileResult]: Results sorted alphabetically or by mtime, depending on the
            input type.
    """
    if not results:
        return []

    if results[0].mtime:
        results.sort(key=attrgetter("mtime"), reverse=True)
    else:
        results.sort(key=lambda result: result.file.name.lower())

    return results


def scan_path_with_python(
    search_path: Path,
    include_mtime: bool = False,
) -> list[FileResult]:
    """Recursively scan a directory using Python.

    Args:
        search_path (Path): Root directory to scan.
        include_mtime (bool): Include modification time in results.

    Returns:
        list[FileResult]: All files in the search path, optionally paired with mtime.
    """
    results: list[FileResult] = []

    def scan_dir(path: str):
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file(follow_symlinks=False):
                        if include_mtime:
                            # mtime = entry.stat().st_mtime
                            # results.append((Path(entry.path), mtime))
                            results.append(
                                FileResult(Path(entry.path), entry.stat().st_mtime)
                            )
                        else:
                            # results.append(Path(entry.path))
                            results.append(FileResult(Path(entry.path)))
                    elif entry.is_dir(follow_symlinks=False):
                        scan_dir(entry.path)
        except PermissionError:
            print_warn(f"Missing access permissions for directory {path}, skipping.")

    scan_dir(str(search_path))
    return results


def scan_path_with_fd(
    search_path: Path,
) -> list[FileResult]:
    """Scan a directory using fd.

    Args:
        search_path (Path): Directory to scan.

    Raises:
        subprocess.CalledProcessError: If fd exits with non-zero status.

    Returns:
        list[FileResult]: All files in search path.
    """
    cmd = [
        str(get_fd_binary()),
        "--type",
        "f",
        "--absolute-path",
        "--hidden",
        ".",
        str(search_path),
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True, encoding="utf-8"
    )
    files: list[FileResult] = []

    for line in result.stdout.strip().split("\n"):
        if line:
            # files.append(Path(line))
            files.append(FileResult(Path(line)))

    return files


def scan_for_media_files(
    pattern: str, *, with_mtime: bool = False, prefer_fd: bool | None = None
) -> list[FileResult]:
    """Find media files by scanning all search paths.

    Args:
        pattern (str): Search pattern.
        with_mtime (bool): Add mtime info for later sorting by new (Python scan only).
        prefer_fd (bool): Prefer fd unless mtime sorting is requested. If None, value is
            read from the configuration file.

    Raises:
        RuntimeError: From fd resolution if platform unsupported.

    Returns:
        list[FileResult]: Results, optionally paired with mtimes.
    """
    cfg = read_config()
    pattern = normalize_pattern(pattern)
    search_paths = get_validated_search_paths()

    if prefer_fd is None:
        prefer_fd = cfg["prefer_fd"]

    use_fd = prefer_fd and not with_mtime

    with ThreadPoolExecutor(max_workers=len(search_paths)) as executor:
        if use_fd:
            try:
                path_results = list(executor.map(scan_path_with_fd, search_paths))
            except (
                FileNotFoundError,
                subprocess.CalledProcessError,
                OSError,
                PermissionError,
            ):
                # Do full scan with python scanner if fd fails for any reason
                partial_fd_scanner = partial(scan_path_with_python, include_mtime=False)
                path_results = list(executor.map(partial_fd_scanner, search_paths))
        else:
            partial_python_scanner = partial(
                scan_path_with_python, include_mtime=with_mtime
            )
            path_results = list(executor.map(partial_python_scanner, search_paths))

    all_results: list = []

    for res in path_results:
        all_results.extend(res)

    return all_results


def rebuild_library_cache() -> list[FileResult]:
    """Rebuild the local library cache.

    Builds an mtime-sorted index (descending / newest first) of all media files in the
    configured search paths.

    Returns:
        list[FileResult]: Rebuilt cache.
    """
    print_info("Rebuilding cache.")
    results = scan_for_media_files("*", with_mtime=True)
    results = sort_scan_results(results)
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "files": [result.file.as_posix() for result in results],
    }

    with open(get_library_cache_file(), "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)

    print_ok("Cache rebuilt.")
    return results


class Query(ABC):
    """Base class for file search queries."""

    def __init__(self):
        """Initialize query."""
        config = read_config()
        self.cache_library = config["cache_library"]
        self.prefer_fd = config["prefer_fd"]
        self.media_extensions = config["media_extensions"]
        self.match_extensions = config["match_extensions"]

    @abstractmethod
    def execute(self) -> list[Path]:
        """Execute the query.

        Returns:
            list[Path]: Search results.
        """
        ...


class FindQuery(Query):
    """Query for finding files matching a glob pattern, sorted alphabetically.

    This query searches for media files matching the specified pattern and returns
    results sorted by filename. Uses cached library data when configured /  available
    for better performance, otherwise performs a fresh filesystem scan.

    Attributes:
        pattern: Normalized glob pattern to search for.
    """

    def __init__(self, pattern: str):
        """Initialize the find query.

        Args:
            pattern (str): Glob pattern to search for (e.g., "*.mp4", "*2023*").
        """
        self.pattern = normalize_pattern(pattern)
        super().__init__()

    def execute(self) -> list[Path]:
        """Execute the query.

        Returns:
            list[Path]: Search results sorted alphabetically by filename.
        """
        if self.cache_library:
            files = load_library_cache()
        else:
            files = scan_for_media_files(self.pattern)

        files = filter_scan_results(
            files,
            self.pattern,
            self.media_extensions,
            self.match_extensions,
        )
        files = sort_scan_results(files)

        return files


class NewQuery(Query):
    """Query for finding the newest files in the collection, sorted by modification
    time.

    This query returns the most recently modified media files in the collection,
    regardless of filename or pattern. Uses cached library data when configured /
    available for better performance, otherwise performs a fresh filesystem scan with
    mtime collection.

    Attributes:
        pattern: Always "*" (searches all files).
        n: Maximum number of results to return.
    """

    pattern = "*"

    def __init__(self, n: int = 20):
        """Initialize the new files query.

        Args:
            n: Maximum number of newest files to return. Defaults to 20.
        """
        self.n = n
        super().__init__()

    def execute(self):
        """Execute the query.

        Returns:
            list[Path]: Up to n newest files, sorted by modification time (newest
            first).
        """
        if self.cache_library:
            # Already sorted by mtime
            files = load_library_cache()
        else:
            # Contains mtime but not sorted yet
            files = scan_for_media_files(self.pattern, with_mtime=True)
            files = sort_scan_results(files)

        files = filter_scan_results(
            files,
            self.pattern,
            self.media_extensions,
            self.match_extensions,
        )
        return files[: self.n]


@dataclass
class FileResult:
    """File search result.

    Attributes:
        file (Path): Filepath.
        mtime (float, optional): Optional last modification timestamp.
    """

    file: Path
    mtime: float | None = None
