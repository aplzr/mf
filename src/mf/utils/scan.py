from __future__ import annotations

import os
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

from ..constants import STATUS_SYMBOLS
from .cache import get_library_cache_size, load_library_cache
from .config import read_config
from .console import console, print_warn
from .file import FileResult, FileResults, get_fd_binary, get_library_cache_file
from .misc import validate_search_paths
from .normalizers import normalize_pattern


def scan_search_paths(
    *,
    cache_stat: bool = False,
    prefer_fd: bool | None = None,
    show_progress: bool = False,
) -> FileResults:
    """Scan configured search paths.

    Returns paths of all files stored in the search paths.

    Args:
        cache_stat (bool): Cache each file's stat info at the cost of an additional
            syscall per file.
        prefer_fd (bool): Prefer the faster fd scanner unless stat caching is requested.
            If None, value is read from the configuration file.
        show_progress (bool): Show progress bar during scanning.

    Raises:
        RuntimeError: From fd resolution if platform unsupported.

    Returns:
        FileResults: Results, optionally with stat info.
    """
    search_paths = validate_search_paths()

    if prefer_fd is None:
        prefer_fd = read_config()["prefer_fd"]

    use_fd = prefer_fd and not cache_stat

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
                    with_mtime=cache_stat,
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
                    scan_path_with_python, with_mtime=cache_stat
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
            results = scan_search_paths(cache_stat=True)
            results.sort(by_mtime=True)

        results.filter_by_extension(
            self.media_extensions if self.match_extensions else None
        )
        results.filter_by_pattern(self.pattern)

        return results[: self.n]
