import typer

from .utils.cache import load_library_cache, rebuild_library_cache
from .utils.console import console, print_ok
from .utils.file import get_library_cache_file
from .utils.parsers import parse_resolution
from .utils.stats import count_file_extensions, show_histogram

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
    # Extension histogram (all files)
    cache = load_library_cache()
    extension_counts = count_file_extensions(cache)
    console.print("")
    show_histogram(extension_counts, "Cache file extension distribution")

    # TODO: Extension histogram (media file extensions only)

    # Resolution distribution
    resolution_counts = parse_resolution(cache)
    show_histogram(resolution_counts, "Cache file resolution distribution")

    # TODO: file size distribution
