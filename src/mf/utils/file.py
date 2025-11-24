from __future__ import annotations

import json
import os
import platform
import stat
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from collections import UserList
from collections.abc import Callable
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
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from ..constants import FD_BINARIES
from .config import (
    get_validated_search_paths,
    parse_timedelta_str,
    read_config,
)
from .console import (
    STATUS_SYMBOLS,
    console,
    print_error,
    print_info,
    print_ok,
    print_warn,
)
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


def save_last_played(result: FileResult):
    """Save which file was played last to the cached search results file.

    Args:
        result (FileResult): File last played.
    """
    with open(get_search_cache_file(), encoding="utf-8") as f:
        cached = json.load(f)

    last_search_results: list[str] = cached["results"]
    last_played_index = last_search_results.index(str(result))
    cached["last_played_index"] = last_played_index

    with open(get_search_cache_file(), "w", encoding="utf-8") as f:
        json.dump(cached, f, indent=2)


def get_last_played_index() -> int | None:
    """Get the search result index of the last played file.

    Returns:
        int | None: Index or None if no file was played.
    """
    with open(get_search_cache_file(), encoding="utf-8") as f:
        cached = json.load(f)

    try:
        return int(cached["last_played_index"])
    except KeyError:
        return None


def get_next() -> FileResult:
    """Get the next file to play.

    Returns:
        FileResult: Next file to play.
    """
    with open(get_search_cache_file(), encoding="utf-8") as f:
        cached = json.load(f)

    results: list[str] = cached["results"]

    try:
        index_last_played = int(cached["last_played_index"])
    except KeyError:
        # Nothing played yet, start at the beginning
        index_last_played = -1

    try:
        next = FileResult.from_string(results[index_last_played + 1])
        return next
    except IndexError:
        print_error("Last available file already played.")


def save_search_results(pattern: str, results: FileResults) -> None:
    """Persist search results to cache.

    Args:
        pattern (str): Search pattern used.
        results (FileResults): Search results.
    """
    cache_data = {
        "pattern": pattern,
        "timestamp": datetime.now().isoformat(),
        "results": [str(result) for result in results],
    }

    cache_file = get_search_cache_file()

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)


def load_search_results() -> tuple[str, FileResults, datetime]:
    """Load cached search results.

    Raises:
        typer.Exit: If cache is missing or invalid.

    Returns:
        tuple[str, FileResults, datetime]: Pattern, results, timestamp.
    """
    cache_file = get_search_cache_file()
    try:
        with open(cache_file, encoding="utf-8") as f:
            cache_data = json.load(f)

        pattern = cache_data["pattern"]
        results = FileResults.from_paths(cache_data["results"])
        timestamp = datetime.fromisoformat(cache_data["timestamp"])

        return pattern, results, timestamp
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        print_error(
            "Cache is empty or doesn't exist. "
            "Please run 'mf find <pattern>' or 'mf new' first."
        )
        raise typer.Exit(1) from e


def print_search_results(title: str, results: FileResults):
    """Render a table of search results.

    Args:
        title (str): Title displayed above table.
        results (FileResults): Search results.
    """
    max_index_width = len(str(len(results))) if results else 1
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("#", style="cyan", width=max_index_width, justify="right")
    table.add_column("File", style="green", overflow="fold")
    table.add_column("Location", style="blue", overflow="fold")

    last_played_index = get_last_played_index()

    for idx, result in enumerate(results):
        is_last_played = idx == last_played_index

        if is_last_played:
            # Highlight last played file in the search results
            table.add_row(
                f"[bright_cyan]{str(idx + 1)}[/bright_cyan]",
                f"[bright_cyan]{result.file.name}[/bright_cyan]",
                str(result.file.parent),
            )
        else:
            table.add_row(str(idx + 1), result.file.name, str(result.file.parent))

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


def _load_library_cache(allow_rebuild=True) -> FileResults:
    """Load cached library metadata. Rebuilds the cache if it is corrupted and
    rebuilding is allowed.

    Returns [] if cache is corrupted and rebuilding is not allowed.

    Args:
        allow_rebuild (bool, optional): Allow cache rebuilding. Defaults to True.

    Returns:
        FileResults: Cached file paths.
    """
    try:
        with open(get_library_cache_file(), encoding="utf-8") as f:
            cache_data = json.load(f)

        results = FileResults(
            [FileResult(Path(path_str)) for path_str in cache_data["files"]]
        )
    except (json.JSONDecodeError, KeyError):
        print_warn("Cache corrupted.")

        results = rebuild_library_cache() if allow_rebuild else []

    return results


