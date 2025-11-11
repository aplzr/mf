from __future__ import annotations

import builtins

from typer.testing import CliRunner

from mf._app_mf import app_mf
from mf.utils.file_utils import FileResult

runner = CliRunner()


def test_find_no_results(monkeypatch):
    """Exercise early exit path when find returns no results."""
    from mf._app_mf import FindQuery as _FindQuery

    class FakeFind(_FindQuery):  # type: ignore
        def __init__(self, pattern: str):  # pragma: no cover - simple init override
            super().__init__(pattern)

        def execute(self):  # noqa: D401
            return []

    monkeypatch.setattr("mf._app_mf.FindQuery", FakeFind)
    result = runner.invoke(app_mf, ["find", "nonexistent*"])
    # Graceful exit (no results) uses default Typer exit code 0
    assert result.exit_code == 0
    assert "No media files found matching" in result.stdout


def test_new_no_results(monkeypatch):
    """Exercise early exit path when new returns empty collection."""
    from mf._app_mf import NewQuery as _NewQuery

    class FakeNew(_NewQuery):  # type: ignore
        def execute(self):  # noqa: D401
            return []

    monkeypatch.setattr("mf._app_mf.NewQuery", FakeNew)
    result = runner.invoke(app_mf, ["new", "5"])
    # Graceful exit (empty collection) uses default Typer exit code 0
    assert result.exit_code == 0
    assert "No media files found (empty collection)." in result.stdout


def test_play_specific_index(monkeypatch, tmp_path):
    """Cover play command when index is provided (non-random path)."""
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(
        "mf._app_mf.get_result_by_index", lambda idx: FileResult(fake_file)
    )
    # Avoid launching VLC: patch subprocess.Popen
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: None)
    # Prevent Windows VLC path detection from succeeding without altering os.name
    from pathlib import Path as _P

    orig_exists = _P.exists

    def fake_exists(self):  # pragma: no cover - trivial wrapper
        vlc_candidates = {
            r"C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
            r"C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe",
        }
        if str(self) in vlc_candidates:
            return False
        return orig_exists(self)

    monkeypatch.setattr(_P, "exists", fake_exists)
    result = runner.invoke(app_mf, ["play", "1"])
    assert result.exit_code == 0
    assert "Playing:" in result.stdout
    assert "movie.mp4" in result.stdout


def test_play_vlc_not_found(monkeypatch, tmp_path):
    """Trigger VLC FileNotFoundError branch."""
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(
        "mf._app_mf.get_result_by_index", lambda idx: FileResult(fake_file)
    )

    def popen_raise(*a, **k):  # pragma: no cover - error branch
        raise FileNotFoundError("vlc missing")

    monkeypatch.setattr("subprocess.Popen", popen_raise)
    result = runner.invoke(app_mf, ["play", "1"])
    assert result.exit_code != 0
    assert "VLC not found" in result.stdout


def test_play_generic_exception(monkeypatch, tmp_path):
    """Trigger generic exception branch in play command."""
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        "mf._app_mf.get_result_by_index", lambda idx: FileResult(fake_file)
    )

    def popen_raise(*a, **k):  # pragma: no cover - error branch
        raise RuntimeError("boom")

    monkeypatch.setattr("subprocess.Popen", popen_raise)
    result = runner.invoke(app_mf, ["play", "1"])
    assert result.exit_code != 0
    assert "Error launching VLC" in result.stdout


def test_imdb_import_error(monkeypatch, tmp_path):
    """Cover IMDb ImportError path (lazy import failure)."""
    # Ensure global IMDb sentinel is None so import attempted
    import mf._app_mf as app_mod

    app_mod.IMDb = None

    fake_file = tmp_path / "Title 2024 1080p.mkv"
    fake_file.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        "mf._app_mf.get_result_by_index", lambda idx: FileResult(fake_file)
    )
    # Simulate guessit parse success
    monkeypatch.setattr("mf._app_mf.guessit", lambda _: {"title": "Title"})

    # Force import failure only for 'imdb' so other imports still work
    real_import = builtins.__import__

    def selective_import(name, *a, **k):  # pragma: no cover - import failure path
        if name.startswith("imdb"):
            raise ImportError("no imdb")
        return real_import(name, *a, **k)

    monkeypatch.setattr("builtins.__import__", selective_import)
    result = runner.invoke(app_mf, ["imdb", "1"])
    assert result.exit_code != 0
    assert "IMDb functionality unavailable" in result.stdout


def test_imdb_no_results(monkeypatch, tmp_path):
    """Cover path where IMDb search returns no results."""
    import mf._app_mf as app_mod

    app_mod.IMDb = lambda: type("FakeIMDb", (), {"search_movie": lambda self, t: []})()
    fake_file = tmp_path / "Title 2024 1080p.mkv"
    fake_file.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        "mf._app_mf.get_result_by_index", lambda idx: FileResult(fake_file)
    )
    monkeypatch.setattr("mf._app_mf.guessit", lambda _: {"title": "Title"})
    result = runner.invoke(app_mf, ["imdb", "1"])
    assert result.exit_code != 0
    assert "No IMDb results found" in result.stdout


def test_filepath_command(monkeypatch, tmp_path, capsys):
    """Cover filepath command printing path."""
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        "mf._app_mf.get_result_by_index", lambda idx: FileResult(fake_file)
    )
    result = runner.invoke(app_mf, ["filepath", "1"])
    assert result.exit_code == 0
    assert str(fake_file) in result.stdout.strip()


def test_version_command_again():
    """Redundant but ensures version path remains covered even after changes."""
    result = runner.invoke(app_mf, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip()


def test_main_callback_help_again():
    """Ensure main callback help path still covered."""
    result = runner.invoke(app_mf, [])
    # Help callback exits with default code 0
    assert result.exit_code == 0
    assert "Version:" in result.stdout
