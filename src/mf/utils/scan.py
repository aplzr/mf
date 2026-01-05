"""File system scanning with multiple strategies and progress tracking.

Provides flexible file scanning capabilities with automatic strategy selection:
- Fast scanning using vendored fd binary (default) with Python fallback
- Python scanning with optional progress display
- Library caching for improved performance on repeated scans

Architecture:
    Strategy Pattern:
        - ScanStrategy (ABC): Base for all scanning strategies
        - FdScanStrategy: Fast external tool (fd binary)
        - PythonSilentScanStrategy: Pure Python without progress
        - PythonProgressScanStrategy: Pure Python with live progress bar

    Query Pattern:
        - Query (ABC): Base for search operations
        - FindQuery: Search by glob pattern
        - NewQuery: Find recently modified files

Features:
    - Automatic fallback from fd to Python on failure
    - Optional parallel scanning of multiple search paths
    - Thread-safe progress tracking across concurrent scans
    - Smart progress display (spinner → progress bar)
    - Optional stat caching for mtime-based operations

Progress Display:
    1. Initial spinner while waiting for first file
    2. Progress bar with estimated total from cache
    3. Dynamic total adjustment if estimate exceeded

Performance:
    fd binary provides 30-70% performance improvement over pure Python scanning. Used
    automatically when:
    - Scanning without stat collection (mtime not needed)
    - Command is 'mf find' or cache rebuilding without mtime

    Python scanner used when:
    - Stat information needed (modification times)
    - Command is 'mf new' (sorts by mtime)
    - Cache rebuilding with mtime collection

    The prefer_fd setting is automatically ignored when mtime is required.

    Parallel scanning:
    - Enabled by default (parallel_search=true)
    - Scans each search path in a separate thread
    - Beneficial when paths are on different physical drives
    - Total time limited by slowest path, not sum of all paths

    Disk Thrashing Prevention:
    - Disable parallel_search if multiple paths are on the same _mechanical_ drive
    - Safe and potentially beneficial to leave enabled for SSDs/NVMe (no thrashing
      concerns)
    - Beneficial when paths are on different physical drives (any type)

Example:
    >>> # Simple scan without stat caching
    >>> results = scan_search_paths()

    >>> # Scan with progress and stat caching
    >>> results = scan_search_paths(cache_stat=True, show_progress=True)

    >>> # Use query interface
    >>> query = FindQuery.from_config(pattern="2024")
    >>> results = query.execute()
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial
from pathlib import Path
from subprocess import CalledProcessError
from typing import cast

from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

from ..constants import STATUS_SYMBOLS
from .cache import get_library_cache_size, load_library_cache
from .config import get_config
from .console import console, print_warn
from .file import FileResult, FileResults, get_fd_binary
from .normalizers import normalize_pattern
from .validation import validate_search_paths


class ScanStrategy(ABC):
    """Base class for file scanning strategies.

    Implementations define how to scan directories for files, with different
    strategies optimized for different scenarios (e.g., fast external tools vs
    pure Python fallback).

    The scan method should handle all aspects of scanning including parallelization,
    error handling, and result aggregation.
    """

    @abstractmethod
    def scan(self, search_paths: list[Path], max_workers: int) -> FileResults:
        """Scan search paths for files.

        Args:
            search_paths: List of directories to scan recursively.
            max_workers: Maximum number of parallel workers to use.

        Returns:
            FileResults: All files found across all search paths.
        """
        pass


class FdScanStrategy(ScanStrategy):
    """Uses the vendored fd binary for fast scans without mtime."""

    def scan(self, search_paths: list[Path], max_workers: int) -> FileResults:
        """Scan using fd binary with automatic fallback to Python scanner."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            try:
                path_results = list(executor.map(scan_path_with_fd, search_paths))
            except (FileNotFoundError, CalledProcessError, OSError):
                print_warn("fd scanner unavailable, falling back to python scanner.")
                fallback_strategy = PythonSilentScanStrategy(cache_stat=False)
                return fallback_strategy.scan(search_paths, max_workers)

            return concatenate_fileresults(path_results)


class PythonScanStrategy(ScanStrategy):
    """Uses the python scanner, optionally with stat caching."""

    def __init__(self, cache_stat: bool):
        """Initialize the scanning strategy.

        Args:
            cache_stat (bool): Caches each file's stat information at the cost of an
                additional syscall per file.
        """
        self.cache_stat = cache_stat


