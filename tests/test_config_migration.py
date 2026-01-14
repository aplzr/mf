"""Tests for configuration migration functionality."""

from pathlib import Path

import pytest
import tomlkit
from tomlkit import document

from mf.utils.config import (
    _read_config,
    add_default_setting,
    get_raw_config,
    migrate_config,
    write_config,
    Configuration
)
from mf.utils.file import get_config_file
from mf.utils.settings import SETTINGS


# --- Unit tests for migrate_config() ---


def test_migrate_config_adds_missing_settings(isolated_config):
    """Verify all REGISTRY settings are added when missing."""
    # Create config with only search_paths
    cfg = document()
    cfg["search_paths"] = ["/test/path"]

    # Migrate
    modified = migrate_config(cfg)

    # Assert all REGISTRY settings present
    assert modified
    for setting in SETTINGS:
        assert setting in cfg


def test_migrate_config_preserves_existing_settings(isolated_config):
    """Existing settings should remain unchanged."""
    # Create config with custom value
    cfg = document()
    cfg["search_paths"] = ["/custom/path"]
    cfg["display_paths"] = False

    # Migrate
    modified = migrate_config(cfg)

    # Assert existing settings preserved
    assert cfg["search_paths"] == ["/custom/path"]
    assert cfg["display_paths"] is False


def test_migrate_config_no_changes_when_complete(isolated_config):
    """Returns modified=False if config is complete."""
    # Create complete config with all REGISTRY settings
    cfg = document()
    for setting in SETTINGS:
        add_default_setting(cfg, setting)

    # Migrate
    modified = migrate_config(cfg)

    # Assert no modification
    assert not modified


def test_migrate_config_empty_config(isolated_config):
    """Handles empty config file by adding all settings."""
    # Create empty config
    cfg = document()

    # Migrate
    modified = migrate_config(cfg)

    # Assert all REGISTRY settings added
    assert modified
    for setting in SETTINGS:
        assert setting in cfg


def test_migrate_config_adds_comments(isolated_config):
    """Help text appears as comments for new settings."""
    # Create config missing one setting
    cfg = document()
    for setting in list(SETTINGS.keys())[:-1]:  # Add all but last
        cfg[setting] = SETTINGS[setting].default

    # Migrate
    modified = migrate_config(cfg)

    # Assert modified
    assert modified

    # Convert to string and check for help text
    cfg_str = tomlkit.dumps(cfg)
    last_setting = list(SETTINGS.keys())[-1]
    help_text = SETTINGS[last_setting].help

    # Help text should appear in comments
    assert help_text[:20] in cfg_str  # Check first 20 chars of help


def test_migrate_config_preserves_formatting(isolated_config):
    """Custom comments/formatting should be preserved."""
    # Create config with custom comment
    cfg = document()
    cfg.add(tomlkit.comment("My custom comment"))
    cfg.add(tomlkit.nl())
    cfg["search_paths"] = ["/my/path"]
    cfg.add(tomlkit.nl())

    # Capture original TOML (first 3 lines)
    original_lines = tomlkit.dumps(cfg).splitlines()[:3]

    # Migrate
    modified = migrate_config(cfg)

    # Verify modification
    assert modified

    # Verify original content preserved
    migrated_lines = tomlkit.dumps(cfg).splitlines()
    assert "# My custom comment" in tomlkit.dumps(cfg)
    assert migrated_lines[:3] == original_lines


def test_migrate_config_idempotent(isolated_config):
    """Running twice has no additional effect."""
    # Create incomplete config
    cfg = document()
    cfg["search_paths"] = []

    # First migration
    modified1 = migrate_config(cfg)
    assert modified1

    # Second migration
    modified2 = migrate_config(cfg)
    assert not modified2


def test_migrate_config_library_cache_interval_old_format(isolated_config):
    """Migrate library_cache_interval from old string format to new int format."""
    # Create config with old format
    cfg = document()
    for setting in SETTINGS:
        if setting != "library_cache_interval":
            add_default_setting(cfg, setting)

    # Add library_cache_interval in old format
    cfg["library_cache_interval"] = "1d"  # Old format: "<number><unit>"

    # Migrate
    modified = migrate_config(cfg)

    # Assert migration occurred
    assert modified
    assert cfg["library_cache_interval"] == 86400  # 1 day in seconds


def test_migrate_config_library_cache_interval_new_format(isolated_config):
    """Don't migrate library_cache_interval if already in new format."""
    # Create config with new format
    cfg = document()
    for setting in SETTINGS:
        add_default_setting(cfg, setting)

    cfg["library_cache_interval"] = 3600  # Already in new format (int)

    # Migrate
    modified = migrate_config(cfg)

    # Assert no modification (all settings present, value already correct)
    assert not modified
    assert cfg["library_cache_interval"] == 3600


