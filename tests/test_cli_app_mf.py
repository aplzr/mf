from __future__ import annotations

from typer.testing import CliRunner

from mf.cli_main import app_mf
from mf.utils.file import FileResult

runner = CliRunner()


def test_find_no_results(monkeypatch):
    """Find command exits gracefully when no files match."""
    from mf.cli_main import FindQuery as _FindQuery

    class FakeFind(_FindQuery):  # type: ignore
        def __init__(self, pattern: str):  # pragma: no cover - trivial init reuse
            super().__init__(pattern)

        def execute(self):  # noqa: D401
            return []

    monkeypatch.setattr("mf.cli_main.FindQuery", FakeFind)
    result = runner.invoke(app_mf, ["find", "nonexistent*"])
    assert result.exit_code == 0
    assert "No media files found" in result.stdout


def test_new_no_results(monkeypatch):
    """New command exits gracefully on empty collection."""
    from mf.cli_main import NewQuery as _NewQuery

    class FakeNew(_NewQuery):  # type: ignore
        def execute(self):  # noqa: D401
            return []

    monkeypatch.setattr("mf.cli_main.NewQuery", FakeNew)
    result = runner.invoke(app_mf, ["new", "5"])
    assert result.exit_code == 0
    assert "No media files found" in result.stdout


def test_play_specific_index(monkeypatch, tmp_path):
    """Play command with explicit index (non-random path)."""
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(
        "mf.cli_main.get_result_by_index", lambda idx: FileResult(fake_file)
    )
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: None)
    # Block VLC path detection for packaged paths
    from pathlib import Path as _P

    orig_exists = _P.exists

    def fake_exists(self):  # pragma: no cover
        if str(self) in {
            r"C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
            r"C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe",
        }:
            return False
        return orig_exists(self)

    monkeypatch.setattr(_P, "exists", fake_exists)
    result = runner.invoke(app_mf, ["play", "1"])
    assert result.exit_code == 0
    assert "Playing:" in result.stdout


def test_play_vlc_not_found(monkeypatch, tmp_path):
    """VLC not installed path raises with message."""
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        "mf.cli_main.get_result_by_index", lambda idx: FileResult(fake_file)
    )

    def popen_raise(*a, **k):  # pragma: no cover
        raise FileNotFoundError("vlc missing")

    monkeypatch.setattr("subprocess.Popen", popen_raise)
    result = runner.invoke(app_mf, ["play", "1"])
    assert result.exit_code != 0
    assert "VLC not found" in result.stdout


def test_play_generic_exception(monkeypatch, tmp_path):
    """Generic VLC launch exception path."""
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        "mf.cli_main.get_result_by_index", lambda idx: FileResult(fake_file)
    )

    def popen_raise(*a, **k):  # pragma: no cover
        raise RuntimeError("boom")

    monkeypatch.setattr("subprocess.Popen", popen_raise)
    result = runner.invoke(app_mf, ["play", "1"])
    assert result.exit_code != 0
    assert "Error launching VLC" in result.stdout


def test_filepath_command(monkeypatch, tmp_path):
    """Filepath command prints path."""
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        "mf.cli_main.get_result_by_index", lambda idx: FileResult(fake_file)
    )
    result = runner.invoke(app_mf, ["filepath", "1"])
    assert result.exit_code == 0
    assert str(fake_file) in result.stdout.strip()


def test_version_command_again():
    """Version command prints version string."""
    result = runner.invoke(app_mf, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip()


def test_main_callback_help_again():
    """Top-level invocation prints help and exits."""
    result = runner.invoke(app_mf, [])
    assert result.exit_code == 0
    assert "Version:" in result.stdout
