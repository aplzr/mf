"""Console output utilities for user-facing messages.

Provides consistent, styled output for the CLI using Rich formatting.
All messages use status symbols (✓, ⚠, ❌, ℹ) and semantic colors.

Functions:
    print_ok: Success/confirmation messages (green)
    print_warn: Warning messages (yellow)
    print_info: Informational messages (cyan)
    print_and_raise: Error messages with exit (red, never returns)

Console Instance:
    Shared Rich console instance to avoid re-initialization overhead.
    Used throughout the application for consistent styling.

Error Handling Strategy:
    Utilities should catch exceptions and use print_and_raise() to convert
    them to user-friendly messages. This ensures users see helpful error
    messages instead of Python tracebacks.

    Pattern:
        try:
            # operation that might fail
        except SpecificError as e:
            print_and_raise("User-friendly message", raise_from=e)

    This:
    1. Shows friendly message to user (no traceback)
    2. Preserves exception chain for debugging
    3. Exits cleanly with code 1
    4. Provides consistent error formatting

Examples:
    >>> print_ok("Configuration saved successfully")
    ✓ Configuration saved successfully

    >>> print_warn("Cache is outdated, rebuilding...")
    ⚠ Cache is outdated, rebuilding...

    >>> print_and_raise("File not found", raise_from=FileNotFoundError())
    ❌ File not found
    # Exits with code 1
"""

from __future__ import annotations

from typing import NoReturn

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


def print_columns(panels: list[Panel], n_columns: int, padding: tuple[int, int]):
    """Print a collection of Panels in a multi-column layout.

    Panels are distributed alternatingly between columns, i.e. row-first.

    Args:
        panels (list[Panel]): List of panels to print.
        n_columns (int): Number of columns.
        padding (tuple[int, int]): (vertical, horizontal) padding between columns.
    """
    columns: list[list[Panel]] = [[] for _ in range(n_columns)]

    for i, panel in enumerate(panels):
        columns[i % n_columns].append(panel)

    column_groups = [Group(*column) for column in columns]
    console.print(Columns(column_groups, padding=padding))
