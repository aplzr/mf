"""Tests for mpv player support."""

import os
from pathlib import Path

import pytest
from click.exceptions import Exit as ClickExit

from mf.utils.file import FileResult
from mf.utils.play import (
    PLAYERS,
    ResolvedPlayer,
    build_player_args,
    get_mpv_command,
    launch_video_player,
    resolve_configured_player,
)


class TestGetMpvCommand:
    """Tests for get_mpv_command() function."""

    def test_get_mpv_command_returns_resolved_player_or_none(self):
        """Test that get_mpv_command returns ResolvedPlayer or None."""
        result = get_mpv_command()
        # If mpv is installed, should return ResolvedPlayer with label "mpv"
        if result:
            assert isinstance(result, ResolvedPlayer)
            assert result.label == "mpv"
            assert result.path is not None


class TestResolveConfiguredPlayer:
    """Tests for resolve_configured_player() function."""

    def test_resolve_vlc_explicitly(self, monkeypatch):
        """Test resolving VLC when explicitly configured."""
        mock_vlc = ResolvedPlayer("vlc", Path("/usr/bin/vlc"))

        # Create a mock PlayerSpec class
        class MockPlayerSpec:
            def get_command(self):
                return mock_vlc
            label = "vlc"
            options = {"fullscreen_playback": []}

        # Mock the PLAYERS registry
        monkeypatch.setattr("mf.utils.play.PLAYERS", {
            "vlc": MockPlayerSpec()
        })

        cfg = {"video_player": "vlc"}
        result = resolve_configured_player(cfg)

        assert result == mock_vlc
        assert result.label == "vlc"

    def test_resolve_mpv_explicitly(self, monkeypatch):
        """Test resolving mpv when explicitly configured."""
        mock_mpv = ResolvedPlayer("mpv", Path("/usr/bin/mpv"))

        # Create a mock PlayerSpec class
        class MockPlayerSpec:
            def get_command(self):
                return mock_mpv
            label = "mpv"
            options = {"fullscreen_playback": []}

        # Mock the PLAYERS registry
        monkeypatch.setattr("mf.utils.play.PLAYERS", {
            "mpv": MockPlayerSpec()
        })

        cfg = {"video_player": "mpv"}
        result = resolve_configured_player(cfg)

        assert result == mock_mpv
        assert result.label == "mpv"

    def test_resolve_auto_prefers_vlc(self, monkeypatch):
        """Test that auto mode prefers VLC over mpv."""
        mock_vlc = ResolvedPlayer("vlc", Path("/usr/bin/vlc"))
        mock_mpv = ResolvedPlayer("mpv", Path("/usr/bin/mpv"))

        monkeypatch.setattr("mf.utils.play.get_vlc_command", lambda: mock_vlc)
        monkeypatch.setattr("mf.utils.play.get_mpv_command", lambda: mock_mpv)

        cfg = {"video_player": "auto"}
        result = resolve_configured_player(cfg)

        assert result == mock_vlc
        assert result.label == "vlc"

    def test_resolve_auto_falls_back_to_mpv(self, monkeypatch):
        """Test that auto mode falls back to mpv when VLC is not found."""
        mock_mpv = ResolvedPlayer("mpv", Path("/usr/bin/mpv"))

        monkeypatch.setattr("mf.utils.play.get_vlc_command", lambda: None)
        monkeypatch.setattr("mf.utils.play.get_mpv_command", lambda: mock_mpv)

        cfg = {"video_player": "auto"}
        result = resolve_configured_player(cfg)

        assert result == mock_mpv
        assert result.label == "mpv"

    def test_resolve_auto_returns_none_when_neither_found(self, monkeypatch):
        """Test that auto mode returns None when neither player is found."""
        monkeypatch.setattr("mf.utils.play.get_vlc_command", lambda: None)
        monkeypatch.setattr("mf.utils.play.get_mpv_command", lambda: None)

        cfg = {"video_player": "auto"}
        result = resolve_configured_player(cfg)

        assert result is None

    def test_resolve_invalid_player_raises(self, monkeypatch):
        """Test that invalid player name raises an error."""
        cfg = {"video_player": "invalid_player"}

        with pytest.raises(ClickExit):
            resolve_configured_player(cfg)


