from __future__ import annotations

from typer.testing import CliRunner

from mf.cli_main import app_mf
from mf.utils.file import FileResult

runner = CliRunner()


def test_find_no_results(monkeypatch):
    """Find command exits gracefully when no files match."""
    from mf.utils.scan import FindQuery as _FindQuery

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
    from mf.utils.scan import NewQuery as _NewQuery

    class FakeNew(_NewQuery):  # type: ignore
        def execute(self):  # noqa: D401
            return []

    monkeypatch.setattr("mf.cli_main.NewQuery", FakeNew)
    result = runner.invoke(app_mf, ["new", "5"])
    assert result.exit_code == 0
    assert "No media files found" in result.stdout


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
