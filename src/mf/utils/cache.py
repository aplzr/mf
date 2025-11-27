import json
from datetime import datetime

from .config import build_config
from .console import print_info, print_ok, print_warn
from .file import FileResults, get_library_cache_file


def rebuild_library_cache() -> FileResults:
    """Rebuild the local library cache.

    Builds an mtime-sorted index (descending / newest first) of all media files in the
    configured search paths.

    Returns:
        FileResults: Rebuilt cache.
    """
    from .scan import scan_search_paths

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

        results = FileResults.from_paths(cache_data["files"])
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


def is_cache_expired() -> bool:
    """Check if the library cache is older than the configured cache interval.

    Args:
        cache_timestamp (datetime): Last cache timestamp.

    Returns:
        bool: True if cache has expired, False otherwise.
    """
    cache_file = get_library_cache_file()

    if not cache_file.exists():
        # is_cache_expired is only called if caching is turned on, so if the cache file
        # doesn't exist we always have to build the cache, even if rebuilding is turned
        # off via library_cache_interval = 0.
        return True

    cache_timestamp = datetime.fromtimestamp(cache_file.stat().st_mtime)
    cache_interval = build_config()["library_cache_interval"]

    if cache_interval.total_seconds() == 0:
        # Cache set to never expire
        return False

    return datetime.now() - cache_timestamp > cache_interval


def get_library_cache_size() -> int:
    """Get the size of the library cache.

    Returns:
        int: Number of cached file paths.
    """
    return len(_load_library_cache(allow_rebuild=False))
