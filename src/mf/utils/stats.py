"""Statistics and histogram visualization utilities.

Provides functions for creating and displaying histograms with support for both
categorical data and numeric data spanning multiple orders of magnitude.

Features:
    - Logarithmic binning for data spanning orders of magnitude (file sizes, etc.)
    - Rich terminal-based histogram rendering with bars and percentages
    - Flexible sorting and filtering of histogram bins
    - Geometric mean bin centers for log-spaced histograms

Histogram Types:
    Categorical: Use get_string_counts() to create bins from categories
    Numeric (log-scale): Use get_log_histogram() for data like file sizes

Display:
    Histograms are rendered as Rich panels with:
    - Unicode bar characters (▆) showing relative frequency
    - Percentage of total for each bin
    - Absolute counts
    - Customizable sorting and top-N filtering

Mathematical Notes:
    Logarithmic binning uses base-10 logarithms and geometric means for bin
    centers, which are appropriate for data that varies over orders of magnitude.
    For example, file sizes from 1KB to 1GB benefit from log-scale binning rather
    than linear binning.

Examples:
    >>> # Categorical histogram (file extensions)
    >>> extensions = ['.mp4', '.mkv', '.mp4', '.avi', '.mp4']
    >>> bins = get_string_counts(extensions)
    >>> show_histogram(bins, "File Extensions by Count", sort=True)

    >>> # Numeric histogram (file sizes in bytes)
    >>> sizes = [1_000_000, 5_000_000, 10_000_000, 50_000_000]
    >>> bin_centers, counts = get_log_histogram(sizes)
    >>> bins = [(f"{c/1e6:.1f}MB", count) for c, count in zip(bin_centers, counts)]
    >>> show_histogram(bins, "File Sizes")
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections import Counter
from collections.abc import Callable, Iterable
from os import stat_result
from typing import Any, Literal, TypeAlias

from rich.panel import Panel

from .console import console
from .file import FileResults
from .misc import format_size
from .parsers import parse_resolutions

BinData: TypeAlias = tuple[str, int]  # (label, count)


def show_histogram(
    bins: list[BinData],
    title: str,
    sort: bool = False,
    sort_reverse: bool = False,
    sort_key: Callable[[BinData], Any] | None = None,
    top_n: int | None = None,
):
    """Plot histogram.

    Uses (label, count) pairs to produce a histogram where each pair represents one bin.

    Args:
        bins (list[BinData]): List of (label, count) pairs that represent one histogram
            bin each.
        title (str): Histogram title.
        sort (bool, optional): Whether to sort bins. Sorts by label if no sort_key is
            given. Defaults to False.
        sort_reverse (bool, optional): Reverse sort order of sort==True. Defaults to
            False.
        sort_key (Callable[[Bindata], Any] | None, optional): Sorting function to use if
            sort==True. Defaults to None.
        top_n (int | None, optional): Only use top n bins (after sorting). Defaults to
            None.
    """
    if sort:
        bins = sorted(bins, key=sort_key, reverse=sort_reverse)

    if top_n:
        bins = bins[:top_n]
        title = title + f" (top {top_n})"

    max_count = max(count for _, count in bins)
    total_count = sum(count for _, count in bins)
    no_label = "(no_name)"  # Label used for items where label is ""
    len_no_label = len(no_label)
    len_max_label = max(
        max(len(label) for label, _ in bins),
        len_no_label if "" in bins else 0,
    )
    len_max_count = len(str(max_count))

    bar_char = "▆"
    bars = []

    for label, count in bins:
        percentage = (count / total_count) * 100
        max_bar_panel_width = 50
        bar_panel_width = max_bar_panel_width - len_max_label - len_max_count
        bar_width = int((count / max_count) * bar_panel_width)
        bar = bar_char * bar_width

        # Bar examples:
        #  .bdjo │▆▆▆▆▆▆▆                                 │  198 (11.3%)
        #  .bdmv │▆▆                                      │   69 ( 4.0%)
        name_display = label if label else no_label
        bars.append(
            f"{name_display:>{len_max_label}} "
            f"│[bold cyan]{bar:<{bar_panel_width}}[/bold cyan]│ "
            f"{count:>{len_max_count}} ({percentage:4.1f}%)"
        )

    console.print(
        Panel(
            "\n".join(bars),
            title=(f"[bold cyan]{title}[/bold cyan]"),
            padding=(1, 2),
            title_align="left",
            expand=False,
        )
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

    Bins values using logarithmically-spaced intervals and returns labeled bins
    with their counts. For data spanning multiple orders of magnitude, such as file
    sizes or response times.

    Args:
        values (list[float]): List of numeric values to bin. Must be non-empty.
            Values < 1 are silently clamped to 1.
        bins_per_decade (int, optional): Number of bins per 10x range. Defaults to 4.
            Higher values create finer granularity.

    Returns:
        tuple[list[float], list[int]]: Bin centers and bin counts.

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


def print_extension_histogram(
    results: FileResults, type: Literal["all_files", "media_files"]
):
    """Print a histogram of file extensions.

    Args:
        results (FileResults): File collection. For type "media_files", collection must
            be filtered to media files.
        type (Literal["all_files", "media_files"]): Histogram type. Defines histogram
            formatting.
    """
    bins = get_string_counts(file.suffix for file in results.get_paths())
    console.print("")

    if type == "all_files":
        show_histogram(
            bins=bins,
            title="File extensions (all files)",
            sort=True,
            sort_key=lambda bin_data: (-bin_data[1], bin_data[0]),
            top_n=20,
        )
    else:  # media_files
        show_histogram(
            bins=bins,
            title="File extensions (media files)",
            sort=True,
        )


def print_resolution_histogram(results: FileResults):
    """Print a histogram of video resolutions.

    Args:
        results (FileResults): File collection.
    """
    console.print("")
    show_histogram(
        bins=get_string_counts(parse_resolutions(results)),
        title="Media file resolution",
        sort=True,
        sort_key=lambda bin_data: int("".join(filter(str.isdigit, bin_data[0]))),
    )


def print_file_size_histogram(results: FileResults):
    """Print a histogram of file sizes.

    Args:
        results (FileResults): File collection.
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

    console.print("")
    show_histogram(bins=bins, title="Media file size")
