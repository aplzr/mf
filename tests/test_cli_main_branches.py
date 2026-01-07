import os

import pytest
from typer.testing import CliRunner

from mf.cli_main import app_mf

runner = CliRunner()


def test_main_callback_no_command_shows_help():
    result = runner.invoke(app_mf, [])
    # Typer Exit should occur after printing help and version
    assert result.exit_code == 0
    assert "Version:" in result.stdout
    assert "Usage:" in result.stdout or "Commands:" in result.stdout


def test_version_prints_version():
    result = runner.invoke(app_mf, ["version"])
    assert result.exit_code == 0
    # Should print semantic version string
    assert any(char.isdigit() for char in result.stdout)


def test_version_check_branch(monkeypatch):
    # Simulate check_version side effect without external calls
    called = {"value": False}

    def fake_check():
        called["value"] = True

    # cli_main imports check_version directly; patch that symbol
    monkeypatch.setattr("mf.cli_main.check_version", fake_check)
    result = runner.invoke(app_mf, ["version", "check"])
    assert result.exit_code == 0
    assert called["value"] is True


def test_find_no_results_warns(monkeypatch):
    # Force FindQuery to return empty to hit warning branch
    class Dummy:
        pattern = "*"

        @classmethod
        def from_config(cls, pattern, **kwargs):
            return cls()

        def execute(self):
            return []

    monkeypatch.setattr("mf.cli_main.FindQuery", Dummy)
    result = runner.invoke(app_mf, ["find", "*.nonexistentext"])
    assert result.exit_code == 0
    assert "No media files found" in result.stdout


def test_new_empty_collection_raises(monkeypatch):
    # Force NewQuery to return empty and hit print_and_raise path
    class Dummy:
        @classmethod
        def from_config(cls, n, **kwargs):
            return cls()

        def execute(self):
            return []

    monkeypatch.setattr("mf.cli_main.NewQuery", Dummy)
    result = runner.invoke(app_mf, ["new", "5"])
    # Typer will convert raised exception to non-zero exit
    assert result.exit_code != 0
    assert "No media files found" in result.stdout or result.stderr


def test_play_invalid_target_errors(monkeypatch):
    # Pass a non-integer to trigger ValueError branch
    result = runner.invoke(app_mf, ["play", "not-an-int"])
    assert result.exit_code != 0
    assert "Invalid target" in (result.stdout + result.stderr)


def test_play_command_integration(monkeypatch):
    """Integration test: verify play command calls resolve and launch functions."""
    from pathlib import Path

    class DummyFile:
        name = "movie.mp4"
        parent = Path("/tmp")

        def __str__(self):
            return "/tmp/movie.mp4"

    class DummyResult:
        file = DummyFile()

    resolve_called_with = None
    launch_called_with = None

    def mock_resolve(target):
        nonlocal resolve_called_with
        resolve_called_with = target
        return DummyResult()

    def mock_launch(file_to_play, cfg):
        nonlocal launch_called_with
        launch_called_with = file_to_play

    monkeypatch.setattr("mf.cli_main.resolve_play_target", mock_resolve)
    monkeypatch.setattr("mf.cli_main.launch_video_player", mock_launch)

    # Test with "next" target
    result = runner.invoke(app_mf, ["play", "next"])
    assert result.exit_code == 0
    assert resolve_called_with == "next"
    assert launch_called_with is not None

    # Test with no target (random)
    resolve_called_with = None
    result = runner.invoke(app_mf, ["play"])
    assert result.exit_code == 0
    assert resolve_called_with is None

    # Test with numeric index
    result = runner.invoke(app_mf, ["play", "5"])
    assert result.exit_code == 0
    assert resolve_called_with == "5"


def test_imdb_opens(monkeypatch):
    # Ensure imdb command calls open_imdb_entry with desired index
    called = {"idx": None}

    def fake_open(fr):
        called["idx"] = True

    monkeypatch.setattr("mf.cli_main.open_imdb_entry", fake_open)
    # get_result_by_index returns a dummy FileResult-like object
    monkeypatch.setattr("mf.cli_main.get_result_by_index", lambda i: object())
    result = runner.invoke(app_mf, ["imdb", "1"])
    assert result.exit_code == 0
    assert called["idx"] is True


def test_filepath_prints(monkeypatch):
    class Dummy:
        def __init__(self, path):
            self.file = type("F", (), {"__str__": lambda self: path})()

    monkeypatch.setattr(
        "mf.cli_main.get_result_by_index", lambda i: Dummy("/tmp/x.mp4")
    )
    result = runner.invoke(app_mf, ["filepath", "1"])
    assert result.exit_code == 0
    assert "/tmp/x.mp4" in result.stdout
