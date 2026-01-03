"""Library cache management commands.

Provides a Typer sub-application for managing the media library cache. The cache
stores metadata about all media files in configured search paths to speed up
queries and enable statistics without filesystem scanning.

Command Structure:
    mf cache rebuild    # Force rebuild of library cache
    mf cache file       # Print cache file location
    mf cache clear      # Delete the cache file
"""

from __future__ import annotations

import typer

from .utils.cache import rebuild_library_cache
from .utils.console import print_ok
from .utils.file import get_library_cache_file

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
