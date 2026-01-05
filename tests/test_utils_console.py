"""Tests for console utilities."""

import pytest
from rich.panel import Panel
from typer import Exit

from mf.utils.console import print_and_raise, print_info


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