def load_library_cache() -> FileResults:
    """Load cached library metadata. Rebuilds the cache if it has expired or is
    corrupted.

    Raises:
        typer.Exit: Cache empty or doesn't exist.

    Returns:
        FileResults: Cached file paths.
    """
    return rebuild_library_cache() if is_cache_expired() else _load_library_cache()


def get_library_cache_size() -> int:
    """Get the size of the library cache.

    Returns:
        int: Number of cached file paths.
    """
    return len(_load_library_cache(allow_rebuild=False))


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

    return datetime.now() - cache_timestamp > cache_interval


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


def scan_path_with_python(
    search_path: Path,
    with_mtime: bool = False,
    progress_callback: Callable[[FileResult], None] | None = None,
) -> FileResults:
    """Recursively scan a directory using Python.

    Args:
        search_path (Path): Root directory to scan.
        with_mtime (bool): Include modification time in results.
        progress_callback (Callable[[FileResult], None] | None): Called for each file
            found (optional, defaults to None).

    Returns:
        FileResults: All files in the search path, optionally paired with mtime.
    """
    results = FileResults()

    def scan_dir(path: str):
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file(follow_symlinks=False):
                        if with_mtime:
                            file_result = FileResult(
                                Path(entry.path), entry.stat().st_mtime
                            )
                        else:
                            file_result = FileResult(Path(entry.path))

                        results.append(file_result)

                        if progress_callback:
                            progress_callback(file_result)

                    elif entry.is_dir(follow_symlinks=False):
                        scan_dir(entry.path)
        except PermissionError:
            print_warn(f"Missing access permissions for directory {path}, skipping.")

    scan_dir(str(search_path))
    return results


