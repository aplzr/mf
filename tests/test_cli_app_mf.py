from __future__ import annotations

from unittest.mock import PropertyMock, patch

from typer.testing import CliRunner

from mf.cli_main import app_mf
from mf.utils.file import FileResult

runner = CliRunner()


def test_find_no_results(monkeypatch):
    """Find command exits gracefully when no files match."""
    from mf.utils.scan import FindQuery as _FindQuery

    class FakeFind(_FindQuery):  # type: ignore
        def __init__(self, pattern: str, **kwargs):  # pragma: no cover - trivial init reuse
            super().__init__(pattern, **kwargs)

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
    assert result.exit_code == 1
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


def test_find_plain_flag(monkeypatch):
    """Find command with --plain outputs only file paths."""
    from pathlib import Path
    from mf.utils.scan import FindQuery as _FindQuery

    test_path1 = Path("/media/movie1.mp4")
    test_path2 = Path("/media/movie2.mkv")

    class FakeFindWithResults(_FindQuery):  # type: ignore
        def __init__(self, pattern: str, **kwargs):
            super().__init__(pattern, **kwargs)

        def execute(self):
            return [
                FileResult(test_path1),
                FileResult(test_path2)
            ]

    monkeypatch.setattr("mf.cli_main.FindQuery", FakeFindWithResults)
    result = runner.invoke(app_mf, ["find", "movie", "--plain"])
    assert result.exit_code == 0
    # Should contain file paths
    assert str(test_path1) in result.stdout
    assert str(test_path2) in result.stdout
    # Should NOT contain rich formatting
    assert "Search pattern:" not in result.stdout


def test_find_plain_short_flag(monkeypatch):
    """Find command with -p outputs plain text."""
    from pathlib import Path
    from mf.utils.scan import FindQuery as _FindQuery

    test_path = Path("/media/test.mp4")

    class FakeFindWithResults(_FindQuery):  # type: ignore
        def __init__(self, pattern: str, **kwargs):
            super().__init__(pattern, **kwargs)

        def execute(self):
            return [FileResult(test_path)]

    monkeypatch.setattr("mf.cli_main.FindQuery", FakeFindWithResults)
    result = runner.invoke(app_mf, ["find", "test", "-p"])
    assert result.exit_code == 0
    assert str(test_path) in result.stdout
    assert "Search pattern:" not in result.stdout


def test_new_plain_flag(monkeypatch):
    """New command with --plain outputs only file paths."""
    from pathlib import Path
    from mf.utils.scan import NewQuery as _NewQuery

    test_path1 = Path("/media/recent1.mp4")
    test_path2 = Path("/media/recent2.mkv")

    class FakeNewWithResults(_NewQuery):  # type: ignore
        def execute(self):
            return [
                FileResult(test_path1),
                FileResult(test_path2)
            ]

    monkeypatch.setattr("mf.cli_main.NewQuery", FakeNewWithResults)
    result = runner.invoke(app_mf, ["new", "2", "--plain"])
    assert result.exit_code == 0
    # Should contain file paths
    assert str(test_path1) in result.stdout
    assert str(test_path2) in result.stdout
    # Should NOT contain rich formatting
    assert "latest additions" not in result.stdout


def test_find_tty_detection(monkeypatch):
    """Find command automatically outputs plain text when not in TTY."""
    from pathlib import Path
    from mf.utils.scan import FindQuery as _FindQuery
    from mf.utils.search import console

    test_path = Path("/media/auto_plain.mp4")

    class FakeFindWithResults(_FindQuery):  # type: ignore
        def __init__(self, pattern: str, **kwargs):
            super().__init__(pattern, **kwargs)

        def execute(self):
            return [FileResult(test_path)]

    monkeypatch.setattr("mf.cli_main.FindQuery", FakeFindWithResults)

    # Override the global mock to simulate non-TTY environment
    with patch.object(type(console), 'is_terminal', new_callable=PropertyMock, return_value=False):
        result = runner.invoke(app_mf, ["find", "test"])
        assert result.exit_code == 0
        # Should automatically output plain text
        assert str(test_path) in result.stdout
        assert "Search pattern:" not in result.stdout
