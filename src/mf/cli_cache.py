import typer

from .utils.cache import load_library_cache, rebuild_library_cache
from .utils.config import read_config
from .utils.console import console, print_ok
from .utils.file import get_library_cache_file
from .utils.parsers import parse_resolutions
from .utils.stats import show_histogram

app_cache = typer.Typer(help="Manage mf's library cache.")


@app_cache.command()
def rebuild():
    """Rebuild the library cache."""
    rebuild_library_cache()


@app_cache.command()
def file():
    """Print cache file location."""
    print(get_library_cache_file())


@app_cache.command()
def clear():
    """Clear the library cache."""
    get_library_cache_file().unlink()
    print_ok("Cleared the library cache.")


@app_cache.command()
def stats():
    """Show cache statistics."""
    cache = load_library_cache()

    # Extension histogram (all files)
    console.print("")
    show_histogram(
        [file.suffix for file in cache.get_paths()],
        "File extension distribution",
        sort=True,
        # Sort by frequency descending, then name ascending
        sort_key=lambda bar: (-bar[1], bar[0]),
        top_n=20,
    )

    # Extension histogram (media file extensions only)
    media_extensions = read_config()["media_extensions"]

    if media_extensions:
        media_cache = cache.copy()
        media_cache.filter_by_extension(media_extensions)
        show_histogram(
            [file.suffix for file in media_cache.get_paths()],
            "Media file extension distribution",
            sort=True,
        )

    # Resolution distribution
    resolutions = parse_resolutions(cache)
    show_histogram(
        resolutions,
        "File resolution distribution",
        sort=True,
        sort_key=lambda bar: int("".join(filter(str.isdigit, bar[0]))),
    )

    # TODO: file size distribution
