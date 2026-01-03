"""Tests for video_player setting with allowed_values."""

import os

from typer.testing import CliRunner

from mf.cli_config import app_config
from mf.utils.config import get_config

runner = CliRunner()


def _set_env(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )


def test_video_player_set_auto_succeeds(tmp_path, monkeypatch):
    """Test setting video_player to 'auto' succeeds."""
    _set_env(monkeypatch, tmp_path)

    r = runner.invoke(app_config, ["set", "video_player", "auto"])
    assert r.exit_code == 0

    cfg = get_config()
    assert cfg["video_player"] == "auto"


def test_video_player_set_vlc_succeeds(tmp_path, monkeypatch):
    """Test setting video_player to 'vlc' succeeds."""
    _set_env(monkeypatch, tmp_path)

    r = runner.invoke(app_config, ["set", "video_player", "vlc"])
    assert r.exit_code == 0

    cfg = get_config()
    assert cfg["video_player"] == "vlc"


def test_video_player_set_mpv_succeeds(tmp_path, monkeypatch):
    """Test setting video_player to 'mpv' succeeds."""
    _set_env(monkeypatch, tmp_path)

    r = runner.invoke(app_config, ["set", "video_player", "mpv"])
    assert r.exit_code == 0

    cfg = get_config()
    assert cfg["video_player"] == "mpv"


def test_video_player_set_invalid_fails(tmp_path, monkeypatch):
    """Test setting video_player to invalid value fails with helpful error."""
    _set_env(monkeypatch, tmp_path)

    r = runner.invoke(app_config, ["set", "video_player", "invalid"])
    assert r.exit_code != 0

    # Error message should list allowed values
    assert "invalid" in r.stdout or "invalid" in r.stderr or "Invalid" in r.output
    assert "auto" in r.output
    assert "vlc" in r.output
    assert "mpv" in r.output


def test_video_player_normalization_works(tmp_path, monkeypatch):
    """Test normalization happens before validation (VLC → vlc → validates)."""
    _set_env(monkeypatch, tmp_path)

    # "VLC" should be normalized to "vlc" before validation
    r = runner.invoke(app_config, ["set", "video_player", "VLC"])
    assert r.exit_code == 0

    cfg = get_config()
    assert cfg["video_player"] == "vlc"  # Normalized to lowercase


def test_video_player_whitespace_normalized(tmp_path, monkeypatch):
    """Test whitespace is stripped during normalization."""
    _set_env(monkeypatch, tmp_path)

    r = runner.invoke(app_config, ["set", "video_player", "  mpv  "])
    assert r.exit_code == 0

    cfg = get_config()
    assert cfg["video_player"] == "mpv"  # Stripped


def test_video_player_mixed_case_normalized(tmp_path, monkeypatch):
    """Test mixed case is normalized to lowercase."""
    _set_env(monkeypatch, tmp_path)

    r = runner.invoke(app_config, ["set", "video_player", "AuTo"])
    assert r.exit_code == 0

    cfg = get_config()
    assert cfg["video_player"] == "auto"
