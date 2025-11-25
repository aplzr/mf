from __future__ import annotations

import os
import re
from datetime import timedelta
from pathlib import Path
from textwrap import wrap

import tomlkit
from tomlkit import TOMLDocument, comment, document, nl

from .console import print_and_raise, print_ok, print_warn
from .normalizers import normalize_media_extension
from .settings import REGISTRY

__all__ = [
    "get_config_file",
    "get_default_cfg",
    "get_media_extensions",
    "get_validated_search_paths",
    "normalize_media_extension",
    "parse_timedelta_str",
    "read_config",
    "write_config",
    "write_default_config",
]

_config = None


def get_config_file() -> Path:
    """Return path to config file.

    Returns:
        Path: Location of the configuration file (platform aware, falls back to
            ~/.config/mf).
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


def _read_config() -> TOMLDocument:
    try:
        with open(get_config_file()) as f:
            cfg = tomlkit.load(f)
    except FileNotFoundError:
        print_warn(
            "Configuration file doesn't exist, creating it with default settings."
        )
        cfg = write_default_config()

    return cfg


def read_config() -> TOMLDocument:
    """Load configuration contents.

    Falls back to creating a default configuration when the file is missing.

    Returns:
        TOMLDocument: Parsed configuration.
    """
    # Load config once per mf invocation
    global _config

    if _config is None:
        _config = _read_config()

    return _config


def get_default_cfg() -> TOMLDocument:
    """Get the default configuration.

    Builds the default configuration from the settings registry.

    Returns:
        TOMLDocument: Default configuration.
    """
    default_cfg = document()

    for setting, spec in REGISTRY.items():
        for line in wrap(spec.help, width=80):
            default_cfg.add(comment(line))

        default_cfg.add(setting, spec.default)
        default_cfg.add(nl())

    return default_cfg


def write_config(cfg: TOMLDocument):
    """Persist configuration to disk.

    Args:
        cfg (TOMLDocument): Configuration object to write.
    """
    with open(get_config_file(), "w") as f:
        tomlkit.dump(cfg, f)


def write_default_config() -> TOMLDocument:
    """Create and persist a default configuration file.

    Returns:
        TOMLDocument: The default configuration document after writing.
    """
    default_cfg = get_default_cfg()
    write_config(default_cfg)
    print_ok(f"Written default configuration to '{get_config_file()}'.")

    return default_cfg


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
        print_and_raise(
            "List of search paths is empty or paths don't exist. "
            "Set search paths with 'mf config set search_paths'."
        )

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
    if interval_str == "0":
        # Special case: 0 without unit
        return timedelta(seconds=0)
    else:
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
