"""Input normalization utilities for user-provided values.

Provides functions to normalize and validate user input before storing in
configuration or using in operations. All normalization is non-destructive and
follows consistent conventions.

Normalization Functions:
    normalize_bool_str: Convert string literals to boolean values
    normalize_path: Convert relative paths to absolute POSIX-style
    normalize_media_extension: Ensure extensions have leading dot and lowercase
    normalize_pattern: Auto-wrap patterns without wildcards with *pattern*
    normalize_bool_to_toml: Convert boolean to TOML representation

Conventions:
    - Booleans: Accept true/false, yes/no, y/n, on/off, 1/0, enable/disable
    - Paths: Always absolute and POSIX-style (forward slashes)
    - Extensions: Always lowercase with leading dot (.mkv not mkv)
    - Patterns: Auto-wrapped if no glob characters [*?[]] present
"""

from __future__ import annotations

from pathlib import Path

from ..constants import BOOLEAN_FALSE_VALUES, BOOLEAN_TRUE_VALUES
from .console import print_and_raise

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

    print_and_raise(
        f"Invalid boolean value. Got: '{bool_str}'. Expected one of: {{}}.".format(
            ", ".join(
                repr(item)
                for item in sorted(BOOLEAN_TRUE_VALUES | BOOLEAN_FALSE_VALUES)
            )
        )
    )


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
        print_and_raise("Extension can't be empty after normalization.")

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


def normalize_bool_to_toml(bool_: bool) -> str:
    """Normalize bool value to a TOML-like string representation.

    Args:
        bool_ (bool): Boolean value.

    Returns:
        str: TOML-like representation.
    """
    return str(bool_).lower()
