"""Tests for treat_rar_as_media setting functionality."""

from tomlkit import document

from mf.utils.config import Configuration, get_raw_config, write_config
from mf.utils.settings import SETTINGS


def test_treat_rar_as_media_true_adds_rar_extension(isolated_config):
    """Test that treat_rar_as_media=true automatically adds .rar to media_extensions."""
    # Create config with treat_rar_as_media=true and media_extensions without .rar
    cfg = get_raw_config()
    cfg["treat_rar_as_media"] = True
    cfg["media_extensions"] = [".mp4", ".mkv"]
    write_config(cfg)

    # Load Configuration and verify .rar is added
    config = Configuration.from_config()
    assert ".rar" in config.media_extensions
    assert ".mp4" in config.media_extensions
    assert ".mkv" in config.media_extensions


def test_treat_rar_as_media_false_does_not_add_rar(isolated_config):
    """Test that treat_rar_as_media=false does not add .rar to media_extensions."""
    # Create config with treat_rar_as_media=false
    cfg = get_raw_config()
    cfg["treat_rar_as_media"] = False
    cfg["media_extensions"] = [".mp4", ".mkv"]
    write_config(cfg)

    # Load Configuration and verify .rar is NOT added
    config = Configuration.from_config()
    assert ".rar" not in config.media_extensions
    assert config.media_extensions == [".mp4", ".mkv"]


def test_treat_rar_as_media_default_value_is_true(isolated_config):
    """Test that the default value for treat_rar_as_media is True."""
    cfg = get_raw_config()
    # Default config should have treat_rar_as_media=true
    assert cfg["treat_rar_as_media"] is True


def test_treat_rar_as_media_allowed_values(isolated_config):
    """Test that treat_rar_as_media only accepts boolean values."""
    spec = SETTINGS["treat_rar_as_media"]
    assert spec.allowed_values == [True, False]
    assert spec.value_type == bool


def test_treat_rar_as_media_with_empty_media_extensions_base(isolated_config):
    """Test treat_rar_as_media=true with only one extension in base list."""
    cfg = get_raw_config()
    cfg["treat_rar_as_media"] = True
    cfg["media_extensions"] = [".mp4"]  # Only one extension
    write_config(cfg)

    config = Configuration.from_config()
    assert ".rar" in config.media_extensions
    assert ".mp4" in config.media_extensions
    assert len(config.media_extensions) == 2
