from collections import Counter

from rich.panel import Panel

from .console import console
from .file import FileResults


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
    # Take top N items
    top_extensions = items[:top_n]
    max_count = max(count for _, count in top_extensions)
    total_count = sum(count for _, count in items)

    # Different bar characters
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

    for ext, count in top_extensions:
        percentage = (count / total_count) * 100
        bar_width = int((count / max_count) * 40)
        bar = bar_char * bar_width

        ext_display = ext if ext else "(no ext)"
        bars.append(
            f"{ext_display:>8} │[bold cyan]{bar:<40}[/bold cyan]│ "
            f"{count:>5} ({percentage:4.1f}%)"
        )

    console.print(
        Panel(
            "\n".join(bars),
            title=(f"[bold cyan]{title} (top {top_n} counts)[/bold cyan]"),
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


def compute_cache_stats(results: FileResults):
    pass
