from pathlib import Path

import typer

from mf.constants import BOOLEAN_FALSE_VALUES, BOOLEAN_TRUE_VALUES, STATUS_SYMBOLS
from mf.utils.console import console

__all__ = [
    "normalize_bool_str",
    "normalize_media_extension",
    "normalize_path",
    "normalize_pattern",
]


def normalize_bool_str(bool_str: str) -> bool:
    """Normalize a boolean-like string literal.

    Args:
        bool_str (str): User provided value (e.g. 'true', 'yes', '0').

    Raises:
        typer.Exit: If the value is not recognized.

    Returns:
        bool: Parsed boolean value.
    """
    bool_str = bool_str.strip().lower()
    if bool_str in BOOLEAN_TRUE_VALUES:
        return True
    if bool_str in BOOLEAN_FALSE_VALUES:
        return False
    console.print(
        f"{STATUS_SYMBOLS['error']}  Invalid boolean value. Got: '{bool_str}'. Expected one of:",
        ", ".join(
            repr(item) for item in sorted(BOOLEAN_TRUE_VALUES | BOOLEAN_FALSE_VALUES)
        ),
        style="red",
    )
    raise typer.Exit(1)


def normalize_path(path_str: str) -> str:
    """Normalize a path to an absolute POSIX-style string.

    Args:
        path_str (str): Input path (relative or absolute).

    Returns:
        str: Normalized absolute path with forward slashes.
    """
    return Path(path_str).resolve().as_posix()


def normalize_media_extension(extension: str) -> str:
    """Normalize a media file extension.

    Args:
        extension (str): Raw extension (with or without leading dot).

    Raises:
        ValueError: If the initial extension value is empty.
        typer.Exit: If normalization results in empty value.

    Returns:
        str: Normalized extension including leading dot.
    """
    if not extension:
        raise ValueError("Extension can't be empty.")
    extension = extension.lower().strip().lstrip(".")
    if not extension:
        console.print(
            f"{STATUS_SYMBOLS['error']} Extension can't be empty after normalization.",
            style="red",
        )
        raise typer.Exit(1)
    return "." + extension


def normalize_pattern(pattern: str) -> str:
    """Normalize a search pattern.

    Args:
        pattern (str): Raw pattern (may lack wildcards).

    Returns:
        str: Pattern wrapped with * on both sides if no glob characters found.
    """
    if not any(ch in pattern for ch in ["*", "?", "[", "]"]):
        return f"*{pattern}*"
    return pattern
