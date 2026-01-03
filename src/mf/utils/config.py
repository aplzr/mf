"""Configuration management.

Provides TOML-based configuration with automatic creation, migration, and type
conversion.

Architecture:
    Two-tier access pattern:
    1. get_config() → Raw TOMLDocument for low-level access
       - Returns the TOML document as-is (strings, lists, ints)
       - Use when you need to modify and write config back to disk
       - Use when you need the exact TOML representation

    2. build_config() → Typed Configuration for application use
       - Converts TOML values to proper Python types (Path, timedelta, etc.)
       - Use for reading configuration values
       - Provides attribute and dict access to settings

    Flow: TOML file → cached TOMLDocument → Configuration (with type conversion)

Caching:
    Configuration is loaded once per process and cached in memory. Since this is
    a CLI tool that exits after each command, the cache naturally clears on exit.
    No thread safety needed.

Error Handling:
    - Missing config: Creates default configuration automatically
    - Corrupted config: Backs up to .toml.backup, creates new default
    - Missing settings: Silently migrates by adding defaults from registry
    - Old formats: Automatically converts to current format

Migration:
    Configurations are automatically migrated when loaded. Changes include:
    - Format conversions (e.g., duration strings → integer seconds)
    - New settings added by an application update since config was last written

Configuration Object:
    Provides dual access patterns:
    - Attribute access: config.video_player
    - Dictionary access: config["video_player"]
    Settings are dynamically added from SETTINGS registry, providing runtime
    type safety via from_toml() conversion functions.

Example:
    >>> # Typed access (recommended for reading values)
    >>> config = build_config()
    >>> player = config.video_player
    >>> paths = config.search_paths  # Already converted to Path objects

    >>> # Raw access (for modifying and writing)
    >>> cfg = get_config()
    >>> cfg["video_player"] = "mpv"
    >>> write_config(cfg)
"""

from __future__ import annotations

from contextlib import suppress
from textwrap import wrap
from typing import Any

import tomlkit
from rich.panel import Panel
from rich.table import Column, Table
from tomlkit import TOMLDocument, comment, document, nl
from tomlkit.exceptions import ParseError, TOMLKitError

from .console import console, print_ok, print_warn
from .file import get_config_file, open_utf8
from .parsers import parse_timedelta_str
from .settings import SETTINGS, SettingSpec

_config = None


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
    except (TOMLKitError, ParseError):
        # Configuration file is corrupted, back up and write default configuration.
        config_file = get_config_file()
        backup_path = config_file.with_suffix(".toml.backup")
        print_warn(
            f"Configuration file is corrupted, backing up to '{backup_path}' "
            "and writing default configuration."
        )
        config_file.rename(backup_path)
        cfg = write_default_config()
        return cfg

    # Migrate missing settings silently
    modified = migrate_config(cfg)

    if modified:
        write_config(cfg)

    return cfg


def get_config() -> TOMLDocument:
    """Get the raw configuration.

    Migrates the loaded configuration by adding missing keys with default values if
    necessary. Falls back to creating a default configuration when the file is missing.
    Caches the configuration on first read from disk and returns the cached instance on
    subsequent calls to avoid unnecessary disk reads.

    Returns:
        TOMLDocument: Parsed configuration.
    """
    global _config

    if _config is None:
        _config = _read_config()

    return _config


def _clear_config_cache():
    global _config
    _config = None


def reload_config() -> TOMLDocument:
    """Reloads the configuration from disk and updates the cached configuration
    instance.

    Returns:
        TOMLDocument: Parsed configuration.
    """
    _clear_config_cache()
    return get_config()


def build_config() -> Configuration:
    """Build integrated Configuration from the raw TOML configuration.

    Transforms raw TOML into typed python values.

    Returns:
        Configuration: Configuration object with settings as attributes.
    """
    return Configuration(get_config(), SETTINGS)


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

    def __getitem__(self, key: str) -> Any:  # noqa: D105
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any):  # noqa: D105
        setattr(self, key, value)


def add_default_setting(cfg: TOMLDocument, key: str):
    """Add setting with default value to the configuration (in-place).

    Args:
        cfg (TOMLDocument): mediafinder configuration.
        key (str): Setting name as defined in the registry.
    """
    spec = SETTINGS[key]

    for line in wrap(spec.help, width=80):
        cfg.add(comment(line))

    cfg.add(key, spec.default)
    cfg.add(nl())


def get_default_cfg() -> TOMLDocument:
    """Get the default configuration.

    Builds the default configuration from the settings registry.

    Returns:
        TOMLDocument: Default configuration.
    """
    default_cfg = document()

    for setting in SETTINGS:
        add_default_setting(default_cfg, setting)

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


def migrate_config(cfg: TOMLDocument) -> bool:
    """Migrate configuration by updating settings and adding missing settings from the
    registry (in-place).

    Args:
        cfg (TOMLDocument): Configuration to migrate.

    Returns:
        bool: True if configuration was modified in-place, false otherwise.
    """
    modified = False

    # Before it got simplified to a value in seconds, the library_cache_interval setting
    # was of the format "<number><unit>", with unit one of s, m, h, d, w. Migrate to new
    # format if necessary.
    key_interval = "library_cache_interval"

    if key_interval in cfg:
        interval_value = cfg[key_interval]

        if isinstance(interval_value, str):
            with suppress(AttributeError, ValueError):
                # Convert from old to new format
                interval_s = int(parse_timedelta_str(interval_value).total_seconds())

                # Update with old value converted to new format (this will not update
                # the help text comment)
                cfg[key_interval] = interval_s

                modified = True

    # Add missing settings with default values.
    if missing_settings := set(SETTINGS.keys()) - set(cfg.keys()):
        for missing_setting in missing_settings:
            add_default_setting(cfg, missing_setting)

        modified = True

    return modified


def list_settings():
    "List all available settings as defined by the settings registry."
    table = Table(
        Column("Setting", style="cyan", no_wrap=True),
        Column("Type", style="magenta", no_wrap=True),
        Column("Allowed", style="yellow"),
        Column("Actions", style="green"),
        Column("Description", style="white"),
        show_header=True,
        box=None,
        padding=(0, 1),
    )

    for key, spec in SETTINGS.items():
        actions = ", ".join(spec.actions)
        allowed_display = ""

        if spec.allowed_values is not None:
            allowed_display = ", ".join(
                str(allowed_value) for allowed_value in spec.allowed_values
            )

        table.add_row(
            key,
            f"{spec.kind}, {spec.value_type.__name__}",
            allowed_display,
            actions,
            spec.help,
        )

    panel = Panel(
        table,
        title="[bold]Available settings[/bold]",
        title_align="left",
        padding=(1, 1),
    )

    console.print()
    console.print(panel)
