from __future__ import annotations

import json
import os
import platform
import stat
import subprocess
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fnmatch import fnmatch
from functools import partial
from importlib.resources import files
from operator import itemgetter
from pathlib import Path

from mf.constants import FD_BINARIES
from mf.utils.cache_utils import get_library_cache_file

from .cache_utils import load_library_cache
from .config_utils import (
    get_validated_search_paths,
    read_config,
)
from .console import print_warn
from .normalizers import normalize_pattern

__all__ = [
    "filter_scan_results",
    "FindQuery",
    "get_fd_binary",
    "NewQuery",
    "rebuild_library_cache",
    "scan_for_media_files",
    "scan_path_with_fd",
    "scan_path_with_python",
]


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
    pattern: str,  # TODO: make results first argument
    results: list[Path] | list[tuple[Path, float]],
    media_extensions: set[str],
    match_extensions: bool,
) -> list[Path]:
    """Filter search results.

    Args:
        pattern (str): Glob pattern to match filenames against.
        results (list[Path] | list[tuple[Path, float]]): Paths, optionally paired with
            mtimes.
        media_extensions (set[str]): Media extensions to match against.
        match_extensions (bool): Whether to match media extensions or not.
        sort_alphabetically (bool, optional): Sorts results alphabetivally if True.

    Returns:
        list[Path]: Filtered results, sorted alphabetically or by modification time,
            depending on the type of results.
    """
    if not results:
        return []

    # Filter by extension
    if match_extensions and media_extensions:
        results = [path for path in results if path.suffix.lower() in media_extensions]

    # Filter by pattern
    if pattern != "*":
        results = [
            path for path in results if fnmatch(path.name.lower(), pattern.lower())
        ]

    return results


def sort_scan_results(
    results: list[Path] | list[tuple[Path, float]], sort_alphabetically: bool = False
) -> list[Path]:
    """Sort combined results from all search paths.

    Args:
        results (list[Path] | list[tuple[Path, float]]): List of paths, optionally
            paired with mtimes.
        sort_alphabetically (bool, optional): Sorts results alphabetically if True.

    Returns:
        list[Path]: Results sorted alphabetically or by mtime, depending on the input
            type.
    """
    if not results:
        return []

    if isinstance(results[0], tuple):
        # Results for `mf new` from a scan. Always sort by mtime when it is present.
        results = [item[0] for item in sorted(results, key=itemgetter(1), reverse=True)]
        return results

    if sort_alphabetically:
        # Whether results without mtime should be sorted alphabetically depends on the
        # context of the call:
        # - Results for `mf find` (scan or cache) must always be sorted alphabetically
        # - Results for `mf new` from the cache are already sorted by mtime and must
        #   stay that way.
        results.sort(key=lambda path: path.name.lower(), reverse=True)

    return results


def scan_path_with_python(
    search_path: Path,
    include_mtime: bool = False,
) -> list[Path] | list[tuple[Path, float]]:
    """Recursively scan a directory using Python.

    Args:
        search_path (Path): Root directory to scan.
        include_mtime (bool): Include modification time in results.

    Returns:
        list[Path] | list[tuple[Path, float]]: All files in the search path, optionally
            paired with mtime.
    """
    results: list[Path] | list[tuple[Path, float]] = []

    def scan_dir(path: str):
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file(follow_symlinks=False):
                        if include_mtime:
                            mtime = entry.stat().st_mtime
                            results.append((Path(entry.path), mtime))
                        else:
                            results.append(Path(entry.path))
                    elif entry.is_dir(follow_symlinks=False):
                        scan_dir(entry.path)
        except PermissionError:
            print_warn(f"Missing access permissions for directory {path}, skipping.")

    scan_dir(str(search_path))
    return results


def scan_path_with_fd(
    search_path: Path,
) -> list[Path]:
    """Scan a directory using fd.

    Args:
        search_path (Path): Directory to scan.

    Raises:
        subprocess.CalledProcessError: If fd exits with non-zero status.

    Returns:
        list[Path]: All files in search path.
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
    files: list[Path] = []

    for line in result.stdout.strip().split("\n"):
        if line:
            files.append(Path(line))

    return files


def scan_for_media_files(
    pattern: str, *, sort_by_mtime: bool = False, prefer_fd: bool | None = None
) -> list[Path] | list[tuple[Path, float]]:
    """Find media files by scanning all search paths.

    Args:
        pattern (str): Search pattern.
        sort_by_mtime (bool): Sort by modification time (Python scan only).
        prefer_fd (bool): Prefer fd unless mtime sorting is requested. If None, value is
            read from the configuration file.

    Raises:
        RuntimeError: From fd resolution if platform unsupported.

    Returns:
        list[Path] | list[tuple[Path, float]]: Results, optionally paired with mtimes.
    """
    cfg = read_config()
    pattern = normalize_pattern(pattern)
    search_paths = get_validated_search_paths()

    if prefer_fd is None:
        prefer_fd = cfg["prefer_fd"]

    use_fd = prefer_fd and not sort_by_mtime

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
                scan_path_with_python, include_mtime=sort_by_mtime
            )
            path_results = list(executor.map(partial_python_scanner, search_paths))

    all_results: list = []

    for res in path_results:
        all_results.extend(res)

    return all_results


def rebuild_library_cache() -> list[Path]:
    """Rebuild the local library cache.

    Builds an mtime-sorted index (descending / newest first) of all media files in the
    configured search paths.

    Returns:
        list[Path]: Rebuilt cache.
    """
    files = scan_for_media_files("*", sort_by_mtime=True)
    files = sort_scan_results(files)
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "files": [file.as_posix() for file in files],
    }

    with open(get_library_cache_file(), "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)

    return files


class Query(ABC):
    """Base class for file search queries."""

    def __init__(self):
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


# TODO: Add cache invalidation
# TODO: Add FileResult type
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
            self.pattern,
            files,
            self.media_extensions,
            self.match_extensions,
        )
        files = sort_scan_results(files, sort_alphabetically=True)

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
            # list[Path], already sorted by mtime
            files = load_library_cache()
        else:
            # list[tuple[Path, float]], not sorted yet
            files = scan_for_media_files(self.pattern, sort_by_mtime=True)
            files = sort_scan_results(files)

        files = filter_scan_results(
            self.pattern, files, self.media_extensions, self.match_extensions
        )
        return files[: self.n]
