"""Console output utilities for user-facing messages and layouts.

Provides consistent, styled output for the CLI using Rich formatting.
Includes message printing functions with semantic colors and a flexible
multi-column layout system for Rich Panel objects.

Message Functions:
    print_ok: Success/confirmation messages (green with ✓)
    print_warn: Warning messages (yellow with ⚠)
    print_info: Informational messages (cyan with ℹ)
    print_and_raise: Error messages that exit (red with ❌)

Console Instance:
    Shared Rich console instance used throughout the application
    for consistent styling and output.

Layout System:
    PanelFormat: Immutable configuration for panel appearance (width, padding,
        alignment). Created automatically by ColumnLayout.from_terminal() to ensure
        consistent formatting across all panels in a layout.

    ColumnLayout: Builder for multi-column panel layouts. Automatically calculates
        optimal column count based on terminal width, accumulates panels via
        add_panel(), and renders them in a responsive grid via print().

    Usage Pattern:
        1. Create layout from terminal dimensions
        2. Extract panel format for histogram creation
        3. Add panels to layout
        4. Print all panels in multi-column grid

    The layout system automatically:
        - Detects terminal width and calculates optimal column count
        - Enforces minimum/maximum panel widths for readability
        - Distributes panels across columns (row-first)
        - Handles responsive layout with configurable spacing

Error Handling Strategy:
    Utilities should catch exceptions and use print_and_raise() to convert
    them to user-friendly messages instead of showing Python tracebacks.

    Pattern:
        try:
            # operation that might fail
        except SpecificError as e:
            print_and_raise("User-friendly message", raise_from=e)

    Benefits:
        - Shows friendly message to user (no traceback)
        - Preserves exception chain for debugging
        - Exits cleanly with code 1
        - Provides consistent error formatting

Examples:
    Message printing:
        >>> print_ok("Configuration saved successfully")
        ✓ Configuration saved successfully

        >>> print_warn("Cache is outdated, rebuilding...")
        ⚠ Cache is outdated, rebuilding...

        >>> print_and_raise("File not found", raise_from=FileNotFoundError())
        ❌ File not found
        # Exits with code 1

    Multi-column panel layout:
        >>> from rich.panel import Panel
        >>> layout = ColumnLayout.from_terminal()
        >>> format = layout.panel_format
        >>>
        >>> layout.add_panel(Panel("Content 1", title="Panel 1"))
        >>> layout.add_panel(Panel("Content 2", title="Panel 2"))
        >>> layout.add_panel(Panel("Content 3", title="Panel 3"))
        >>> layout.print()  # Renders panels in responsive multi-column grid
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from typing import Literal, NoReturn

import typer
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel

from ..constants import STATUS_SYMBOLS

__all__ = [
    "console",
    "print_and_raise",
    "print_info",
    "print_ok",
    "print_warn",
]

COLUMNLAYOUT_MAX_COLUMNS = 5

# Shared console instance for the project
console = Console()


def print_ok(msg: str):
    """Print confirmation message.

    Args:
        msg (str): Confirmation message.
    """
    console.print(f"{STATUS_SYMBOLS['ok']}  {msg}", style="green")


def print_warn(msg: str):
    """Print warning message.

    Args:
        msg (str): Warning message.
    """
    console.print(f"{STATUS_SYMBOLS['warn']}  {msg}", style="yellow")


def print_and_raise(msg: str, raise_from: Exception | None = None) -> NoReturn:
    """Print error message and exit with status 1.

    Args:
        msg (str): Error message.
        raise_from (Exception | None, optional): Caught exception to raise from.
            Defaults to None.
    """
    console.print(f"{STATUS_SYMBOLS['error']} {msg}", style="red")

    raise typer.Exit(1) from raise_from


def print_info(msg: str):
    """Print info message.

    Args:
        msg (str): Info message.
    """
    console.print(f"{STATUS_SYMBOLS['info']}  {msg}", style="bright_cyan")


@dataclass(frozen=True)
class PanelFormat:
    """Immutable configuration for Rich Panel formatting.

    Defines the visual appearance of panels including width, internal padding,
    and title alignment. Typically created by ColumnLayout.from_terminal() to
    ensure consistent formatting across multiple panels.

    Attributes:
        panel_width: Width of panel content area in characters.
        padding: (vertical, horizontal) internal padding within panels.
        title_align: Alignment of panel titles.
    """

    panel_width: int
    padding: tuple[int, int] = (1, 1)
    title_align: Literal["left", "center", "right"] = "left"


@dataclass
class ColumnLayout:
    """Mutable builder for multi-column panel layouts.

    Accumulates Rich Panel objects and renders them in a responsive multi-column
    grid. The layout automatically distributes panels across columns (row-first)
    and adapts to terminal width constraints.

    Usage:
        Create layout from terminal dimensions, add panels, then print:

        >>> layout = ColumnLayout.from_terminal()
        >>> layout.add_panel(make_histogram(bins, "Title", layout.format))
        >>> layout.add_panel(Panel("More content"))
        >>> layout.print()

    Attributes:
        n_columns: Number of columns to render panels in.
        panel_format: Immutable PanelFormat configuration for panel appearance.
        terminal_width: Detected terminal width in characters, or None.
        panels: Read-only list of accumulated panels.
    """

    n_columns: int
    panel_format: PanelFormat
    terminal_width: int | None = None
    _panels: list[Panel] = field(default_factory=list, repr=False)

    @property
    def panels(self):  # noqa: D102
        return self._panels

    @staticmethod
    def from_terminal(
        max_columns: int = COLUMNLAYOUT_MAX_COLUMNS,
        min_width: int = 39,
        max_width: int = 80,
        padding: tuple[int, int] = (1, 1),
        title_align: Literal["left", "center", "right"] = "left",
    ) -> ColumnLayout:
        """Create layout optimized for current terminal width.

        Determines optimal column count and panel width to maximize terminal space while
        respecting min/max width constraints. Prioritizes more columns over wider
        panels.

        Args:
            max_columns (int, optional): Maximum panels to display side by side.
                Defaults to 5.
            min_width (int, optional): Minimum panel width in characters. Defaults to
                39.
            max_width (int, optional): Maximum panel width in characters. Defaults to
                80.
            padding (tuple[int, int], optional): (vertical, horizontal) padding inside
                panels and between panels.
                Defaults to (1, 1).
            title_align (Literal["left", "center", "right"], optional): Title alignment
                of panels formatted by the layout. Defaults to "left".

        Returns:
            ColumnLayout: Responsive layout for current terminal dimensions.

        Example:
            >>> layout = ColumnLayout.from_terminal(max_columns=3, min_width=50)
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

                return ColumnLayout(
                    n_columns=n_columns,
                    panel_format=PanelFormat(
                        panel_width=panel_width,
                        padding=padding,
                        title_align=title_align,
                    ),
                    terminal_width=terminal_width,
                )

        # Fallback
        return ColumnLayout(
            n_columns=1,
            panel_format=PanelFormat(
                panel_width=min_width,
                padding=padding,
                title_align=title_align,
            ),
            terminal_width=terminal_width,
        )

    def add_panel(self, panel: Panel | list[Panel]):
        """Add panel(s) to the layout.

        Args:
            panel (Panel | list[Panel]): Panel(s) to add.
        """
        if isinstance(panel, Panel):
            self._panels.append(panel)
            return

        self._panels.extend(panel)

    def print(self):
        """Print layout."""
        console.print(self._distribute_panels())

    def _distribute_panels(self) -> Columns:
        """Distribute panels among columns using a greedy best-fit algorithm.

        Panels are sorted by height, then iteratively placed in the column that
        currently has the smallest height. This produces a pseudo-even distribution
        of column heights as the outcome.

        Returns:
            Columns: Grouped panels, pseudo-evenly distributed by height.
        """
        if any(panel.height is None for panel in self.panels):
            raise ValueError("Can't distribute panels: some panels have no height set.")

        sorted_panels = sorted(self.panels, key=lambda panel: -panel.height)

        columns: list[list[Panel]] = [[] for _ in range(self.n_columns)]
        column_heights: list[int] = [0] * self.n_columns

        for panel in sorted_panels:
            min_idx = column_heights.index(min(column_heights))
            columns[min_idx].append(panel)
            column_heights[min_idx] += panel.height

        return Columns(
            [Group(*column) for column in columns],
            padding=self.panel_format.padding,
        )
