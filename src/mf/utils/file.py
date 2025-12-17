from __future__ import annotations

import os
import platform
import stat
from collections import UserList
from dataclasses import dataclass
from fnmatch import fnmatch
from importlib.resources import files
from io import TextIOWrapper
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ..constants import FD_BINARIES

if TYPE_CHECKING:
    from .cache import CacheData


def open_utf8(
    file: str | Path, mode: Literal["r", "w"] = "r", **kwargs
) -> TextIOWrapper:
    """Open a text file with utf-8 encoding.

    Args:
        file (str | Path): File to open.
        mode (Literal["r", "w"], optional): Read or write mode. Defaults to "r".
        kwargs: Additional keyword arguments passed on to open().

    Returns:
        TextIOWrapper: Opened file.
    """
    return open(file, mode, encoding="utf-8", **kwargs)


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
        Path: Location of the pickle library cache file.
    """
    return get_cache_dir() / "library.pkl"


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

    bin_path = files("mf").joinpath("bin").joinpath(binary_name)
    bin_path = Path(str(bin_path))

    if system in ("linux", "darwin"):
        current_perms = bin_path.stat().st_mode

        if not (current_perms & stat.S_IXUSR):
            bin_path.chmod(current_perms | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return bin_path


@dataclass
class FileResult:
    """File search result.

    Attributes:
        file (Path): Filepath.
        stat (stat_result, optional): Optional stat result of the file.
    """

    file: Path
    stat: os.stat_result | None = None

    def __str__(self) -> str:
        """Returns a POSIX string representation of the file path.

        mtime is never included.

        Returns:
            str: POSIX representation of the file path.
        """
        # resolve is expensive, so only do it if necessary
        return (
            self.file.as_posix()
            if self.file.is_absolute()
            else self.file.resolve().as_posix()
        )

    def get_path(self) -> Path:
        """Get the path of a FileResult.

        Returns:
            Path: FileResult path.
        """
        return self.file

    @classmethod
    def from_string(cls, path: str | Path) -> FileResult:
        """Create a FileResult from a path.

        Args:
            path (str | Path): String or Path representation of the file path.

        Returns:
            FileResult: New FileResult instance.
        """
        return cls(Path(path))


class FileResults(UserList[FileResult]):
    """Collection of FileResult objects.

    Provides filtering and sorting on file search results.
    """

    def __init__(self, results: list[FileResult] | None = None):
        """Initialize FileResults collection.

        Args:
            results (list[FileResult] | None): List of FileResult objects, or None for
            empty collection.
        """
        super().__init__(results or [])

    def __str__(self) -> str:
        """Returns newline-separated POSIX paths of all files.

        Returns:
            str: Each file path on a separate line.
        """
        return "\n".join(str(result) for result in self.data)

    @classmethod
    def from_paths(cls, paths: list[str | Path]) -> FileResults:
        """Create FileResults from list of paths.

        Args:
            paths (list[str | Path]): List of paths.

        Returns:
            FileResults: FileResults object.
        """
        return cls([FileResult.from_string(path) for path in paths])

    @classmethod
    def from_cache(cls, cache: CacheData) -> FileResults:
        """Create FileResults from cache loaded from disk.

        Args:
            cache (CacheData): Loaded cache.

        Returns:
            FileResults: FileResults object.
        """
        return cls(
            [
                FileResult(Path(path_str), os.stat_result(stat_info))
                for path_str, stat_info in cache["files"]
            ]
        )

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
        if not self.data or pattern == "*":
            return

        self.data = [
            result
            for result in self.data
            if fnmatch(result.file.name.lower(), pattern.lower())
        ]

    def sort(self, *, by_mtime: bool = False, reverse: bool = False):
        """Sort collection in-place by file path or modification time.

        Args:
            by_mtime (bool): If True, sort by modification time. If False, sort by file
                name (case insensitive).
            reverse (bool): Sort order reversed if True.

        Raises:
            ValueError: If by_mtime is True and any files lack modification time.
        """
        if by_mtime:
            mtime_missing = [result for result in self.data if result.stat is None]

            if mtime_missing:
                raise ValueError(
                    "Can't sort by mtime, "
                    f"{len(mtime_missing)} files lack modification time."
                )

            self.data.sort(
                key=attrgetter("stat.st_mtime"),
                reverse=not reverse,  # Sort descending by default
            )
        else:
            self.data.sort(key=lambda result: result.file.name.lower(), reverse=reverse)

    def sorted(self, *, by_mtime: bool = False, reverse: bool = False) -> FileResults:
        """Return new sorted collection by file path or modification time.

        Args:
            by_mtime (bool): If True, sort by modification time. If False, sort by file
                name (case insensitive).
            reverse (bool): If True, sort in descending order.

        Returns:
            FileResults: New sorted collection.

        Raises:
            ValueError: If by_mtime is True and any files lack modification time.
        """
        sorted_results = FileResults(self.data.copy())
        sorted_results.sort(by_mtime=by_mtime, reverse=reverse)
        return sorted_results

    def get_paths(self) -> list[Path]:
        """Get paths of all FileResult objects.

        Returns:
            list[Path]: Paths of all FileResults
        """
        return [result.get_path() for result in self.data]
