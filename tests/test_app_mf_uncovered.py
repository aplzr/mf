from __future__ import annotations

from typer.testing import CliRunner

from mf.cli_main import app_mf
from mf.utils.file import FileResult

runner = CliRunner()


def test_find_no_results(monkeypatch):
    """Exercise early exit path when find returns no results."""
    from mf.utils.scan import FindQuery as _FindQuery

    class FakeFind(_FindQuery):  # type: ignore
        def __init__(self, pattern: str):  # pragma: no cover - simple init override
            super().__init__(pattern)

        def execute(self):  # noqa: D401
            return []

    monkeypatch.setattr("mf.cli_main.FindQuery", FakeFind)
    result = runner.invoke(app_mf, ["find", "nonexistent*"])
    # Graceful exit (no results) uses default Typer exit code 0
    assert result.exit_code == 0
    assert "No media files found matching" in result.stdout


def test_new_no_results(monkeypatch):
    """Exercise early exit path when new returns empty collection."""
    from mf.utils.scan import NewQuery as _NewQuery

    class FakeNew(_NewQuery):  # type: ignore
        def execute(self):  # noqa: D401
            return []

    monkeypatch.setattr("mf.cli_main.NewQuery", FakeNew)
    result = runner.invoke(app_mf, ["new", "5"])
    # Graceful exit (empty collection) uses default Typer exit code 0
    assert result.exit_code == 1
    assert "No media files found (empty collection)." in result.stdout


def test_filepath_command(monkeypatch, tmp_path, capsys):
    """Cover filepath command printing path."""
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        "mf.cli_main.get_result_by_index", lambda idx: FileResult(fake_file)
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
