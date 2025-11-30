from collections import Counter
from collections.abc import Callable
from typing import Any

from rich.panel import Panel

from .console import console


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
    produce the historam, where each tuple produces a histogram bar.

    Args:
        items (list[[str]): Data whose distribution should be shown.
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
