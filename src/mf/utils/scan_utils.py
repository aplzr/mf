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

from mf.constants import FD_BINARIES, STATUS_SYMBOLS

from .config_utils import (
    get_media_extensions,
    get_validated_search_paths,
    read_config,
)
from .console import console
from .patterns import normalize_pattern

__all__ = [
    "get_fd_binary",
    "scan_path_with_python",
    "scan_path_with_fd",
    "find_media_files",
]


def get_fd_binary() -> Path:
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
    pattern: str,
    media_extensions: set[str],
    match_extensions: bool,
    include_mtime: bool = False,
) -> list[Path] | list[tuple[Path, float]]:
    results: list[Path] | list[tuple[Path, float]] = []

    def scan_dir(path: str):
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file(follow_symlinks=False):
                        if match_extensions and media_extensions:
                            if Path(entry.name).suffix.lower() in media_extensions:
                                if fnmatch(entry.name.lower(), pattern.lower()):
                                    if include_mtime:
                                        mtime = entry.stat().st_mtime
                                        results.append((Path(entry.path), mtime))
                                    else:
                                        results.append(Path(entry.path))
                        else:
                            if fnmatch(entry.name.lower(), pattern.lower()):
                                if include_mtime:
                                    mtime = entry.stat().st_mtime
                                    results.append((Path(entry.path), mtime))
                                else:
                                    results.append(Path(entry.path))
                    elif entry.is_dir(follow_symlinks=False):
                        scan_dir(entry.path)
        except PermissionError:
            console.print(
                f"{STATUS_SYMBOLS['warn']}  Missing access permissions for directory {path}, skipping.",
                style="yellow",
            )

    scan_dir(str(search_path))
    return results


def scan_path_with_fd(
    search_path: Path,
    pattern: str,
    media_extensions: set[str],
    match_extensions: bool,
) -> list[Path]:
    cmd = [
        str(get_fd_binary()),
        "--glob",
        "--type",
        "f",
        "--absolute-path",
        "--hidden",
        pattern,
        str(search_path),
    ]
    if match_extensions and media_extensions:
        for ext in media_extensions:
            cmd.extend(["-e", ext.lstrip(".")])
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    files: list[Path] = []
    for line in result.stdout.strip().split("\n"):
        if line:
            files.append(Path(line))
    return files


def find_media_files(
    pattern: str, *, sort_by_mtime: bool = False, prefer_fd: bool = True
) -> list[tuple[int, Path]]:
    pattern = normalize_pattern(pattern)
    search_paths = get_validated_search_paths()
    match_extensions = read_config()["match_extensions"]
    media_extensions = get_media_extensions()
    use_fd = prefer_fd and not sort_by_mtime
    with ThreadPoolExecutor(max_workers=len(search_paths)) as executor:
        if use_fd:
            try:
                scanner = partial(
                    scan_path_with_fd,
                    pattern=pattern,
                    media_extensions=media_extensions,
                    match_extensions=match_extensions,
                )
                path_results = list(executor.map(scanner, search_paths))
            except (
                FileNotFoundError,
                subprocess.CalledProcessError,
                OSError,
                PermissionError,
            ):
                scanner = partial(
                    scan_path_with_python,
                    pattern=pattern,
                    media_extensions=media_extensions,
                    match_extensions=match_extensions,
                    include_mtime=False,
                )
                path_results = list(executor.map(scanner, search_paths))
        else:
            scanner = partial(
                scan_path_with_python,
                pattern=pattern,
                media_extensions=media_extensions,
                match_extensions=match_extensions,
                include_mtime=sort_by_mtime,
            )
            path_results = list(executor.map(scanner, search_paths))
    all_results: list = []
    for res in path_results:
        all_results.extend(res)
    if sort_by_mtime:
        all_results.sort(key=lambda item: item[1], reverse=True)  # type: ignore[index]
        indexed = [
            (idx, path) for idx, (path, _mtime) in enumerate(all_results, start=1)
        ]
    else:
        all_results.sort(key=lambda p: p.name.lower())  # type: ignore[attr-defined]
        indexed = [(idx, p) for idx, p in enumerate(all_results, start=1)]
    return indexed
