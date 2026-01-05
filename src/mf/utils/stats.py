"""Statistics and histogram visualization utilities.

Provides functions for creating histogram panels from categorical and numeric data.
Histograms are returned as Rich Panel objects that can be displayed directly or
accumulated in a ColumnLayout for multi-column presentation.

Features:
    - Logarithmic binning for data spanning orders of magnitude (file sizes, etc.)
    - Terminal-based histogram rendering with bars and percentages
    - Flexible sorting and filtering of histogram bins
    - Geometric mean bin centers for log-spaced histograms
    - Customizable panel formatting via PanelFormat

Functions:
    make_histogram(): Create histogram panel from (label, count) bin data
    make_extension_histogram(): Histogram of file extensions
    make_resolution_histogram(): Histogram of video resolutions
    make_filesize_histogram(): Histogram of file sizes (logarithmic)

    get_string_counts(): Count frequency of categorical values
    get_log_histogram(): Create logarithmic histogram bins for numeric data
    create_log_bins(): Generate logarithmically-spaced bin edges
    get_log_bin_centers(): Calculate geometric mean bin centers
    group_values_by_bins(): Assign values to histogram bins

Histogram Types:
    Categorical: Use get_string_counts() to create bins from string values
    Numeric (log-scale): Use get_log_histogram() for data like file sizes

Display:
    Histograms are rendered as Rich panels with:
    - Unicode bar characters (▆) showing relative frequency
    - Percentage of total for each bin
    - Absolute counts
    - Customizable sorting and top-N filtering

Mathematical Notes:
    Logarithmic binning uses base-10 logarithms and geometric means for bin centers,
    which are appropriate for data spanning multiple orders of magnitude. For example,
    file sizes from 1KB to 1GB benefit from log-scale binning rather than linear bins.

Examples:
    Categorical histogram (file extensions):
        >>> from mf.utils.console import ColumnLayout
        >>> extensions = ['.mp4', '.mkv', '.mp4', '.avi', '.mp4']
        >>> bins = get_string_counts(extensions)
        >>>
        >>> layout = ColumnLayout.from_terminal()
        >>> format = layout.panel_format
        >>> panel = make_histogram(bins, "File Extensions", format, sort=True)
        >>> layout.add_panel(panel)
        >>> layout.print()

    Numeric histogram (file sizes):
        >>> sizes = [1_000_000, 5_000_000, 10_000_000, 50_000_000]
        >>> bin_centers, counts = get_log_histogram(sizes)
        >>> bins = [(f"{c/1e6:.1f}MB", count) for c, count in zip(bin_centers, counts)]
        >>>
        >>> panel = make_histogram(bins, "File Sizes", format)
        >>> layout.add_panel(panel)
        >>> layout.print()

    Direct display (single histogram):
        >>> from mf.utils.config import console
        >>> from mf.utils.console import PanelFormat
        >>> format = PanelFormat(panel_width=60)
        >>> panel = make_histogram(bins, "Title", format)
        >>> console.print(panel)
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import datetime
from os import stat_result
from pathlib import Path
from statistics import mean
from typing import Any, Literal, TypeAlias, cast

from rich import box
from rich.panel import Panel
from rich.table import Table

from .config import get_config
from .console import ColumnLayout, PanelFormat, console
from .file import FileResults
from .library import load_library, split_by_search_path
from .misc import format_size
from .parsers import parse_resolutions

BinData: TypeAlias = tuple[str, int]  # (label, count)


def make_histogram(
    bins: list[BinData],
    title: str,
    format: PanelFormat,
    sort: bool = False,
    sort_reverse: bool = False,
    sort_key: Callable[[BinData], Any] | None = None,
    top_n: int | None = None,
) -> Panel:
    """Make a histogram.

    Uses (label, count) pairs to produce a histogram where each pair represents one bin.

    Args:
        bins (list[BinData]): List of (label, count) pairs that represent one histogram
            bin each.
        title (str): Histogram title.
        format (PanelFormat): Panel format.
        sort (bool, optional): Whether to sort bins. Sorts by label if no sort_key is
            given. Defaults to False.
        sort_reverse (bool, optional): Reverse sort order of sort==True. Defaults to
            False.
        sort_key (Callable[[Bindata], Any] | None, optional): Sorting function to use if
            sort==True. Defaults to None.
        top_n (int | None, optional): Only use top n bins (after sorting). Defaults to
            None.

    Returns:
        Panel: Ready-to-render panel conforming to the specified format.
    """
    if sort:
        bins = sorted(bins, key=sort_key, reverse=sort_reverse)

    if top_n:
        bins = bins[:top_n]
        title = title + f" (top {top_n})"

    # Statistical parameters
    max_count = max(count for _, count in bins)
    total_count = sum(count for _, count in bins)

    # Formatting
    no_label = "(no_name)"  # Label used for items where label is ""
    bar_char = "▆"

    # Accumulator for strings representing histogram bars
    bars: list[str] = []

    # Parameters controlling panel width
    panel_border_width = 1
    len_no_label = len(no_label)
    len_max_label = max(
        max(len(label) for label, _ in bins),
        len_no_label if "" in bins else 0,
    )
    len_max_count = len(str(max_count))
    percentage_width = 4

    # This is the free parameter that needs to be adjusted to hit the target total width
    max_bar_width = (
        format.panel_width
        - 2 * panel_border_width
        - 2 * format.padding[1]
        - len_max_label
        - len_max_count
        - (percentage_width + 3)  # "( 2.4%)"
        - 5  # 3 spaces, two "|" characters left and right to the bar
    )

    for label, count in bins:
        # Create the histogram bars. Examples:
        # │  110 MB │▆                    │   59 ( 1.6%) │
        # │ 1.93 GB │▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆ │ 1010 (28.0%) │
        percentage = (count / total_count) * 100
        bar_width = int((count / max_count) * max_bar_width)
        bar = bar_char * bar_width
        name_display = label if label else no_label
        bars.append(
            f"{name_display:>{len_max_label}} "
            f"│[bold cyan]{bar:<{max_bar_width}}[/bold cyan]│ "
            f"{count:>{len_max_count}} ({percentage:{percentage_width}.1f}%)"
        )

    return Panel(
        "\n".join(bars),
        title=(f"[bold cyan]{title}[/bold cyan]"),
        padding=format.padding,
        title_align=format.title_align,
        expand=False,
    )


def make_extension_histogram(
    results: FileResults,
    type: Literal["all_files", "media_files"],
    format: PanelFormat,
) -> Panel:
    """Make a histogram of file extensions.

    Args:
        results (FileResults): File collection. For type "media_files", collection must
            be filtered to media files.
        type (Literal["all_files", "media_files"]): Histogram type. Defines histogram
            formatting.
        format (PanelFormat): Panel format.

    Returns:
        Panel: Ready-to-render histogram panel.
    """
    bins = get_string_counts(file.suffix for file in results.get_paths())

    if type == "all_files":
        return make_histogram(
            bins=bins,
            title="File extensions",
            format=format,
            sort=True,
            sort_key=lambda bin_data: (-bin_data[1], bin_data[0]),
            top_n=20,
        )
    else:  # media_files
        return make_histogram(
            bins=bins,
            title="Media file extensions",
            format=format,
            sort=True,
        )


def make_resolution_histogram(results: FileResults, format: PanelFormat) -> Panel:
    """Make a histogram of video resolutions.

    Args:
        results (FileResults): File collection.
        format (PanelFormat): Panel format.

    Returns:
        Panel: Ready-to-render histogram panel.
    """
    return make_histogram(
        bins=get_string_counts(parse_resolutions(results)),
        title="File resolution",
        format=format,
        sort=True,
        sort_key=lambda bin_data: int("".join(filter(str.isdigit, bin_data[0]))),
    )


def make_filesize_histogram(results: FileResults, format: PanelFormat) -> Panel:
    """Make a histogram of file sizes.

    Args:
        results (FileResults): File collection.
        format (PanelFormat): Panel format.

    Returns:
        Panel: Ready-to-render histogram panel.
    """
    bin_centers, bin_counts = get_log_histogram(
        [
            result.stat.st_size
            for result in results
            if isinstance(result.stat, stat_result)
        ]
    )
    # Centers are file sizes in bytes. Convert to string with appropriate size prefix.
    bin_labels = [format_size(bin_center) for bin_center in bin_centers]
    bins: list[BinData] = [
        (label, count) for label, count in zip(bin_labels, bin_counts)
    ]

    return make_histogram(bins=bins, title="Media file size", format=format)


def make_file_age_histogram(
    results: FileResults, format: PanelFormat, title: str = "File age"
) -> Panel:
    """Make a histogram of file age by year.

    Args:
        results (FileResults): File collection.
        format (PanelFormat): Panel format.
        title (str, optional): Panel title. Defaults to "File age".

    Returns:
        Panel: _description_
    """
    year_strings = [
        datetime.fromtimestamp(file.stat.st_mtime).strftime("%Y")
        for file in results
        if file.stat
    ]
    bins = get_string_counts(year_strings)

    return make_histogram(
        bins,
        title=title,
        format=format,
        sort=True,
        sort_key=lambda bin: bin[0],
    )


def create_log_bins(
    min_size: float, max_size: float, bins_per_decade: int = 4
) -> list[float]:
    """Create logarithmic histogram bins.

    Args:
        min_size (float): Lower histogram edge. Values < 1 are automatically clamped to
            1.
        max_size (float): Upper histogram edge (must be > min_size after clamping).
        bins_per_decade (int): How many bins per 10x range. Defaults to 4.

    Returns:
        list[float]: Bin edges.

    Note:
        min_size is clamped to a minimum of 1 to avoid log(0) or log(negative). This
        means the histogram will show all values < 1 in the first bin.
    """
    if min_size <= 1:
        min_size = 1

    log_min = math.log10(min_size)
    log_max = math.log10(max_size)
    n_bins = int((log_max - log_min) * bins_per_decade) + 1

    return [
        10 ** (log_min + i * (log_max - log_min) / (n_bins - 1)) for i in range(n_bins)
    ]


def get_log_bin_centers(bin_edges: list[float]) -> list[float]:
    """Get the geometric mean of log-spaced histogram bins.

    Args:
        bin_edges (list[float]): Log-spaced histogram bin edges.

    Returns:
        list[float]: Geometric bin centers.
    """
    return [
        math.sqrt(bin_edges[i] * bin_edges[i + 1]) for i in range(len(bin_edges) - 1)
    ]


def group_values_by_bins(
    values: list[float], bin_edges: list[float]
) -> list[list[float]]:
    """Assign values to histogram bins based on bin edges.

    Uses left-closed, right-open intervals: [edge_i, edge_{i+1}).
    Values exactly equal to an edge are assigned to the bin starting at that edge.
    Values outside the range are clamped to the nearest bin.

    Args:
        values: List of numbers to bin
        bin_edges: List of bin edge values (must be sorted ascending)

    Binning Strategy:
        Value < bin_edges[0]: Assigned to first bin (clamped)
        bin_edges[i] <= value < bin_edges[i+1]: Assigned to bin i
        Value >= bin_edges[-1]: Assigned to last bin (clamped)

    Returns:
        list[list[float]]: Length len(bin_edges)-1 list of bins with their values.
    """
    bins: list[list[float]] = [[] for _ in range(len(bin_edges) - 1)]

    for value in values:
        bin_idx = bisect_left(bin_edges, value)

        if bin_idx == 0:
            # Value is below first edge
            bin_idx = 0
        elif bin_idx >= len(bin_edges):
            # Value is above last edge
            bin_idx = len(bin_edges) - 2
        else:
            # Value is within the edges
            bin_idx = bin_idx - 1

        bins[bin_idx].append(value)

    return bins


def get_string_counts(values: Iterable[str]) -> list[tuple[str, int]]:
    """Calculate the frequency distribution of string values.

    Takes a list of strings and returns the unique values along with their
    occurrence counts, similar to creating bins for a histogram of categorical data.

    Args:
        values (list[str]): List of string values to analyze.

    Returns:
        list[tuple[str, int]]: List of (unique string, count) pairs.

    Example:
        >>> get_string_counts(['apple', 'banana', 'apple', 'banana', 'apple'])
        [('apple', 3), ('banana', 2)]
    """
    return list(Counter(values).items())


def get_log_histogram(
    values: list[float], bins_per_decade: int = 4
) -> tuple[list[float], list[int]]:
    """Create a logarithmic histogram of numeric values.

    Bins values using logarithmically-spaced intervals. For data spanning multiple
    orders of magnitude, such as file sizes or response times.

    Args:
        values (list[float]): List of numeric values to bin. Must be non-empty.
            Values < 1 are silently clamped to 1.
        bins_per_decade (int, optional): Number of bins per 10x range. Defaults to 4.
            Higher values create finer granularity.

    Returns:
        tuple[list[float], list[int]]: Bin centers (geometric means of bin edges) and
        bin counts.

    Example:
        >>> values = [100_000_000, 500_000_000, 2_000_000_000, 5_000_000_000]
        >>> ([147875763.6628315,
              323363503.2886788,
              707106781.1865475,
              1546247473.5549579,
              3381216689.0312037],
             [1, 0, 1, 1, 1])
    """
    if not values:
        raise ValueError("'values' can't be empty.")

    bin_edges = create_log_bins(min(values), max(values), bins_per_decade)
    bin_centers = get_log_bin_centers(bin_edges)
    bins = group_values_by_bins(values, bin_edges)

    return bin_centers, [len(bin) for bin in bins]


def print_stats():
    """Print library statistics.

    Loads library metadata from cache if caching is activated, otherwise performs a
    fresh filesystem scan to compute library statistics.
    """
    cfg = get_config()
    configured_extensions = cast(list[str], cfg["media_extensions"])
    results = load_library()
    layout = ColumnLayout.from_terminal()

    if configured_extensions:
        results_filtered = results.copy()
        results_filtered.filter_by_extension(configured_extensions)

    # Create statistics
    layout.add_panel(
        make_extension_histogram(results, type="all_files", format=layout.panel_format)
    )
    layout.add_panel(make_resolution_histogram(results, format=layout.panel_format))

    if configured_extensions:
        layout.add_panel(
            make_extension_histogram(
                results_filtered, type="media_files", format=layout.panel_format
            )
        )
        layout.add_panel(
            make_filesize_histogram(results_filtered, format=layout.panel_format)
        )
        layout.add_panel(
            make_file_age_histogram(
                results_filtered, format=layout.panel_format, title="Media file age"
            )
        )
    else:
        layout.add_panel(make_file_age_histogram(results, format=layout.panel_format))

    # Render statistics in a multi-column layout
    print_summary()
    layout.print()


def print_summary():
    """Print summary statistics of individual search paths and the full library."""
    cfg = get_config()
    library = load_library()
    search_paths = [Path(path_str) for path_str in cfg["search_paths"]]
    media_extensions = cast(list[str], cfg["media_extensions"])
    subsets = split_by_search_path(library, search_paths)
    subsets["Full library"] = library  # NOTE: Other keys are paths, not strings

    table = Table(
        box=box.ROUNDED, padding=(0, 1), header_style="bright_cyan", show_lines=False
    )
    table.add_column("Subset", justify="left", overflow="ellipsis")

    for header in ["Files", "Media", "Newest", "Oldest", "Av. Size", "Total Size"]:
        table.add_column(header, justify="right")

    def build_row(label: str, subset: FileResults) -> tuple[str, ...]:
        subset.sort(by_mtime=True)
        subset_media = subset.filtered_by_extension(media_extensions)

        files = str(len(subset))
        media_files = str(len(subset_media)) if media_extensions else "N/A"
        newest = (
            datetime.fromtimestamp(subset[0].stat.st_mtime).strftime("%Y-%m-%d")
            if subset[0].stat
            else "N/A"
        )
        oldest = (
            datetime.fromtimestamp(subset[-1].stat.st_mtime).strftime("%Y-%m-%d")
            if subset[-1].stat
            else "N/A"
        )
        av_size = format_size(mean(file.stat.st_size for file in subset if file.stat))
        total_size = format_size(sum(file.stat.st_size for file in subset if file.stat))

        return label, files, media_files, newest, oldest, av_size, total_size

    for label, subset in subsets.items():
        table.add_row(*build_row(str(label), subset))

    console.print(table)