def test_migrate_config_library_cache_interval_invalid_format(isolated_config):
    """Invalid library_cache_interval format is ignored (suppressed)."""
    # Create config with invalid format
    cfg = document()
    for setting in SETTINGS:
        if setting != "library_cache_interval":
            add_default_setting(cfg, setting)

    cfg["library_cache_interval"] = "invalid"  # Invalid format

    # Migrate (should not crash, should suppress ValueError)
    modified = migrate_config(cfg)

    # Assert value unchanged (migration failed silently)
    assert cfg["library_cache_interval"] == "invalid"







# --- Integration tests for _read_config() ---


def test_read_config_migrates_and_persists(isolated_config):
    """Missing settings should be written to disk."""
    # Write incomplete config to disk
    cfg = document()
    cfg["search_paths"] = ["/test"]
    write_config(cfg)

    # Clear config cache
    import mf.utils.config

    mf.utils.config._config = None

    # Read config (should migrate)
    loaded_cfg = get_raw_config()

    # Assert all settings present in memory
    for setting in SETTINGS:
        assert setting in loaded_cfg

    # Clear cache and read from disk again
    mf.utils.config._config = None
    disk_cfg = get_raw_config()

    # Assert all settings persisted to disk
    for setting in SETTINGS:
        assert setting in disk_cfg


def test_read_config_handles_corrupted_toml(isolated_config, capsys):
    """Backup created, fresh config written for corrupted TOML."""
    config_file = get_config_file()

    # Write invalid TOML
    with open(config_file, "w") as f:
        f.write("invalid toml content {{{")

    # Clear config cache
    import mf.utils.config

    mf.utils.config._config = None

    # Read config (should handle corruption)
    cfg = get_raw_config()

    # Assert backup file created
    backup_path = config_file.with_suffix(".toml.backup")
    assert backup_path.exists()

    # Assert fresh default config created
    for setting in SETTINGS:
        assert setting in cfg

    # Assert warning message shown
    captured = capsys.readouterr()
    assert "corrupted" in captured.out.lower()
    assert "backup" in captured.out.lower()


# --- End-to-end tests ---


def test_cli_works_with_migrated_config(isolated_config):
    """CLI commands work after migration."""
    from typer.testing import CliRunner

    from mf.cli_config import app_config

    # Write incomplete config
    cfg = document()
    cfg["search_paths"] = []
    write_config(cfg)

    # Clear config cache
    import mf.utils.config

    mf.utils.config._config = None

    # Run CLI command
    runner = CliRunner()
    result = runner.invoke(app_config, ["list"])

    # Assert command succeeds
    assert result.exit_code == 0

    # Assert all settings visible
    for setting in SETTINGS:
        assert setting in result.stdout


def test_build_config_after_migration(isolated_config):
    """Configuration object has all attributes after migration."""
    # Write incomplete config
    cfg = document()
    cfg["search_paths"] = ["/test"]
    write_config(cfg)

    # Clear config cache
    import mf.utils.config

    mf.utils.config._config = None

    # Build config (should migrate first)
    config_obj = Configuration.from_config()

    # Assert no errors and all attributes present
    for setting in SETTINGS:
        assert hasattr(config_obj, setting)
        assert config_obj[setting] is not None


# --- Backward compatibility test ---


def test_upgrade_scenario(isolated_config):
    """Simulate old config missing new settings, verify auto-upgrade."""
    # Simulate old config with only original settings
    # (e.g., missing newly added settings like auto_wildcards, parallel_search, etc.)
    old_settings = ["search_paths", "media_extensions"]

    cfg = document()
    for setting in old_settings:
        if setting in SETTINGS:
            cfg[setting] = SETTINGS[setting].default

    write_config(cfg)

    # Clear config cache
    import mf.utils.config

    mf.utils.config._config = None

    # Access config (should auto-upgrade)
    loaded_cfg = get_raw_config()

    # Assert all REGISTRY settings present (old + new)
    for setting in SETTINGS:
        assert setting in loaded_cfg

    # Verify file was updated
    mf.utils.config._config = None
    disk_cfg = get_raw_config()

    for setting in SETTINGS:
        assert setting in disk_cfg

    # Verify old settings preserved
    for setting in old_settings:
        if setting in SETTINGS:
            assert disk_cfg[setting] == SETTINGS[setting].default
