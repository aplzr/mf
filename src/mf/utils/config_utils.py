from __future__ import annotations

import os
from pathlib import Path

import tomlkit
import typer
from tomlkit import TOMLDocument

from .console import console

__all__ = [
    "get_config_file",
    "write_default_config",
    "read_config",
    "write_config",
    "normalize_path",
    "get_validated_search_paths",
    "add_search_path",
    "remove_search_path",
    "get_media_extensions",
    "add_media_extension",
    "remove_media_extension",
    "normalize_media_extension",
    "normalize_bool_str",
]


def get_config_file() -> Path:
    """Return path to config file (platform aware, fallback to ~/.config/mf)."""
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
    """Write and return default configuration file with initial settings."""
    # fmt: off
    default_cfg = tomlkit.document()
    default_cfg.add(tomlkit.comment("Media file search paths"))
    default_cfg.add("search_paths", [])
    default_cfg.add(tomlkit.nl())
    default_cfg.add(tomlkit.comment("Media file extensions matched by 'mf find' and 'mf new'."))
    default_cfg.add("media_extensions", ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'])
    default_cfg.add(tomlkit.nl())
    default_cfg.add(tomlkit.comment("If true, 'mf find' and 'mf new' will only return results that match one of the file extensions"))
    default_cfg.add(tomlkit.comment("defined by media_extensions. Otherwise all files found in the search paths will be returned."))
    default_cfg.add(tomlkit.comment("Set to false if your search paths only contain media files and you don't want to manage media"))
    default_cfg.add(tomlkit.comment("extensions."))
    default_cfg.add("match_extensions", True)
    # fmt: on
    write_config(default_cfg)
    console.print(
        f"✔  Written default configuration to '{get_config_file()}'.", style="green"
    )
    return default_cfg


def read_config() -> TOMLDocument:
    """Load configuration or create default if missing."""
    try:
        with open(get_config_file()) as f:
            cfg = tomlkit.load(f)
    except FileNotFoundError:
        console.print(
            "⚠  Configuration file doesn't exist, creating it with default settings.",
            style="yellow",
        )
        cfg = write_default_config()
    return cfg


def write_config(cfg: TOMLDocument):
    """Persist configuration back to disk."""
    with open(get_config_file(), "w") as f:
        tomlkit.dump(cfg, f)


def normalize_path(path_str: str) -> str:
    return Path(path_str).resolve().as_posix()


def get_validated_search_paths() -> list[Path]:
    search_paths = read_config()["search_paths"]
    validated: list[Path] = []
    for search_path in search_paths:
        p = Path(search_path)
        if not p.exists():
            console.print(
                f"⚠  Configured search path {search_path} does not exist.",
                style="yellow",
            )
        else:
            validated.append(p)
    if not validated:
        console.print(
            "❌ List of search paths is empty or paths don't exist. Set search paths with 'mf config set search_paths'.",
            style="red",
        )
        raise typer.Exit(1)
    return validated


def add_search_path(cfg: TOMLDocument, path_str: str) -> TOMLDocument:
    path_str = normalize_path(path_str)
    if path_str not in cfg["search_paths"]:
        if not Path(path_str).exists():
            console.print(
                f"⚠  Path '{path_str}' does not exist (storing anyway).", style="yellow"
            )
        cfg["search_paths"].append(path_str)
        console.print(f"✔  Added search path: '{path_str}'", style="green")
    else:
        console.print(
            f"⚠  Search path '{path_str}' already stored in configuration file, skipping.",
            style="yellow",
        )
    return cfg


def remove_search_path(cfg: TOMLDocument, path_str: str) -> TOMLDocument:
    path_str = normalize_path(path_str)
    try:
        cfg["search_paths"].remove(path_str)
        console.print(f"✔  Removed search path: '{path_str}'", style="green")
        return cfg
    except ValueError:
        console.print(
            f"❌ Path '{path_str}' not found in configuration file.", style="red"
        )
        raise typer.Exit(1)


def normalize_media_extension(extension: str) -> str:
    if not extension:
        raise ValueError("Extension can't be empty.")
    extension = extension.lower().strip().lstrip(".")
    if not extension:
        console.print("❌ Extension can't be empty after normalization.", style="red")
        raise typer.Exit(1)
    return "." + extension


def add_media_extension(cfg: TOMLDocument, extension: str) -> TOMLDocument:
    normalized = normalize_media_extension(extension)
    if normalized not in cfg["media_extensions"]:
        cfg["media_extensions"].append(normalized)
        console.print(f"✔  Added media extension '{normalized}'.", style="green")
    else:
        console.print(
            f"⚠  Extension '{normalized}' already stored in configuration, skipping.",
            style="yellow",
        )
    return cfg


def remove_media_extension(cfg: TOMLDocument, extension: str) -> TOMLDocument:
    extension = normalize_media_extension(extension)
    if extension in cfg["media_extensions"]:
        cfg["media_extensions"].remove(extension)
        console.print(
            f"✔  Extension '{extension}' removed from configuration.", style="green"
        )
        return cfg
    console.print(
        f"❌ Extension '{extension}' not found in configuration.", style="red"
    )
    raise typer.Exit(1)


def get_media_extensions() -> set[str]:
    return {normalize_media_extension(e) for e in read_config()["media_extensions"]}


def normalize_bool_str(bool_str: str) -> bool:
    bool_str = bool_str.strip().lower()
    TRUE_VALUES = {"1", "true", "yes", "y", "on", "enable", "enabled"}
    FALSE_VALUES = {"0", "false", "no", "n", "off", "disable", "disabled"}
    if bool_str in TRUE_VALUES:
        return True
    if bool_str in FALSE_VALUES:
        return False
    console.print(
        f"❌  Invalid boolean value. Got: '{bool_str}'. Expected one of:",
        ", ".join(repr(item) for item in sorted(TRUE_VALUES | FALSE_VALUES)),
        style="red",
    )
    raise typer.Exit(1)
