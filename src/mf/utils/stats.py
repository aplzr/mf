"""Statistics and histogram visualization utilities.

Provides functions for creating histogram panels with support for both categorical data
and numeric data spanning multiple orders of magnitude. Histograms are returned as Rich
Panel objects configured via StatsLayout for consistent, responsive formatting.

Features:
    - Logarithmic binning for data spanning orders of magnitude (file sizes, etc.)
    - Rich terminal-based histogram rendering with bars and percentages
    - Flexible sorting and filtering of histogram bins
    - Geometric mean bin centers for log-spaced histograms
    - Responsive layout system that adapts to terminal width

Architecture:
    StatsLayout: Configures panel dimensions, padding, spacing, and column layout
    make_*_histogram(): Factory functions that return configured Panel objects
    get_*(): Data processing functions that compute bin counts

Histogram Types:
    Categorical: Use get_string_counts() to create bins from categories
    Numeric (log-scale): Use get_log_histogram() for data like file sizes

Layout System:
    StatsLayout controls panel formatting and can be created from terminal width:
    - StatsLayout.from_terminal(): Auto-configures based on current terminal
    - Supports multi-column layouts with configurable spacing
    - Enforces minimum/maximum panel widths for readability

Display:
    Histograms are rendered as Rich panels with:
    - Unicode bar characters (▆) showing relative frequency
    - Percentage of total for each bin
    - Absolute counts
    - Customizable sorting and top-N filtering

Mathematical Notes:
    Logarithmic binning uses base-10 logarithms and geometric means for bin centers,
    which are appropriate for data that varies over orders of magnitude. For example,
    file sizes from 1KB to 1GB benefit from log-scale binning rather than linear
    binning.

Examples:
    >>> # Configure layout based on terminal
    >>> layout = StatsLayout.from_terminal()

    >>> # Categorical histogram (file extensions)
    >>> extensions = ['.mp4', '.mkv', '.mp4', '.avi', '.mp4']
    >>> bins = get_string_counts(extensions)
    >>> panel = make_histogram(bins, "File Extensions", layout, sort=True)
    >>> console.print(panel)

    >>> # Numeric histogram (file sizes in bytes)
    >>> sizes = [1_000_000, 5_000_000, 10_000_000, 50_000_000]
    >>> bin_centers, counts = get_log_histogram(sizes)
    >>> bins = [(f"{c/1e6:.1f}MB", count) for c, count in zip(bin_centers, counts)]
    >>> panel = make_histogram(bins, "File Sizes", layout)
    >>> console.print(panel)
"""

from __future__ import annotations

import math
import shutil
from bisect import bisect_left
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from os import stat_result
from typing import Any, Literal, TypeAlias

from rich.panel import Panel

from .file import FileResults
from .misc import format_size
from .parsers import parse_resolutions

BinData: TypeAlias = tuple[str, int]  # (label, count)