def scan_path_with_fd(
    search_path: Path,
) -> FileResults:
    """Scan a directory using fd.

    Args:
        search_path (Path): Directory to scan.

    Raises:
        subprocess.CalledProcessError: If fd exits with non-zero status.

    Returns:
        FileResults: All files in search path.
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
    files = FileResults()

    for line in result.stdout.strip().split("\n"):
        if line:
            files.append(FileResult(Path(line)))

    return files


def scan_search_paths(
    *,
    with_mtime: bool = False,
    prefer_fd: bool | None = None,
    show_progress: bool = False,
) -> FileResults:
    """Scan configured search paths.

    Returns paths of all files stored in the search paths.

    Args:
        with_mtime (bool): Add mtime info for later sorting by new (Python scan only).
        prefer_fd (bool): Prefer the faster fd scanner unless mtime sorting is
            requested. If None, value is read from the configuration file.
        show_progress (bool): Show progress bar during scanning.

    Raises:
        RuntimeError: From fd resolution if platform unsupported.

    Returns:
        FileResults: Results, optionally paired with mtimes.
    """
    cfg = read_config()
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
                partial_fd_scanner = partial(scan_path_with_python, with_mtime=False)
                path_results = list(executor.map(partial_fd_scanner, search_paths))
        else:
            if show_progress:
                # Get estimated total from cache
                if get_library_cache_file().exists():
                    estimated_total = get_library_cache_size()
                else:
                    estimated_total = None

                # Set up progress tracking, use list to make it mutable for the helper
                # function
                files_found = [0]
                progress_lock = threading.Lock()

                def progress_callback(file_result: FileResult):
                    with progress_lock:
                        files_found[0] += 1

                scanner_with_progress = partial(
                    scan_path_with_python,
                    with_mtime=with_mtime,
                    progress_callback=progress_callback,
                )

                futures = [
                    executor.submit(scanner_with_progress, path)
                    for path in search_paths
                ]

                path_results = _scan_with_progress_bar(
                    futures, estimated_total, files_found, progress_lock
                )
            else:
                partial_python_scanner = partial(
                    scan_path_with_python, with_mtime=with_mtime
                )
                path_results = list(executor.map(partial_python_scanner, search_paths))

    all_results = FileResults()

    for res in path_results:
        all_results.extend(res)

    return all_results


def _scan_with_progress_bar(
    futures: list,
    estimated_total: int | None,
    files_found: list[int],
    progress_lock: threading.Lock,
) -> FileResults:
    """Handle progress bar display while futures complete.

    Shows a spinner until first file is found, then displays a progress bar
    with estimated completion based on cache size. Updates progress in real-time
    as files are discovered.

    Args:
        futures (list): List of Future objects from ThreadPoolExecutor.
        estimated_total (int | None): Estimated number of files for progress bar.
            If None, no progress bar is shown.
        files_found (list[int]): Mutable list containing current file count.
            Modified by progress callback during scanning.
        progress_lock (threading.Lock): Lock for thread-safe access to files_found.

    Returns:
        FileResults: Combined results from all completed futures.
    """
    path_results = FileResults()
    remaining_futures = futures.copy()
    first_file_found = False

    # Phase 1: Show spinner until first file found
    with console.status(
        "[bright_cyan]Waiting for file system to respond...[/bright_cyan]"
    ):
        while remaining_futures and not first_file_found:
            # Check for completed futures (non-blocking)
            done_futures = []
            for future in remaining_futures:
                if future.done():
                    path_results.append(future.result())  # Type FileResult
                    done_futures.append(future)

            # Remove completed futures
            for future in done_futures:
                remaining_futures.remove(future)

            # Check progress counter
            with progress_lock:
                current_count = files_found[0]  # Use list to make it mutable

            # Exit if first file found
            if current_count > 0:
                first_file_found = True
                break

            time.sleep(0.1)

    # Phase 2: Show progress bar after first file found
    if estimated_total and estimated_total > 0:
        # Progress bar with estimated cache size from last run
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("({task.completed}/{task.total} files)"),
        ) as progress:
            task = progress.add_task(
                f"{STATUS_SYMBOLS['info']}  "
                "[bright_cyan]Scanning search paths[/bright_cyan]",
                total=estimated_total,
            )
            last_update_count = 0
            update_threshold = max(1, estimated_total // 20)

            while remaining_futures:
                # Check for completed futures (non-blocking)
                done_futures = []

                for future in remaining_futures:
                    if future.done():
                        path_results.append(future.result())
                        done_futures.append(future)

                # Remove completed futures
                for future in done_futures:
                    remaining_futures.remove(future)

                # Update progress bar
                with progress_lock:
                    current_count = files_found[0]

                # Only update if we've found enough new files
                if current_count - last_update_count >= update_threshold:
                    # If we exceed estimate, update the total as well
                    if current_count > estimated_total:
                        new_estimate = int(current_count * 1.1)  # Add 10% buffer
                        progress.update(
                            task,
                            completed=current_count,
                            total=new_estimate,
                        )
                        estimated_total = new_estimate
                    else:
                        progress.update(task, completed=current_count)

                    last_update_count = current_count

                time.sleep(0.1)

            # Final update
            with progress_lock:
                final_count = files_found[0]
                progress.update(task, completed=final_count, total=final_count)
    else:
        # No cache size estimate, continue silently
        while remaining_futures:
            done_futures = []
            for future in remaining_futures:
                if future.done():
                    path_results.append(future.result())
                    done_futures.append(future)

            # Remove completed futures
            for future in done_futures:
                remaining_futures.remove(future)

            time.sleep(0.1)

    return path_results


def rebuild_library_cache() -> FileResults:
    """Rebuild the local library cache.

    Builds an mtime-sorted index (descending / newest first) of all media files in the
    configured search paths.

    Returns:
        FileResults: Rebuilt cache.
    """
    print_info("Rebuilding cache.")
    results = scan_search_paths(with_mtime=True, show_progress=True)
    results.sort(by_mtime=True)
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
    def execute(self) -> FileResults:
        """Execute the query.

        Returns:
            FileResults: Search results.
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

    def execute(self) -> FileResults:
        """Execute the query.

        Returns:
            FileResults: Search results sorted alphabetically by filename.
        """
        results = load_library_cache() if self.cache_library else scan_search_paths()

        results.filter_by_extension(
            self.media_extensions if self.match_extensions else None
        )
        results.filter_by_pattern(self.pattern)
        results.sort()

        return results


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

    def execute(self) -> FileResults:
        """Execute the query.

        Returns:
            FileResults: Up to n newest files, sorted by modification time (newest
                first).
        """
        if self.cache_library:
            # Already sorted by mtime
            results = load_library_cache()
        else:
            # Contains mtime but not sorted yet
            results = scan_search_paths(with_mtime=True)
            results.sort(by_mtime=True)

        results.filter_by_extension(
            self.media_extensions if self.match_extensions else None
        )
        results.filter_by_pattern(self.pattern)

        return results[: self.n]


