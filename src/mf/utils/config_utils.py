from __future__ import annotations

import os
from pathlib import Path

import tomlkit
import typer
from tomlkit import TOMLDocument

from mf.constants import (
    STATUS_SYMBOLS,
)
from mf.utils.normalizers import normalize_media_extension, normalize_path

from .console import console, print_error, print_ok, print_warn
from .default_config import default_cfg

__all__ = [
    "get_config_file",
    "write_default_config",
    "read_config",
    "write_config",
    "get_validated_search_paths",
    "add_search_path",
    "remove_search_path",
    "get_media_extensions",
    "add_media_extension",
    "remove_media_extension",
    "normalize_media_extension",
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


def add_search_path(cfg: TOMLDocument, path_str: str) -> TOMLDocument:
    """Add a search path to the configuration.

    Args:
        cfg (TOMLDocument): Current configuration.
        path_str (str): Path to add.

    Returns:
        TOMLDocument: Updated configuration.
    """
    path_str = normalize_path(path_str)

    if path_str not in cfg["search_paths"]:
        if not Path(path_str).exists():
            print_warn(f"Path '{path_str}' does not exist (storing anyway).")

        cfg["search_paths"].append(path_str)
        print_ok(f"Added search path: '{path_str}'.")
    else:
        print_warn(
            f"Search path '{path_str}' already stored in configuration file, skipping."
        )

    return cfg


def remove_search_path(cfg: TOMLDocument, path_str: str) -> TOMLDocument:
    """Remove a search path.

    Args:
        cfg (TOMLDocument): Current configuration.
        path_str (str): Path to remove.

    Raises:
        typer.Exit: If the path is not configured.

    Returns:
        TOMLDocument: Updated configuration with path removed.
    """
    path_str = normalize_path(path_str)
    try:
        cfg["search_paths"].remove(path_str)
        print_ok(f"Removed search path: '{path_str}'.")
        return cfg
    except ValueError:
        print_error(f"Path '{path_str}' not found in configuration file.")
        raise typer.Exit(1)


def add_media_extension(cfg: TOMLDocument, extension: str) -> TOMLDocument:
    """Add a media extension.

    Args:
        cfg (TOMLDocument): Current configuration.
        extension (str): Extension to add.

    Returns:
        TOMLDocument: Updated configuration.
    """
    normalized = normalize_media_extension(extension)
    if normalized not in cfg["media_extensions"]:
        cfg["media_extensions"].append(normalized)
        print_error(f"Added media extension '{normalized}'.")
    else:
        print_warn(
            f"Extension '{normalized}' already stored in configuration, skipping."
        )
    return cfg


def remove_media_extension(cfg: TOMLDocument, extension: str) -> TOMLDocument:
    """Remove a media extension.

    Args:
        cfg (TOMLDocument): Current configuration.
        extension (str): Extension to remove.

    Raises:
        typer.Exit: If the extension is not configured.

    Returns:
        TOMLDocument: Updated configuration.
    """
    extension = normalize_media_extension(extension)
    if extension in cfg["media_extensions"]:
        cfg["media_extensions"].remove(extension)
        console.print(
            f"{STATUS_SYMBOLS['ok']}  Extension '{extension}' removed from configuration.",
            style="green",
        )
        return cfg
    console.print(
        f"{STATUS_SYMBOLS['error']} Extension '{extension}' not found in configuration.",
        style="red",
    )
    raise typer.Exit(1)


def get_media_extensions() -> set[str]:
    """Retrieve configured media extensions.

    Args:
        None

    Returns:
        set[str]: Set of normalized extensions.
    """
    return {normalize_media_extension(e) for e in read_config()["media_extensions"]}
