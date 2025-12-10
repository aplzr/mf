import math
from bisect import bisect_left
from collections import Counter
from collections.abc import Callable
from numbers import Number
from typing import Any, TypeAlias

from rich.panel import Panel

from .console import console
from .misc import format_size

BinData: TypeAlias = tuple[str, int]  # (label, count)


def show_histogram(
    bins: list[BinData],
    title: str,
    sort: bool = False,
    sort_reverse: bool = False,
    sort_key: Callable[[str], Any] | None = None,
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
        sort_key (Callable[[str], Any] | None, optional): Sorting function to use if
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
        min_size (float): Lower histogram edge. Must be >= 1.
        max_size (float): Upper histogram edge.
        bins_per_decade (int): How many bins per 10x range. Defaults to 4.

    Returns:
        list[float]: Bin edges.
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
    """Assign values to bins and return bins with their values.

    Clamps values outside the bin edges to the lowest or highest bin.

    Args:
        values: List of numbers to bin
        bin_edges: List of bin edge values (must be sorted ascending)

    Returns:
        list[list[float]]: (len(bin_edges) - 1,) list of bins with their values.
    """
    bins = [[] for _ in range(len(bin_edges) - 1)]

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


def get_string_counts(values: list[str]) -> list[tuple[str, int]]:
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
    values: list[Number], bins_per_decade: int = 4
) -> list[tuple[float, int]]:
    """Create a logarithmic histogram of numeric values.

    Bins values using logarithmically-spaced intervals and returns labeled bins
    with their counts. For data spanning multiple orders of magnitude, such as file
    sizes or response times.

    Args:
        values (list[Number]): List of numeric values to bin. Must be non-empty.
        bins_per_decade (int, optional): Number of bins per 10x range. Defaults to 4.
            Higher values create finer granularity.

    Returns:
        list[tuple[float, int]]: List of (bin_center, count) pairs.

    Example:
        >>> file_sizes = [100_000_000, 500_000_000, 2_000_000_000, 5_000_000_000]
        >>> get_log_histogram(file_sizes, bins_per_decade=3)
        [('95.4 MB', 1), ('302 MB', 1), ('955 MB', 0), ('3.02 GB', 1), ('9.55 GB', 1)]
    """
    bin_edges = create_log_bins(min(values), max(values), bins_per_decade)
    bin_centers = get_log_bin_centers(bin_edges)
    bin_labels = [format_size(bin_center) for bin_center in bin_centers]
    bins = group_values_by_bins(values, bin_edges)

    return [(bin_label, len(bin)) for bin_label, bin in zip(bin_labels, bins)]