@dataclass
class FileResult:
    """File search result.

    Attributes:
        file (Path): Filepath.
        mtime (float, optional): Optional last modification timestamp.
    """

    file: Path
    mtime: float | None = None

    def __str__(self) -> str:
        """Returns a POSIX string representation of the file path.

        mtime is never included.

        Returns:
            str: POSIX representation of the file path.
        """
        return self.file.resolve().as_posix()

    @classmethod
    def from_string(cls, path: str | Path) -> FileResult:
        """Create a FileResult from a path.

        Args:
            path (str | Path): String or Path representation of the file path.

        Returns:
            FileResult: New FileResult instance.
        """
        return cls(Path(path))


class FileResults(UserList):
    """Collection of FileResult objects.

    Provides filtering and sorting on file search results.
    """

    def __init__(self, results: list[FileResult] | None = None):
        """Initialize FileResults collection.

        Args:
            results (list[FileResult] | None): List of FileResult objects, or None for
            empty collection.
        """
        super().__init__(results or [])  # Goes to self.data
        self.data: list[FileResult]

    def __str__(self) -> str:
        """Returns newline-separated POSIX paths of all files.

        Returns:
            str: Each file path on a separate line.
        """
        return "\n".join(str(result) for result in self.data)

    @classmethod
    def from_paths(cls, paths: list[str | Path]) -> FileResults:
        """Creare FileResults from list of paths.

        Args:
            paths (list[str | Path]): List of paths.

        Returns:
            FileResults: FileResults object.
        """
        return cls([FileResult.from_string(path) for path in paths])

    def filter_by_extension(self, media_extensions: list[str] | None = None):
        """Filter files by media extensions (in-place).

        Args:
            media_extensions (list[str] | None, optional): List of media file
                extensions, each with a leading '.', for filtering. Defaults to None.
        """
        if not self.data or not media_extensions:
            return

        self.data = [
            result
            for result in self.data
            if result.file.suffix.lower() in media_extensions
        ]

    def filter_by_pattern(self, pattern: str):
        """Filter files by filename pattern (in-place).

        Args:
            pattern (str): Glob-style pattern to match against filenames.
        """
        if not self.data:
            return

        if pattern != "*":
            self.data = [
                result
                for result in self.data
                if fnmatch(result.file.name.lower(), pattern.lower())
            ]

    def sort(self, *, by_mtime: bool = False, reverse: bool = False):
        """Sort collection in-place by file path or modification time.

        Args:
            by_mtime (bool): If True, sort by modification time. If False, sort by file
                path.
            reverse (bool): Sort order reversed if True.

        Raises:
            ValueError: If by_mtime is True and any files lack modification time.
        """
        if by_mtime:
            mtime_missing = [result for result in self.data if result.mtime is None]

            if mtime_missing:
                raise ValueError(
                    "Can't sort by mtime, "
                    f"{len(mtime_missing)} files lack modification time."
                )

            self.data.sort(
                key=attrgetter("mtime"),
                reverse=not reverse,  # Sort descending by default
            )
        else:
            self.data.sort(key=lambda result: result.file.name.lower(), reverse=reverse)

    def sorted(self, *, by_mtime: bool = False, reverse: bool = False) -> FileResults:
        """Return new sorted collection by file path or modification time.

        Args:
            by_mtime (bool): If True, sort by modification time. If False, sort by file
                path.
            reverse (bool): If True, sort in descending order.

        Returns:
            FileResults: New sorted collection.

        Raises:
            ValueError: If by_mtime is True and any files lack modification time.
        """
        sorted_results = FileResults(self.data.copy())
        sorted_results.sort(by_mtime=by_mtime, reverse=reverse)
        return sorted_results
