from __future__ import annotations

import os
from pathlib import Path
from textwrap import wrap
from typing import Any

import tomlkit
from tomlkit import TOMLDocument, comment, document, nl

from .console import print_and_raise, print_ok, print_warn
from .normalizers import normalize_media_extension
from .settings import REGISTRY, SettingSpec

__all__ = [
    "get_config_file",
    "get_default_cfg",
    "validate_search_paths",
    "normalize_media_extension",
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


def _get_config() -> Configuration:
    global _config

    if _config is None:
        _configuration = Configuration(read_config(), REGISTRY)

    return _configuration


def get_config() -> Configuration:
    """Get configuration as a Configuration object.

    Returns:
        Configuration: Configuration object with settings as attributes.
    """
    return _get_config()


class Configuration:
    """Configuration object with settings as attributes."""

    def __init__(
        self, raw_config: TOMLDocument, settings_registry: dict[str, SettingSpec]
    ):
        """Create Configuration object from raw configigration and settings registry.

        Access setting values by subscription (config["key"] == value) or dot notation
        (config.key == value).

        Args:
            raw_config (TOMLDocument): Raw configuration as loaded from disk.
            settings_registry (dict[str, SettingSpec]): Setting specifications registry
                that defines how to process each setting before making it available.

        """
        self._registry = settings_registry
        self._raw_config = raw_config

        for key, setting in self._raw_config.items():
            # Apply after_read hook and store as attribute for dot notation access
            setting_spec = self._registry[key]
            setattr(self, key, setting_spec.after_read(setting))

    def __repr__(self) -> str:
        """Return a representation showing all configured settings."""
        # Get all attributes that aren't the registry
        configured_settings = {
            setting: getattr(self, setting)
            for setting in self._registry
            if hasattr(self, setting)
        }

        # Format each key-value pair
        items = [f"{key}={value!r}" for key, value in configured_settings.items()]

        return f"Configuration({', '.join(items)})"

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any):
        setattr(self, key, value)

    def to_toml(self) -> TOMLDocument:
        """Convert (possibly updated) Configuration object back to TOMLDocument.

        Returns:
            TOMLDocument: Configuration as TOMLDocument.
        """
        cfg = self._raw_config  # Preserve user-added comments

        for setting, spec in self._registry.items():
            value = getattr(self, setting)
            cfg[setting] = spec.before_write(value)

        return cfg


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


def validate_search_paths() -> list[Path]:
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