class PythonSilentScanStrategy(PythonScanStrategy):
    """Uses the python scanner without a progress bar."""

    def scan(self, search_paths: list[Path], max_workers: int):
        """Scan using the python scanner without progress bar."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            partial_python_scanner = partial(
                scan_path_with_python, with_mtime=self.cache_stat
            )
            path_results = list(executor.map(partial_python_scanner, search_paths))

        return concatenate_fileresults(path_results)


class PythonProgressScanStrategy(PythonScanStrategy):
    """Uses the python scanner with a live progress bar."""

    def scan(self, search_paths: list[Path], max_workers: int) -> FileResults:
        """Scan using the python scanner with a live progress bar."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Get estimated total from cache
            # NOTE: This leads to a silent scan if the total can't be estimated, e.g.
            #   because the cache doesn't exist yet.
            estimated_total = get_library_cache_size()

            progress_counter = ProgressCounter()

            def progress_callback(file_result: FileResult):
                progress_counter.increment()

            scanner_with_progress = partial(
                scan_path_with_python,
                with_mtime=self.cache_stat,
                progress_callback=progress_callback,
            )

            futures = [
                executor.submit(scanner_with_progress, path) for path in search_paths
            ]

            path_results = _scan_with_progress_bar(
                futures, estimated_total, progress_counter
            )

        return concatenate_fileresults(path_results)


def get_scan_strategy(
    cache_stat: bool, prefer_fd: bool, show_progress: bool
) -> ScanStrategy:
    """Get the correct scanning strategy for a specific scenario.

    Args:
        cache_stat (bool): Cache each file's stat info at the cost of an additional
            syscall per file.
        prefer_fd (bool): Prefer the faster fd scanner unless stat caching is requested.
        show_progress (bool): Show progress bar during scanning (python scanner only).

    Returns:
        ScanStrategy: Selected strategy.
    """
    if prefer_fd and not cache_stat:
        return FdScanStrategy()

    if show_progress:
        return PythonProgressScanStrategy(cache_stat=cache_stat)
    else:
        return PythonSilentScanStrategy(cache_stat=cache_stat)


def concatenate_fileresults(path_results: list[FileResults]) -> FileResults:
    """Concatenate a list of FileResults.

    Args:
        path_results (list[FileResults]): FileResults to concatenate.

    Returns:
        FileResults: Concatenated FileResults.
    """
    concatenated_results = FileResults()

    for results in path_results:
        concatenated_results.extend(results)

    return concatenated_results


def scan_search_paths(
    *,
    cache_stat: bool = False,
    prefer_fd: bool | None = None,
    show_progress: bool = False,
) -> FileResults:
    """Scan configured search paths.

    Returns paths of all files stored in the search paths.

    Args:
        cache_stat (bool, optional): Cache each file's stat info at the cost of an
            additional syscall per file. Defaults to False.
        prefer_fd (bool | None, optional): Prefer the faster fd scanner unless stat
            caching is requested. If None, value is read from the configuration file.
            Defaults to None.
        show_progress (bool, optional): Show progress bar during scanning. Defaults to
            False.

    Returns:
        FileResults: Results, optionally with stat info.
    """
    search_path_strings = cast(list[str], get_config()["search_paths"])
    search_paths = validate_search_paths(search_path_strings)

    if prefer_fd is None:
        prefer_fd = get_config()["prefer_fd"]  # type: ignore [assignment]

    max_workers = get_max_workers(search_paths, get_config()["parallel_search"])  # type: ignore [arg-type]
    strategy = get_scan_strategy(cache_stat, prefer_fd, show_progress)  # type: ignore [arg-type]

    return strategy.scan(search_paths, max_workers)


