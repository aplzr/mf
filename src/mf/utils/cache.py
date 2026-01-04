"""Media library caching system with pickle serialization.

Provides persistent caching of media file metadata to speed up searches and queries.
Uses pickle (protocol 5) instead of JSON for significantly faster deserialization on
large media libraries.

Performance Rationale:
    Pickle chosen over JSON for 5-10x faster loading on large libraries. This is safe
    because the cache is entirely self-generated from local filesystem scans and never
    contains external/untrusted data.

Cache Location:
    - Stored in user's cache directory as 'library.pkl'
    - Platform-aware: $XDG_CACHE_HOME/mf or ~/.cache/mf

Cache Expiration:
    Controlled by 'library_cache_interval' config setting (seconds). Set to 0 for no
    expiration (cache persists indefinitely).

Data Format:
    Pickle protocol 5 (Python 3.8+) containing:
    - timestamp: ISO format string of cache creation time
    - files: List of (POSIX filepath_string, stat_tuple) pairs
    - Sorted by mtime (newest first) for efficient newest-file queries

Migration:
    - Migrated from JSON to pickle for performance
    - Old JSON caches automatically detected and removed on first run

Example:
    >>> # Rebuild cache
    >>> results = rebuild_library_cache()
    >>> print(f"Cached {len(results)} files")

    >>> # Load existing cache
    >>> results = load_library_cache()
    >>> # Returns FileResults sorted by mtime (newest first)
"""

from __future__ import annotations

import json
import pickle
from contextlib import suppress
from datetime import datetime, timedelta
from pickle import UnpicklingError
from pprint import pprint
from typing import Any, TypedDict

from .config import build_config, get_config
from .console import print_and_raise, print_info, print_ok, print_warn
from .file import (
    FileResults,
    get_cache_dir,
    get_library_cache_file,
    get_search_cache_file,
    open_utf8,
)
from .validation import validate_search_cache

PICKLE_PROTOCOL = 5

StatList = tuple[
    int,  # st_mode
    int,  # st_ino
    int,  # st_dev
    int,  # st_nlink
    int,  # st_uid
    int,  # st_gid
    int,  # st_size
    int,  # st_atime
    int,  # st_mtime
    int,  # st_ctime
]
FileEntry = tuple[
    str,  # File path
    StatList,
]


class CacheData(TypedDict):
    """Media library cache data structure.

    Contains metadata for all files found during library scanning,
    including file paths and their filesystem stat information.

    Attributes:
        timestamp: ISO format timestamp of when the cache was last rebuilt
        files: List of (file_path, stat_list) pairs where:

            - file_path: Absolute POSIX path to the media file
            - stat_list: os.stat_result as 10-element tuple containing

              (st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid,
               st_size, st_atime, st_mtime, st_ctime)

    Example:
        {
            "timestamp": "2025-01-02T10:30:00.123456",
            "files": [
                (
                 "/path/to/movie.mkv",
                 (33206, 0, 0, 0, 0, 0, 1234567890, 1640995200, 1640995200, 1640995200)
                ),
                ...
            ]
        }
    """

    timestamp: str
    files: list[FileEntry]


def rebuild_library_cache() -> FileResults:
    """Rebuild the local library cache.

    Builds an mtime-sorted index (descending / newest first) of all media files in the
    configured search paths.

    Returns:
        FileResults: Rebuilt cache.
    """
    from .scan import scan_search_paths

    print_info("Rebuilding cache.")
    remove_old_json_cache()
    results = scan_search_paths(cache_stat=True, show_progress=True)
    results.sort(by_mtime=True)
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "files": [
            (result.file.as_posix(), tuple(result.stat) if result.stat else None)
            for result in results
        ],
    }

    with open(get_library_cache_file(), "wb") as f:
        pickle.dump(cache_data, f, protocol=PICKLE_PROTOCOL)

    print_ok("Cache rebuilt.")
    return results


def _load_library_cache(allow_rebuild=True) -> FileResults:
    """Load cached library metadata. Rebuilds the cache if it is corrupted and
    rebuilding is allowed.

    Args:
        allow_rebuild (bool, optional): Allow cache rebuilding. Defaults to True.

    Returns:
        FileResults: Cached file paths.
    """
    try:
        with open(get_library_cache_file(), "rb") as f:
            cache_data: CacheData = pickle.load(f)

        return FileResults.from_cache(cache_data)
    except (UnpicklingError, EOFError, OSError):
        print_warn("Cache corrupted.")

        return rebuild_library_cache() if allow_rebuild else FileResults()


def load_library_cache() -> FileResults:
    """Load cached library metadata. Rebuilds the cache if it has expired or is
    corrupted.

    Raises:
        typer.Exit: Cache empty or doesn't exist.

    Returns:
        FileResults: Cached file paths.
    """
    return rebuild_library_cache() if is_cache_expired() else _load_library_cache()


def is_cache_expired() -> bool:
    """Check if the library cache is older than the configured cache interval.

    Args:
        cache_timestamp (datetime): Last cache timestamp.

    Returns:
        bool: True if cache has expired or doesn't exist, False otherwise.
    """
    cache_file = get_library_cache_file()

    if not cache_file.exists():
        return True

    cache_timestamp = datetime.fromtimestamp(cache_file.stat().st_mtime)
    cache_interval: timedelta = build_config()["library_cache_interval"]

    if cache_interval.total_seconds() == 0:
        # Cache set to never expire
        return False

    return datetime.now() - cache_timestamp > cache_interval


def get_library_cache_size() -> int | None:
    """Get the size of the library cache.

    Returns:
        int | None: Number of cached file paths or None if cache doesn't exist.
    """
    return (
        len(_load_library_cache(allow_rebuild=False))
        if get_library_cache_file().exists()
        else None
    )


def remove_old_json_cache():
    """Deletes the old JSON cache if it exists."""
    json_cache = get_cache_dir() / "library.json"

    if json_cache.exists():
        with suppress(OSError):
            json_cache.unlink()
            print_info("Removed old JSON cache.")


def print_cache():
    """Print library cache contents for debugging purposes."""
    with open(get_library_cache_file(), "rb") as f:
        pprint(pickle.load(f), compact=True)


def _load_search_cache() -> dict[str, Any]:
    """Load the search cache from disk.

    Returns:
        dict[str, Any]: Cached search results.
    """
    try:
        with open_utf8(get_search_cache_file()) as f:
            return validate_search_cache(json.load(f))
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print_and_raise(
            "No cached search results. "
            "Please run 'mf find <pattern>' or 'mf new' first.",
            raise_from=e,
        )


def load_library() -> FileResults:
    """Loads the full library from cache if caching is activated, does a fresh
    filesystem scan otherwise.

    Returns:
        FileResilts: Full library.
    """
    from .scan import FindQuery

    cfg = get_config()
    cache_library = bool(cfg["cache_library"])

    return (
        load_library_cache()
        if cache_library
        else FindQuery(
            "*",
            auto_wildcards=False,
            cache_stat=True,
            show_progress=True,
            cache_library=False,
            media_extensions=[],
            match_extensions=False,
        ).execute()
    )
