import typer

from .utils.cache import load_library_cache, rebuild_library_cache
from .utils.console import console, print_ok
from .utils.file import get_library_cache_file
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
    # Extension histogram
    cache = load_library_cache()
    extension_counts = count_file_extensions(cache)
    console.print("")
    show_histogram(extension_counts, "File extension distribution")

    # TODO: file size distribution
