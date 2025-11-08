from __future__ import annotations

import os
import platform
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatch
from functools import partial
from importlib.resources import files
from pathlib import Path

from mf.constants import FD_BINARIES

from .config_utils import (
    get_media_extensions,
    get_validated_search_paths,
    read_config,
)
from .console import print_warn
from .normalizers import normalize_pattern

__all__ = [
    "get_fd_binary",
    "scan_path_with_python",
    "scan_path_with_fd",
    "scan_for_media_files",
    "filter_scan_results",
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
    pattern: str,
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

    Returns:
        list[Path]: Filtered results.
    """
    if not results:
        return []

    if isinstance(results[0], tuple):
        # Sort by mtime, extract paths
        results = [
            item[0] for item in sorted(results, key=lambda item: item[1], reverse=True)
        ]
    else:
        # Sort alphabetically
        results.sort()

    # Filter by extension
    if match_extensions and media_extensions:
        results = [path for path in results if path.suffix.lower() in media_extensions]

    # Filter by pattern
    if pattern != "*":
        results = [
            path for path in results if fnmatch(path.name.lower(), pattern.lower())
        ]

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
) -> list[Path]:
    """Find media files by scanning all search paths.

    Args:
        pattern (str): Search pattern.
        sort_by_mtime (bool): Sort by modification time (Python scan only).
        prefer_fd (bool): Prefer fd unless mtime sorting is requested. If None, value is
            read from the configuration file.

    Raises:
        RuntimeError: From fd resolution if platform unsupported.

    Returns:
        list[Path]: Results sorted by mtime if sort_by_mtime, sorted alphabetically
            otherwise.
    """
    cfg = read_config()
    pattern = normalize_pattern(pattern)
    search_paths = get_validated_search_paths()
    match_extensions = cfg["match_extensions"]
    media_extensions = get_media_extensions()

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

    all_results = filter_scan_results(
        pattern, all_results, media_extensions, match_extensions
    )

    return all_results
