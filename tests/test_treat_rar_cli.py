"""Tests for treat_rar_as_media CLI commands and cache rebuild."""

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from mf.cli_config import app_config
from mf.utils.config import get_raw_config

runner = CliRunner()


def test_set_treat_rar_as_media_true(isolated_config):
    """Test setting treat_rar_as_media to true via CLI."""
    result = runner.invoke(app_config, ["set", "treat_rar_as_media", "true"])
    assert result.exit_code == 0

    cfg = get_raw_config()
    assert cfg["treat_rar_as_media"] is True


def test_set_treat_rar_as_media_false(isolated_config):
    """Test setting treat_rar_as_media to false via CLI."""
    result = runner.invoke(app_config, ["set", "treat_rar_as_media", "false"])
    assert result.exit_code == 0

    cfg = get_raw_config()
    assert cfg["treat_rar_as_media"] is False


def test_set_treat_rar_as_media_yes_normalized_to_true(isolated_config):
    """Test that 'yes' is normalized to true for treat_rar_as_media."""
    result = runner.invoke(app_config, ["set", "treat_rar_as_media", "yes"])
    assert result.exit_code == 0

    cfg = get_raw_config()
    assert cfg["treat_rar_as_media"] is True


def test_set_treat_rar_as_media_no_normalized_to_false(isolated_config):
    """Test that 'no' is normalized to false for treat_rar_as_media."""
    result = runner.invoke(app_config, ["set", "treat_rar_as_media", "no"])
    assert result.exit_code == 0

    cfg = get_raw_config()
    assert cfg["treat_rar_as_media"] is False


def test_set_treat_rar_as_media_invalid_value(isolated_config):
    """Test that invalid boolean values are rejected."""
    result = runner.invoke(app_config, ["set", "treat_rar_as_media", "maybe"])
    assert result.exit_code != 0
    assert "Invalid boolean value" in result.stdout


def test_get_treat_rar_as_media(isolated_config):
    """Test getting treat_rar_as_media value via CLI."""
    # Set it first
    runner.invoke(app_config, ["set", "treat_rar_as_media", "true"])

    # Get it
    result = runner.invoke(app_config, ["get", "treat_rar_as_media"])
    assert result.exit_code == 0
    assert "treat_rar_as_media = true" in result.stdout


def test_treat_rar_as_media_triggers_cache_rebuild_when_changed(isolated_config, monkeypatch):
    """Test that changing treat_rar_as_media triggers cache rebuild if caching enabled."""
    # Enable cache_library first
    runner.invoke(app_config, ["set", "cache_library", "true"])

    # Mock the rebuild function
    mock_rebuild = Mock()
    monkeypatch.setattr("mf.utils.cache.rebuild_library_cache", mock_rebuild)

    # Change treat_rar_as_media
    result = runner.invoke(app_config, ["set", "treat_rar_as_media", "false"])
    assert result.exit_code == 0

    # Verify rebuild was called
    assert mock_rebuild.called


def test_treat_rar_as_media_no_rebuild_when_cache_disabled(isolated_config, monkeypatch):
    """Test that changing treat_rar_as_media doesn't rebuild when caching disabled."""
    # Disable cache_library
    runner.invoke(app_config, ["set", "cache_library", "false"])

    # Mock the rebuild function
    mock_rebuild = Mock()
    monkeypatch.setattr("mf.utils.cache.rebuild_library_cache", mock_rebuild)

    # Change treat_rar_as_media
    result = runner.invoke(app_config, ["set", "treat_rar_as_media", "false"])
    assert result.exit_code == 0

    # Verify rebuild was NOT called
    assert not mock_rebuild.called


def test_treat_rar_as_media_add_action_not_supported(isolated_config):
    """Test that 'add' action is not supported for treat_rar_as_media."""
    result = runner.invoke(app_config, ["add", "treat_rar_as_media", "true"])
    assert result.exit_code != 0
    assert "not supported" in result.stdout


def test_treat_rar_as_media_clear_action_not_supported(isolated_config):
    """Test that 'clear' action is not supported for treat_rar_as_media."""
    result = runner.invoke(app_config, ["clear", "treat_rar_as_media"])
    assert result.exit_code != 0
    assert "not supported" in result.stdout


def test_treat_rar_as_media_remove_action_not_supported(isolated_config):
    """Test that 'remove' action is not supported for treat_rar_as_media."""
    result = runner.invoke(app_config, ["remove", "treat_rar_as_media", "true"])
    assert result.exit_code != 0
    assert "not supported" in result.stdout


def test_list_settings_shows_treat_rar_as_media(isolated_config):
    """Test that 'list' command shows treat_rar_as_media."""
    result = runner.invoke(app_config, ["list"])
    assert result.exit_code == 0
    assert "treat_rar_as_media" in result.stdout
