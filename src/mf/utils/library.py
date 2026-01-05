from .cache import load_library_cache
from .config import get_config
from .file import FileResults


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
