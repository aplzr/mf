from __future__ import annotations

import os
from pathlib import Path
from textwrap import wrap
from typing import Any

import tomlkit
from tomlkit import TOMLDocument, comment, document, nl

from .console import print_ok, print_warn
from .file import open_utf8
from .normalizers import normalize_media_extension
from .settings import REGISTRY, SettingSpec

__all__ = [
    "get_config_file",
    "get_default_cfg",
    "normalize_media_extension",
    "get_config",
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
        with open_utf8(get_config_file()) as f:
            cfg = tomlkit.load(f)
    except FileNotFoundError:
        print_warn(
            "Configuration file doesn't exist, creating it with default settings."
        )
        cfg = write_default_config()

    return cfg


def get_config() -> TOMLDocument:
    """Get the raw configuration.

    Falls back to creating a default configuration when the file is missing.

    Caches the configuration on first read from disk and returns the cached instance on
    subsequent calls to avoid unnecessary disk reads.

    Returns:
        TOMLDocument: Parsed configuration.
    """
    global _config

    if _config is None:
        _config = _read_config()

    return _config


def build_config() -> Configuration:
    """Build integrated Configuration from the raw TOML configuration.

    Transforms raw TOML into typed python values.

    Returns:
        Configuration: Configuration object with settings as attributes.
    """
    return Configuration(get_config(), REGISTRY)


class Configuration:
    """Configuration object with settings as attributes."""

    def __init__(
        self, raw_config: TOMLDocument, settings_registry: dict[str, SettingSpec]
    ):
        """Create Configuration object from raw configuration and settings registry.

        Access setting values by subscription (config["key"] == value) or dot notation
        (config.key == value).

        Args:
            raw_config (TOMLDocument): Raw configuration as loaded from disk.
            settings_registry (dict[str, SettingSpec]): Setting specifications registry
                that defines how to process each setting before making it available.

        """
        self._registry = settings_registry
        self._raw_config = raw_config

        for setting, values in self._raw_config.items():
            spec = self._registry[setting]

            if spec.kind == "list":
                setattr(self, setting, [spec.from_toml(value) for value in values])
            else:
                setattr(self, setting, spec.from_toml(values))

    def __repr__(self) -> str:
        """Return a representation showing all configured settings."""
        # Get all attributes that aren't the registry
        configured_settings = {
            setting: getattr(self, setting)
            for setting in self._registry
            if hasattr(self, setting)
        }
        items = [f"{key}={value!r}" for key, value in configured_settings.items()]
        return f"Configuration({', '.join(items)})"

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any):
        setattr(self, key, value)


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
    with open_utf8(get_config_file(), "w") as f:
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
