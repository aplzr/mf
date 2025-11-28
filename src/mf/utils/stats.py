from collections import Counter

from rich.panel import Panel

from .console import console
from .file import FileResults


# TODO: Generalize the histogram function
# - Let it accept any list of strings (no counts)
# - Let it count the strings itself
# - Optionally pass a function for sorting
# - Make top_n fully optional (don't limit if None)
def show_histogram(
    items: list[tuple[str, int]],
    title: str,
    top_n: int = 20,
    bar_style: str = "lower_blocks",
):
    """Plot histogram.

    Args:
        items (list[tuple[str, int]]): (Name, count) pairs in descending order.
        title (str): Plot title.
        top_n (int, optional): Only use top n counts. Defaults to 20.
        bar_style (str, optional): Bar style. Defaults to "lower_blocks".
    """
    top_items = items[:top_n]
    max_count = max(count for _, count in top_items)
    total_count = sum(count for _, count in items)
    max_name_len = max(len(item[0]) for item in top_items)

    bar_chars = {
        "solid": "█",
        "thick_line": "━",
        "squares": "■",
        "half_blocks": "▌",
        "lower_blocks": "▆",
        "small_squares": "▪",
    }

    bar_char = bar_chars[bar_style]
    bars = []

    for name, count in top_items:
        percentage = (count / total_count) * 100
        bar_width = int((count / max_count) * 40)
        bar = bar_char * bar_width

        name_display = name if name else "(no name)"
        bars.append(
            f"{name_display:>{max_name_len}} │[bold cyan]{bar:<40}[/bold cyan]│ "
            f"{count:>{len(str(max_count))}} ({percentage:4.1f}%)"
        )

    console.print(
        Panel(
            "\n".join(bars),
            title=(f"[bold cyan]{title} (top {top_n})[/bold cyan]"),
            padding=(1, 2),
            title_align="left",
        )
    )


def count_file_extensions(results: FileResults) -> list[tuple[str, int]]:
    """Count file extensions.

    Args:
        results (FileResults): Files whose extensions should be counted.

    Returns:
        list[tuple[str, int]]: (extension, count) tuples, sorted by count descending and
            extension ascending.
    """
    return sorted(
        Counter(file.suffix for file in results.get_paths()).items(),
        key=lambda x: (-x[1], x[0]),
    )
