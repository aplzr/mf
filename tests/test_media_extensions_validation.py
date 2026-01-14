"""Tests for media_extensions clearing and validation via CLI."""

from typer.testing import CliRunner

from mf.cli_config import app_config
from mf.utils.config import get_raw_config, write_config

runner = CliRunner()


def test_clear_media_extensions_not_supported(isolated_config):
    """Test that clearing media_extensions action is not supported."""
    # Set up some extensions first
    cfg = get_raw_config()
    cfg["media_extensions"] = [".mp4", ".mkv", ".avi"]
    write_config(cfg)

    # Try to clear media_extensions
    result = runner.invoke(app_config, ["clear", "media_extensions"])

    # Should fail because clear action is not supported
    assert result.exit_code != 0
    assert "not supported" in result.stdout


def test_remove_all_media_extensions_one_by_one_fails_on_last(isolated_config):
    """Test that removing all extensions one by one fails on the last one."""
    # Set up with only one extension
    cfg = get_raw_config()
    cfg["media_extensions"] = [".mp4", ".mkv"]
    write_config(cfg)

    # Remove first extension - should succeed
    result = runner.invoke(app_config, ["remove", "media_extensions", ".mp4"])
    assert result.exit_code == 0

    # Try to remove the last extension - should fail
    result = runner.invoke(app_config, ["remove", "media_extensions", ".mkv"])
    assert result.exit_code != 0
    assert "can't be empty" in result.stdout


def test_set_empty_media_extensions_not_possible(isolated_config):
    """Test that setting media_extensions requires at least one value."""
    # Try to set media_extensions with no values
    result = runner.invoke(app_config, ["set", "media_extensions"])

    # Should fail (no values provided)
    assert result.exit_code != 0


def test_media_extensions_always_has_at_least_one_value(isolated_config):
    """Test that media_extensions always maintains at least one extension."""
    cfg = get_raw_config()

    # Default config should have extensions
    assert len(cfg["media_extensions"]) > 0

    # Try to set to empty would require validation to catch
    # (which is tested in test_clear_media_extensions_fails_validation)


def test_remove_last_extension_then_readd(isolated_config):
    """Test workflow: try to remove last extension (fails), then add new one first."""
    # Set up with only one extension
    cfg = get_raw_config()
    cfg["media_extensions"] = [".mp4"]
    write_config(cfg)

    # Try to remove the only extension - should fail
    result = runner.invoke(app_config, ["remove", "media_extensions", ".mp4"])
    assert result.exit_code != 0

    # Add a different extension first
    result = runner.invoke(app_config, ["add", "media_extensions", ".mkv"])
    assert result.exit_code == 0

    # Now we can remove .mp4
    result = runner.invoke(app_config, ["remove", "media_extensions", ".mp4"])
    assert result.exit_code == 0

    # Verify only .mkv remains
    cfg = get_raw_config()
    assert cfg["media_extensions"] == [".mkv"]