def _scan_with_progress_bar(
    futures: list[Future],
    estimated_total: int | None,
    progress_counter: ProgressCounter,
) -> list[FileResults]:
    """Handle progress bar display while futures complete.

    Shows a spinner until first file is found, then displays a progress bar
    with estimated completion based on cache size. Updates progress in real-time
    as files are discovered.

    Args:
        futures (list[Future]): List of futures from ThreadPoolExecutor. Each
            future represents a search path.
        estimated_total (int | None): Estimated number of files for progress bar.
            If None, no progress bar is shown.
        progress_counter (ProgressCounter): Thread-safe progress counter that tracks
            the number of discovered files during (potentially parallel) scanning of all
            search paths. Updated via callbacks invoked by each scanning thread as files
            are discovered.

    Returns:
        list[FileResults]: FileResults from all futures / search paths.
    """
    polling_interval = 0.1  # [s]
    update_threshold_divisor = 20  # Progress bar is updated this many times
    path_results: list[FileResults] = []  # Results accumulator for all search paths
    remaining_futures = futures.copy()
    first_file_found = False

    # Phase 1: Show spinner until first file found
    with console.status(
        "[bright_cyan]Waiting for file system to respond...[/bright_cyan]"
    ):
        while remaining_futures and not first_file_found:
            remaining_futures = _process_completed_futures(
                remaining_futures, path_results
            )

            # Exit if first file found
            if progress_counter.count > 0:
                first_file_found = True
                break

            time.sleep(polling_interval)

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
            update_threshold = max(1, estimated_total // update_threshold_divisor)

            while remaining_futures:
                remaining_futures = _process_completed_futures(
                    remaining_futures, path_results
                )

                current_count = progress_counter.count

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

                time.sleep(polling_interval)

            # Final update
            final_count = progress_counter.count
            progress.update(task, completed=final_count, total=final_count)

    else:
        # No cache size estimate, continue silently
        while remaining_futures:
            remaining_futures = _process_completed_futures(
                remaining_futures, path_results
            )

            time.sleep(polling_interval)

    return path_results


def _process_completed_futures(
    futures: list[Future], results: list[FileResults]
) -> list[Future]:
    """Processes completed futures and adds them to the results accumulator.

    Args:
        futures (list[Future]): List of futures, some of which may be completed.
        results (list[FileResults]): Accumulator for completed future results (modified
            in-place).

    Returns:
        list[Future]: Remaining futures yet to be processed.
    """
    remaining_futures = []

    for future in futures:
        if future.done():
            results.append(future.result())  # FileResults of one search path

        else:
            remaining_futures.append(future)

    return remaining_futures


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
            found. Can be used for live progress tracking (optional, defaults to None).

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
                            file_result = FileResult(Path(entry.path), entry.stat())
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


def get_max_workers(search_paths: list[Path], parallel_search: bool) -> int:
    """Determines the number of workers for file searching.

    Returns 1 if parallel searching is turned off via the parallel_search setting.
    Returns the number of search paths otherwise.

    Args:
        search_paths (list[Path]): List of configured search paths.
        parallel_search (bool): Whether parallel searching is turned on.

    Returns:
        int: Number of workers to use for file searching.
    """
    return len(search_paths) if parallel_search else 1


class ProgressCounter:
    """Thread-safe counter for tracking progress across multiple threads.

    Provides thread-safe increment operations and read access to the
    current count value via the count property.
    """

    def __init__(self):
        """Initialize counter to zero with a new lock."""
        self._count = 0
        self._lock = threading.Lock()

    def increment(self):
        """Increment the counter by one in a thread-safe manner."""
        with self._lock:
            self._count += 1

    @property
    def count(self) -> int:
        """Get the current count value in a thread-safe manner.

        Returns:
            int: Current count.
        """
        with self._lock:
            return self._count


class Query(ABC):
    """Base class for file search queries.

    Attributes:
        cache_library (bool): Loads library metadata from cache if True, performs
            a fresh filescan otherwise.
        media_extensions (list[str]): Media extensions to match if matching is
            turned on.
        match_extensions (bool): Whether to match media extensions.
    """

    def __init__(
        self, cache_library: bool, media_extensions: list[str], match_extensions: bool
    ):
        """Initialize query.

        Args:
            cache_library (bool): Loads library metadata from cache if True, performs
                a fresh filescan otherwise.
            media_extensions (list[str]): Media extensions to match if matching is
                turned on.
            match_extensions (bool): Whether to match media extensions.
        """
        self.cache_library = cache_library
        self.media_extensions = media_extensions
        self.match_extensions = match_extensions

    @classmethod
    def _get_config_params(cls) -> dict:
        """Get configuration parameters for query initialization.

        Returns the following parameters from the current configuration:
        {
            "cache_library": <bool>,
            "media_extensions": <list[str]>,
            "match_extensions": <bool>,
        }
        """
        cfg = get_config()

        return {
            "cache_library": cfg["cache_library"],
            "media_extensions": cfg["media_extensions"],
            "match_extensions": cfg["match_extensions"],
        }

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
        pattern (str): (Normalized) glob pattern to search for.
        auto_wildcards (bool): Whether to wrap search patterns that don't already
            contain wildcards with asterisks ("batman" -> "*batman*").
        cache_stat (bool): Cache each file's stat info at the cost of an
                additional syscall per file. Defaults to False.
        show_progress (bool): Show progress bar during scanning. Defaults to False.
        cache_library (bool): Loads library metadata from cache if True, performs
            a fresh filescan otherwise.
        media_extensions (list[str]): Media extensions to match if matching is
            turned on.
        match_extensions (bool): Whether to match media extensions.
    """

    def __init__(
        self,
        pattern: str,
        auto_wildcards: bool,
        cache_stat: bool = False,
        show_progress: bool = False,
        *,
        cache_library: bool,
        media_extensions: list[str],
        match_extensions: bool,
    ):
        """Initialize the find query.

        Args:
            pattern (str): Glob pattern to search for (e.g., "*.mp4", "*2023*").
            auto_wildcards: Whether to wrap search patterns that don't already contain
                wildcards with asterisks ("batman" -> "*batman*").
            cache_stat (bool, optional): Cache each file's stat info at the cost of an
                additional syscall per file. Defaults to False.
            show_progress (bool, optional): Show progress bar during scanning. Defaults
                to False.
            cache_library (bool): Loads library metadata from cache if True, performs
                a fresh filescan otherwise.
            media_extensions (list[str]): Media extensions to match if matching is
                turned on.
            match_extensions (bool): Whether to match media extensions.

        """
        if auto_wildcards:
            self.pattern = normalize_pattern(pattern)
        else:
            self.pattern = pattern

        self.cache_stat = cache_stat
        self.show_progress = show_progress

        super().__init__(
            cache_library=cache_library,
            media_extensions=media_extensions,
            match_extensions=match_extensions,
        )

    @classmethod
    def from_config(
        cls, pattern: str, cache_stat: bool = False, show_progress: bool = False
    ) -> FindQuery:
        """Create FindQuery from current configuration.

        Args:
            pattern (str): Glob pattern to search for (e.g., "*.mp4", "*2023*").
            cache_stat (bool, optional): Cache each file's stat info at the cost of an
                additional syscall per file. Defaults to False.
            show_progress (bool, optional): Show progress bar during scanning. Defaults
                to False.

        Returns:
            FindQuery: FindQuery initialized with pattern and parameters from current
                configuration.
        """
        auto_wildcards = bool(get_config()["auto_wildcards"])

        return cls(
            pattern=pattern,
            auto_wildcards=auto_wildcards,
            cache_stat=cache_stat,
            show_progress=show_progress,
            **cls._get_config_params(),
        )

    def execute(self) -> FileResults:
        """Execute the query.

        Returns:
            FileResults: Search results sorted alphabetically by filename.
        """
        results = (
            load_library_cache()
            if self.cache_library
            else scan_search_paths(
                cache_stat=self.cache_stat,
                show_progress=self.show_progress,
            )
        )

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
        n (int): Maximum number of results to return.
        show_progress (bool): Show progress bar during scanning. Defaults to False.
        cache_library (bool): Loads library metadata from cache if True, performs
            a fresh filescan otherwise.
        media_extensions (list[str]): Media extensions to match if matching is
            turned on.
        match_extensions (bool): Whether to match media extensions.
    """

    def __init__(
        self,
        n: int = 20,
        show_progress: bool = False,
        *,
        cache_library: bool,
        media_extensions: list[str],
        match_extensions: bool,
    ):
        """Initialize the new files query.

        Args:
            n: Maximum number of newest files to return. Defaults to 20.
            show_progress (bool, optional): Show progress bar during scanning. Defaults
                to False.
            cache_library (bool): Loads library metadata from cache if True, performs
                a fresh filescan otherwise.
            media_extensions (list[str]): Media extensions to match if matching is
                turned on.
            match_extensions (bool): Whether to match media extensions.
        """
        self.n = n
        self.show_progress = show_progress

        super().__init__(
            cache_library=cache_library,
            media_extensions=media_extensions,
            match_extensions=match_extensions,
        )

    @classmethod
    def from_config(cls, n: int = 20, show_progress: bool = False) -> NewQuery:
        """Create NewQuery from current configuration.

        Args:
            n (int, optional): Maximum number of newest files to return. Defaults to 20.
            show_progress (bool, optional): Show progress bar during scanning. Defaults
                to False.


        Returns:
            NewQuery: NewQuery initialized with n and parameters from current
                configuration.
        """
        return cls(n=n, show_progress=show_progress, **cls._get_config_params())

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
            results = scan_search_paths(
                cache_stat=True,
                show_progress=self.show_progress,
            )
            results.sort(by_mtime=True)

        results.filter_by_extension(
            self.media_extensions if self.match_extensions else None
        )

        return results[: self.n]
