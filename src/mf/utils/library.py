from pathlib import Path

from .cache import load_library_cache
from .config import get_config
from .file import FileResults


def load_library() -> FileResults:
    """Loads the full library from cache if caching is activated, does a fresh
    filesystem scan with stat caching otherwise.

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


def split_by_search_path(
    file_results: FileResults, search_paths: list[Path]
) -> dict[Path, FileResults]:
    """Split file_results by corresponding search paths.

    Args:
        file_results (FileResults): Collection of files to split.
        search_paths (list[Path]): Search paths to split by.

    Returns:
        dict[Path, FileResults]: Files split by search path.

    Note:
        Search paths are symlink-resolved when they're set, and the library is built by
        recursively scanning these resolved paths. If file_results passed to this
        function have been built from these resolved search paths, splitting by search
        path will work reliably. This is not necessarily true for file_results built in
        other ways.
    """
    files_by_search_path = {search_path: FileResults() for search_path in search_paths}

    for file_result in file_results:
        for search_path in search_paths:
            if file_result.get_path().is_relative_to(search_path):
                files_by_search_path[search_path].append(file_result)
                break

    return files_by_search_path
