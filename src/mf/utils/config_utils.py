from __future__ import annotations

import os
import re
from datetime import timedelta
from pathlib import Path

import tomlkit
import typer
from tomlkit import TOMLDocument

from .console import print_error, print_ok, print_warn
from .normalizers import normalize_media_extension
from .settings_registry import default_cfg

__all__ = [
    "get_config_file",
    "write_default_config",
    "read_config",
    "write_config",
    "get_validated_search_paths",
    "get_media_extensions",
    "normalize_media_extension",
    "parse_timedelta_str",
]


def get_config_file() -> Path:
    """Return path to config file.

    Returns:
        Path: Location of the configuration file (platform aware; falls back to
            ~/.config/mf on POSIX).
    """
    config_dir = (
        Path(
            os.environ.get(
                "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME",
                Path.home() / ".config",
            )
        )
        / "mf"
    )
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.toml"


def write_default_config() -> TOMLDocument:
    """Create and persist a default configuration file.

    Returns:
        TOMLDocument: The default configuration document after writing.
    """
    write_config(default_cfg)
    print_ok(f"Written default configuration to '{get_config_file()}'.")

    return default_cfg


def read_config() -> TOMLDocument:
    """Load configuration contents.

    Falls back to creating a default configuration when the file is missing.

    Returns:
        TOMLDocument: Parsed configuration.
    """
    try:
        with open(get_config_file()) as f:
            cfg = tomlkit.load(f)
    except FileNotFoundError:
        print_warn(
            "Configuration file doesn't exist, creating it with default settings."
        )
        cfg = write_default_config()

    return cfg


def write_config(cfg: TOMLDocument):
    """Persist configuration to disk.

    Args:
        cfg (TOMLDocument): Configuration object to write.
    """
    with open(get_config_file(), "w") as f:
        tomlkit.dump(cfg, f)


def get_validated_search_paths() -> list[Path]:
    """Return existing configured search paths.

    Raises:
        typer.Exit: If no valid search paths are configured.

    Returns:
        list[Path]: List of validated existing search paths.
    """
    search_paths = read_config()["search_paths"]
    validated: list[Path] = []

    for search_path in search_paths:
        p = Path(search_path)

        if not p.exists():
            print_warn(f"Configured search path {search_path} does not exist.")
        else:
            validated.append(p)

    if not validated:
        print_error(
            "List of search paths is empty or paths don't exist. "
            "Set search paths with 'mf config set search_paths'."
        )
        raise typer.Exit(1)

    return validated


def get_media_extensions() -> set[str]:
    """Retrieve configured media extensions.

    Args:
        None

    Returns:
        set[str]: Set of normalized extensions.
    """
    return {normalize_media_extension(e) for e in read_config()["media_extensions"]}


def parse_timedelta_str(interval_str: str) -> timedelta:
    """Parse time interval string like '10s', '30m', '2h', '1d', '5w' into timedelta.

    Args:
        interval_str (str): Interval string.

    Raises:
        ValueError: Invalid input.

    Returns:
        timedelta: Parsed time interval.
    """
    pattern = r"^(\d+)([smhdw])$"
    match = re.match(pattern, interval_str.lower().strip())

    if not match:
        raise ValueError(
            f"Invalid time interval format: {interval_str}. "
            "Use format like '30m', '2h', '1d'"
        )

    value, unit = match.groups()
    value = int(value)

    unit_map = {
        "s": timedelta(seconds=value),
        "m": timedelta(minutes=value),
        "h": timedelta(hours=value),
        "d": timedelta(days=value),
        "w": timedelta(weeks=value),
    }

    return unit_map[unit]
