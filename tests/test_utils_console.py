"""Tests for console utilities."""

import pytest
from rich.panel import Panel
from typer import Exit

from mf.utils.console import print_columns, print_and_raise, print_info


def test_print_columns_runs_without_error():
    """Test that print_columns executes without error."""
    panels = [
        Panel("Content 1", title="Panel 1"),
        Panel("Content 2", title="Panel 2"),
        Panel("Content 3", title="Panel 3"),
        Panel("Content 4", title="Panel 4"),
    ]

    # Should not raise any errors
    print_columns(panels, n_columns=2, padding=(0, 1))


def test_print_columns_single_column():
    """Test print_columns with single column."""
    panels = [
        Panel("Content 1"),
        Panel("Content 2"),
        Panel("Content 3"),
    ]

    # Should not raise any errors
    print_columns(panels, n_columns=1, padding=(1, 1))


def test_print_columns_more_columns_than_panels():
    """Test print_columns when n_columns > number of panels."""
    panels = [
        Panel("Content 1"),
        Panel("Content 2"),
    ]

    # Should not raise any errors with 3 columns but only 2 panels
    print_columns(panels, n_columns=3, padding=(0, 1))


def test_print_columns_empty_panels():
    """Test print_columns with empty panel list."""
    panels = []

    # Should handle empty list gracefully
    print_columns(panels, n_columns=2, padding=(0, 1))


def test_print_columns_distribution():
    """Test that panels are distributed correctly across columns.

    This tests the distribution logic by verifying the round-robin pattern.
    Panels should be distributed as: col0=[0,2,4], col1=[1,3,5] for 2 columns.
    """
    # We can't easily verify the internal distribution without looking at output,
    # but we can at least verify it runs with various panel counts and column counts

    test_cases = [
        (5, 2),   # 5 panels, 2 columns -> [0,2,4], [1,3]
        (7, 3),   # 7 panels, 3 columns -> [0,3,6], [1,4], [2,5]
        (10, 4),  # 10 panels, 4 columns -> [0,4,8], [1,5,9], [2,6], [3,7]
    ]

    for n_panels, n_columns in test_cases:
        panels = [Panel(f"Content {i}") for i in range(n_panels)]
        # Should complete without error
        print_columns(panels, n_columns=n_columns, padding=(0, 1))


def test_print_info_runs_without_error():
    """Test that print_info executes without error."""
    # Should not raise any errors
    print_info("This is an informational message")


def test_print_and_raise_exits_with_code_1():
    """Test that print_and_raise raises Exit with code 1."""
    with pytest.raises(Exit) as exc_info:
        print_and_raise("Error message")

    # Verify it exits with code 1
    assert exc_info.value.exit_code == 1


def test_print_and_raise_with_exception_chain():
    """Test that print_and_raise preserves exception chain."""
    original_error = ValueError("Original error")

    with pytest.raises(Exit) as exc_info:
        print_and_raise("Friendly error message", raise_from=original_error)

    # Verify it exits with code 1
    assert exc_info.value.exit_code == 1
    # Verify exception chain is preserved
    assert exc_info.value.__cause__ is original_error