@dataclass
class StatsLayout:
    """Configuration for histogram panel layout and formatting.

    Controls panel dimensions, spacing, and alignment for statistics displays. Supports
    responsive multi-column layouts that adapt to terminal width.

    Usage:
        Use StatsLayout.from_terminal() to auto-configure based on current terminal:

        >>> layout = StatsLayout.from_terminal()
        >>> panel = make_histogram(bins, "Title", layout)

    Attributes:
        n_columns (int): Number of panels to render side by side.
        panel_width (int): Width of a single panel in characters.
        terminal_width (int | None): Terminal width in characters, if detected.
        padding (tuple[int, int]): (vertical, horizontal) padding inside panels and
            between panels.
        title_align (Literal["left", "center", "right"]): Panel title alignment.
        expand (bool): Whether to expand to terminal width. Always False.
    """

    n_columns: int
    panel_width: int
    terminal_width: int | None = None
    padding: tuple[int, int] = (1, 1)
    title_align: Literal["left", "center", "right"] = "left"
    _expand: bool = field(default=False, repr=False)

    @property
    def expand(self):  # noqa: D102
        return self._expand

    @staticmethod
    def from_terminal(
        max_columns: int = 5,
        min_width: int = 39,
        max_width: int = 80,
        padding: tuple[int, int] = (1, 1),
    ) -> StatsLayout:
        """Create layout optimized for current terminal width.

        Determines optimal column count and panel width to maximize terminal space while
        respecting min/max width constraints. Prioritizes more columns over wider
        panels.

        Args:
            max_columns: Maximum panels to display side by side. Defaults to 5.
            min_width: Minimum panel width in characters. Defaults to 39.
            max_width: Maximum panel width in characters. Defaults to 80.
            padding: (vertical, horizontal) padding inside panels and between panels.
                Defaults to (1, 1).

        Returns:
            StatsLayout: Responsive layout for current terminal dimensions.

        Example:
            >>> layout = StatsLayout.from_terminal(max_columns=3, min_width=50)
        """
        fallback_cols = 80
        fallback_rows = 24
        terminal_width = shutil.get_terminal_size(
            fallback=(fallback_cols, fallback_rows)
        ).columns

        # Calculate columns that fit
        for n_columns in range(max_columns, 0, -1):
            needed = min_width * n_columns + padding[1] * (n_columns - 1)

            if needed <= terminal_width:
                available = terminal_width - padding[1] * (n_columns - 1)
                width = available // n_columns
                panel_width = min(width, max_width)

                return StatsLayout(
                    n_columns=n_columns,
                    panel_width=panel_width,
                    terminal_width=terminal_width,
                    padding=padding,
                )

        # Fallback
        return StatsLayout(n_columns=1, panel_width=min_width)


def make_histogram(
    bins: list[BinData],
    title: str,
    layout: StatsLayout,
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
        layout (LayoutConfig): Panel layout.
        sort (bool, optional): Whether to sort bins. Sorts by label if no sort_key is
            given. Defaults to False.
        sort_reverse (bool, optional): Reverse sort order of sort==True. Defaults to
            False.
        sort_key (Callable[[Bindata], Any] | None, optional): Sorting function to use if
            sort==True. Defaults to None.
        top_n (int | None, optional): Only use top n bins (after sorting). Defaults to
            None.

    Returns:
        Panel: Ready-to-render panel conforming to the specified layout.
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
        layout.panel_width
        - 2 * panel_border_width
        - 2 * layout.padding[1]
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
        padding=layout.padding,
        title_align=layout.title_align,
        expand=layout.expand,
    )


def make_extension_histogram(
    results: FileResults,
    type: Literal["all_files", "media_files"],
    layout: StatsLayout,
) -> Panel:
    """Make a histogram of file extensions.

    Args:
        results (FileResults): File collection. For type "media_files", collection must
            be filtered to media files.
        type (Literal["all_files", "media_files"]): Histogram type. Defines histogram
            formatting.
        layout (StatsLayout): Panel layout.

    Returns:
        Panel: Ready-to-render histogram panel.
    """
    bins = get_string_counts(file.suffix for file in results.get_paths())

    if type == "all_files":
        return make_histogram(
            bins=bins,
            title="File extensions (all files)",
            layout=layout,
            sort=True,
            sort_key=lambda bin_data: (-bin_data[1], bin_data[0]),
            top_n=20,
        )
    else:  # media_files
        return make_histogram(
            bins=bins,
            title="File extensions (media files)",
            layout=layout,
            sort=True,
        )


def make_resolution_histogram(results: FileResults, layout: StatsLayout) -> Panel:
    """Make a histogram of video resolutions.

    Args:
        results (FileResults): File collection.
        layout (StatsLayout): Panel layout.

    Returns:
        Panel: Ready-to-render histogram panel.
    """
    return make_histogram(
        bins=get_string_counts(parse_resolutions(results)),
        title="Media file resolution",
        layout=layout,
        sort=True,
        sort_key=lambda bin_data: int("".join(filter(str.isdigit, bin_data[0]))),
    )


def make_filesize_histogram(results: FileResults, layout: StatsLayout) -> Panel:
    """Make a histogram of file sizes.

    Args:
        results (FileResults): File collection.
        layout (LayoutConfig): Panel layout.

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

    return make_histogram(bins=bins, title="Media file size", layout=layout)


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
