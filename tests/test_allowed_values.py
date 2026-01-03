"""Tests for allowed_values validation in list settings."""

import os

from typer.testing import CliRunner

from mf.cli_config import app_config
from mf.utils.config import get_config

runner = CliRunner()


def _set_env(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )


def test_list_set_all_valid_succeeds(tmp_path, monkeypatch):
    """Test list 'set' action succeeds when all values are valid."""
    _set_env(monkeypatch, tmp_path)

    # media_extensions has no allowed_values, so any valid extension should work
    r = runner.invoke(app_config, ["set", "media_extensions", ".mp4", ".mkv"])
    assert r.exit_code == 0

    cfg = get_config()
    assert ".mp4" in cfg["media_extensions"]
    assert ".mkv" in cfg["media_extensions"]


def test_list_add_valid_succeeds(tmp_path, monkeypatch):
    """Test list 'add' action succeeds when value is valid."""
    _set_env(monkeypatch, tmp_path)

    # Add a new extension
    r = runner.invoke(app_config, ["add", "media_extensions", ".avi"])
    assert r.exit_code == 0

    cfg = get_config()
    assert ".avi" in cfg["media_extensions"]


def test_list_remove_allows_any_value(tmp_path, monkeypatch):
    """Test list 'remove' action doesn't validate (allows removing anything)."""
    _set_env(monkeypatch, tmp_path)

    # Set up initial state
    runner.invoke(app_config, ["set", "media_extensions", ".mp4", ".mkv"])

    # Remove should work even if we theoretically had allowed_values
    r = runner.invoke(app_config, ["remove", "media_extensions", ".mp4"])
    assert r.exit_code == 0

    cfg = get_config()
    assert ".mp4" not in cfg["media_extensions"]
    assert ".mkv" in cfg["media_extensions"]
