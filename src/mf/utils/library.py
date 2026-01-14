"""Library loading and organization utilities."""

from pathlib import Path

from .cache import load_library_cache
from .config import Configuration
from .file import FileResults


# TODO: make progress bar optional
def load_library(show_progress: bool = False) -> FileResults:
    """Loads the full media library from cache if caching is activated, does a fresh
    filesystem scan with stat caching otherwise.

    Args:
        show_progress (bool, optional): Whether to show a progress bar in case a
        filesystem is performed. Defaults to False.

    Returns:
        FileResilts: Full library (media files only).
    """
    from .scan import FindQuery

    cfg = Configuration.from_config()
    cache_library = cfg.cache_library

    return (
        load_library_cache().filtered_by_extension(cfg.media_extensions)
        if cache_library
        else FindQuery(
            "*",
            auto_wildcards=False,
            cache_stat=True,
            show_progress=True,
            cache_library=False,
            media_extensions=cfg.media_extensions,
        ).execute()
    )


def split_by_search_path(
    file_results: FileResults, search_paths: list[Path]
) -> dict[str, FileResults]:
    """Split file_results by corresponding search paths.

    Args:
        file_results (FileResults): Collection of files to split.
        search_paths (list[Path]): Search paths to split by.

    Returns:
        dict[str, FileResults]: Files split by search path.

    Note:
        Search paths are symlink-resolved when they're set, and the library is built by
        recursively scanning these resolved paths. If file_results passed to this
        function have been built from these resolved search paths, splitting by search
        path will work reliably. This is not necessarily true for file_results built in
        other ways.
    """
    files_by_search_path = {
        str(search_path): FileResults() for search_path in search_paths
    }

    for file_result in file_results:
        for search_path in search_paths:
            if file_result.get_path().is_relative_to(search_path):
                files_by_search_path[str(search_path)].append(file_result)
                break

    return files_by_search_path
