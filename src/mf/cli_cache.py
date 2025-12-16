from __future__ import annotations

import typer

from .utils.cache import load_library_cache, rebuild_library_cache
from .utils.config import get_config
from .utils.console import console, print_ok
from .utils.file import get_library_cache_file
from .utils.misc import format_size
from .utils.parsers import parse_resolutions
from .utils.stats import BinData, get_log_histogram, get_string_counts, show_histogram

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
    media_extensions = get_config()["media_extensions"]

    if media_extensions:
        media_cache = cache.copy()
        media_cache.filter_by_extension(media_extensions)

    # Extension histogram (all files)
    console.print("")
    show_histogram(
        get_string_counts(file.suffix for file in cache.get_paths()),
        "File extensions (all files)",
        sort=True,
        # Sort by frequency descending, then name ascending
        sort_key=lambda bar: (-bar[1], bar[0]),
        top_n=20,
    )

    # Extension histogram (media file extensions only)
    if media_extensions:
        show_histogram(
            get_string_counts(file.suffix for file in media_cache.get_paths()),
            "File extensions (media files)",
            sort=True,
        )

    # Resolution distribution
    show_histogram(
        get_string_counts(parse_resolutions(cache)),
        "Media file resolution",
        sort=True,
        sort_key=lambda bar: int("".join(filter(str.isdigit, bar[0]))),
    )

    # File size distribution
    if media_extensions:
        bin_centers, bin_counts = get_log_histogram(
            [result.stat.st_size for result in media_cache]
        )

        # Centers are file sizes in bytes.
        # Convert to string with appropriate size prefix.
        bin_labels = [format_size(bin_center) for bin_center in bin_centers]

        bin_data: list[BinData] = [
            (label, count) for label, count in zip(bin_labels, bin_counts)
        ]
        show_histogram(bin_data, "Media file size")