class TestBuildPlayerArgs:
    """Tests for build_player_args() function."""

    def test_build_mpv_args_fullscreen_enabled(self):
        """Test building mpv args with fullscreen enabled."""
        player_spec = PLAYERS["mpv"]
        cfg = {"fullscreen_playback": True}

        args = build_player_args(player_spec, cfg)

        assert args == ["--fullscreen"]

    def test_build_mpv_args_fullscreen_disabled(self):
        """Test building mpv args with fullscreen disabled."""
        player_spec = PLAYERS["mpv"]
        cfg = {"fullscreen_playback": False}

        args = build_player_args(player_spec, cfg)

        assert args == []

    def test_build_vlc_args_fullscreen_enabled(self):
        """Test building VLC args with fullscreen enabled."""
        player_spec = PLAYERS["vlc"]
        cfg = {"fullscreen_playback": True}

        args = build_player_args(player_spec, cfg)

        assert args == ["--fullscreen", "--no-video-title-show"]

    def test_mpv_has_different_flags_than_vlc(self):
        """Test that mpv uses different flags than VLC."""
        vlc_spec = PLAYERS["vlc"]
        mpv_spec = PLAYERS["mpv"]
        cfg = {"fullscreen_playback": True}

        vlc_args = build_player_args(vlc_spec, cfg)
        mpv_args = build_player_args(mpv_spec, cfg)

        # VLC has --no-video-title-show, mpv doesn't
        assert "--no-video-title-show" in vlc_args
        assert "--no-video-title-show" not in mpv_args

        # Both have --fullscreen
        assert "--fullscreen" in vlc_args
        assert "--fullscreen" in mpv_args


class TestLaunchVideoPlayerWithMpv:
    """Tests for launching video player with mpv."""

    def test_launch_mpv_single_file(self, monkeypatch, capsys):
        """Test launching mpv with a single file."""
        popen_args = None

        def mock_popen(*args, **kwargs):
            nonlocal popen_args
            popen_args = args[0]

        mock_player = ResolvedPlayer("mpv", Path("mpv"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": False, "video_player": "mpv"})
        monkeypatch.setattr("mf.utils.play.subprocess.Popen", mock_popen)
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

        test_path = Path("/tmp/movie.mp4")
        dummy_file = FileResult(test_path)
        launch_video_player(dummy_file)

        assert popen_args == ["mpv", str(test_path)]

        captured = capsys.readouterr()
        assert "Playing:" in captured.out
        assert "movie.mp4" in captured.out
        assert "mpv launched successfully" in captured.out

    def test_launch_mpv_with_fullscreen(self, monkeypatch):
        """Test launching mpv with fullscreen enabled."""
        popen_args = None

        def mock_popen(*args, **kwargs):
            nonlocal popen_args
            popen_args = args[0]

        mock_player = ResolvedPlayer("mpv", Path("mpv"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": True, "video_player": "mpv"})
        monkeypatch.setattr("mf.utils.play.subprocess.Popen", mock_popen)
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

        dummy_file = FileResult(Path("/tmp/movie.mp4"))
        launch_video_player(dummy_file)

        assert "--fullscreen" in popen_args
        # mpv doesn't use --no-video-title-show
        assert "--no-video-title-show" not in popen_args


class TestPlayerRegistry:
    """Tests for PLAYERS registry."""

    def test_players_registry_has_vlc_and_mpv(self):
        """Test that PLAYERS registry has both VLC and mpv."""
        assert "vlc" in PLAYERS
        assert "mpv" in PLAYERS

    def test_player_specs_have_required_fields(self):
        """Test that each PlayerSpec has required fields."""
        for player_name, player_spec in PLAYERS.items():
            assert hasattr(player_spec, "get_command")
            assert hasattr(player_spec, "label")
            assert hasattr(player_spec, "options")
            assert callable(player_spec.get_command)

    def test_player_options_have_fullscreen_playback(self):
        """Test that each player has fullscreen_playback option."""
        for player_name, player_spec in PLAYERS.items():
            assert "fullscreen_playback" in player_spec.options
            assert isinstance(player_spec.options["fullscreen_playback"], list)
