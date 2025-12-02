import math
from bisect import bisect_left
from collections import Counter
from collections.abc import Callable
from numbers import Number
from typing import Any

from rich.panel import Panel

from .console import console
from .misc import format_size


def show_histogram(
    items: list[str],
    title: str,
    sort: bool = False,
    sort_reverse: bool = False,
    sort_key: Callable[[str], Any] | None = None,
    top_n: int | None = None,
):
    """Plot histogram.

    Counts the items by producing (item, count) tuples which are then sorted if sorting
    is requested (using sort_key if given). The resulting tuples are then used to
    produce the histogram, where each tuple produces a histogram bar.

    Args:
        items (list[str]): Data whose distribution should be shown.
        title (str): Histogram title.
        sort (bool, optional): Whether to sort item counts. Defaults to False.
        sort_reverse (bool, optional): Reverse sort order of sort==True. Defaults to
            False.
        sort_key (Callable[[str], Any] | None, optional): Sorting function to use if
            sort==True. Defaults to None.
        top_n (int | None, optional): Only use top n counts (after sorting). Defaults to
            None.
    """
    item_counts = list(Counter(items).items())

    if sort:
        item_counts = sorted(item_counts, key=sort_key, reverse=sort_reverse)

    if top_n:
        item_counts = item_counts[:top_n]
        title = title + f" (top {top_n})"

    max_count = max(count for _, count in item_counts)
    total_count = sum(count for _, count in item_counts)
    no_name = "(no_name)"  # Name used for items where name is ""
    len_no_name = len(no_name)
    max_name_len = max(
        max(len(name) for name, _ in item_counts),
        len_no_name if "" in item_counts else 0,
    )

    bar_char = "▆"
    bars = []

    for name, count in item_counts:
        percentage = (count / total_count) * 100
        bar_width = int((count / max_count) * 40)
        bar = bar_char * bar_width

        # Bar examples:
        #  .bdjo │▆▆▆▆▆▆▆                                 │  198 (11.3%)
        #  .bdmv │▆▆                                      │   69 ( 4.0%)
        name_display = name if name else no_name
        bars.append(
            f"{name_display:>{max_name_len}} "
            f"│[bold cyan]{bar:<40}[/bold cyan]│ "
            f"{count:>{len(str(max_count))}} ({percentage:4.1f}%)"
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
        min_size (float): Smallest value in the distribution.
        max_size (float): Largest value in the distribution.
        bins_per_decade (int): How many bins per 10x range. Defaults to 4.

    Returns:
        list[float]: Bin edges.
    """
    log_min = math.log10(min_size)
    log_max = math.log10(max_size)
    n_bins = int((log_max - log_min) * bins_per_decade) + 1

    return [
        10 ** (log_min + i * (log_max - log_min) / (n_bins - 1)) for i in range(n_bins)
    ]


def create_log_bin_labels(bin_edges: list[Number]) -> list[str]:
    """Create labels for logarithmic histogram bins.

    Creates a label for each bin that is the geometric mean of the bin edges.

    Args:
        bin_edges (list[Number]): List of bin edge values.

    Returns:
        list[str]: Label strings like "250 MB" (bin center).
    """
    labels = []

    for i in range(len(bin_edges) - 1):
        center = math.sqrt(bin_edges[i] * bin_edges[i + 1])
        labels.append(format_size(center))

    return labels


def bin_values(values: list[float], bin_edges: list[float]) -> list[list[float]]:
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
