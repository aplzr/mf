import os

import pytest
from typer.testing import CliRunner

from mf.cli_config import app_config
from mf.cli_main import app_mf
from mf.utils.config import get_raw_config, write_config
from mf.utils.file import FileResult
from mf.utils.normalizers import normalize_media_extension
from mf.utils.scan import scan_path_with_python
from mf.utils.search import save_search_results

runner = CliRunner()


def test_find_no_results(monkeypatch, tmp_path):
    # Configure empty search path directory with no files
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    cfg = get_raw_config()
    cfg["search_paths"] = [empty_dir.resolve().as_posix()]
    write_config(cfg)
    result = runner.invoke(app_mf, ["find", "nonexistentpattern123"])
    # Command exits with code 0 (non-error) but prints warning; just assert message
    assert result.exit_code == 0
    assert "No media files found" in result.stdout


def test_play_random(monkeypatch, tmp_path):
    # Monkeypatch find_media_files used in cli_main to return deterministic files
    from mf.utils import scan as app_module
    from mf.utils.play import ResolvedPlayer
    from pathlib import Path

    fake_path = tmp_path / "movie.mkv"
    fake_path.write_text("x")
    monkeypatch.setattr(
        app_module.FindQuery,
        "execute",
        lambda self: [FileResult(fake_path)],
    )
    # Mock player resolution to work in CI without VLC/mpv installed
    mock_player = ResolvedPlayer("vlc", Path("vlc"))
    monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)

    # Monkeypatch subprocess.Popen to prevent launching real VLC
    import subprocess

    def fake_popen(*args, **kwargs):
        class DummyProc:
            def __init__(self):
                self.pid = 12345

        return DummyProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    result = runner.invoke(app_mf, ["play"])  # random play branch
    assert result.exit_code == 0
    assert "Playing:" in result.stdout


def test_play_vlc_not_found(monkeypatch, tmp_path):
    # Seed cache with one file so get_file_by_index succeeds
    from mf.utils.play import ResolvedPlayer
    from pathlib import Path

    media_dir = tmp_path / "media"
    media_dir.mkdir()
    target_file = media_dir / "video.mkv"
    target_file.write_text("x")
    save_search_results("*", [FileResult(target_file)])
    # Mock player resolution to work in CI without VLC/mpv installed
    mock_player = ResolvedPlayer("vlc", Path("vlc"))
    monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)

    # Monkeypatch subprocess.Popen to raise FileNotFoundError simulating missing VLC
    import subprocess

    def raise_fn(*args, **kwargs):
        raise FileNotFoundError("vlc")

    monkeypatch.setattr(subprocess, "Popen", raise_fn)
    result = runner.invoke(app_mf, ["play", "1"])  # play index 1
    assert result.exit_code != 0
    assert "vlc not found" in result.stdout


def test_play_generic_exception(monkeypatch, tmp_path):
    from mf.utils.play import ResolvedPlayer
    from pathlib import Path

    media_dir = tmp_path / "media2"
    media_dir.mkdir()
    target_file = media_dir / "video2.mkv"
    target_file.write_text("x")
    save_search_results("*", [FileResult(target_file)])
    # Mock player resolution to work in CI without VLC/mpv installed
    mock_player = ResolvedPlayer("vlc", Path("vlc"))
    monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)

    import subprocess

    def raise_gen(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(subprocess, "Popen", raise_gen)
    result = runner.invoke(app_mf, ["play", "1"])  # play index 1
    assert result.exit_code != 0
    assert "Error launching vlc" in result.stdout


def test_add_not_supported(monkeypatch):
    result = runner.invoke(app_config, ["add", "display_paths", "true"])
    assert result.exit_code != 0
    assert "not supported" in result.stdout


def test_clear_not_supported(monkeypatch):
    result = runner.invoke(app_config, ["clear", "display_paths"])
    assert result.exit_code != 0
    assert "not supported" in result.stdout


def test_normalize_media_extension_whitespace(monkeypatch):
    import click

    with pytest.raises(click.exceptions.Exit):  # typer.Exit maps to click Exit
        normalize_media_extension("   ")


def test_scan_path_python_permission(monkeypatch, tmp_path):
    # Simulate PermissionError on scandir for given directory
    target_dir = tmp_path / "protected"
    target_dir.mkdir()

    def fake_scandir(path):
        raise PermissionError("denied")

    monkeypatch.setattr(os, "scandir", fake_scandir)
    results = scan_path_with_python(target_dir)
    assert results == []  # skipped


def test_set_false(monkeypatch):
    # Ensure we can set false and cover branch
    result = runner.invoke(app_config, ["set", "display_paths", "false"])
    assert result.exit_code == 0
    cfg = get_raw_config()
    assert cfg["display_paths"] is False
