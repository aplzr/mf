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

        def execute(self):
            return []

    monkeypatch.setattr("mf.cli_main.FindQuery", lambda p: Dummy())
    result = runner.invoke(app_mf, ["find", "*.nonexistentext"])
    assert result.exit_code == 0
    assert "No media files found" in result.stdout


def test_new_empty_collection_raises(monkeypatch):
    # Force NewQuery to return empty and hit print_and_raise path
    class Dummy:
        def __init__(self, n):
            pass

        def execute(self):
            return []

    monkeypatch.setattr("mf.cli_main.NewQuery", lambda n: Dummy(n))
    result = runner.invoke(app_mf, ["new", "5"])
    # Typer will convert raised exception to non-zero exit
    assert result.exit_code != 0
    assert "No media files found" in result.stdout or result.stderr


def test_play_invalid_target_errors(monkeypatch):
    # Pass a non-integer to trigger ValueError branch
    result = runner.invoke(app_mf, ["play", "not-an-int"])
    assert result.exit_code != 0
    assert "Invalid target" in (result.stdout + result.stderr)


def test_play_next_branch(monkeypatch):
    # Simulate get_next returning a FileResult-like object
    class DummyFile:
        name = "movie.mp4"
        parent = "/tmp"

        def __str__(self):
            return "/tmp/movie.mp4"

    class DummyResult:
        file = DummyFile()

    monkeypatch.setattr("mf.cli_main.get_next", lambda: DummyResult())
    monkeypatch.setattr("mf.cli_main.save_last_played", lambda fr: None)
    monkeypatch.setattr("mf.cli_main.get_vlc_command", lambda: "vlc")

    # Prevent actual process spawn
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)

    result = runner.invoke(app_mf, ["play", "next"])
    assert result.exit_code == 0
    assert "VLC launched successfully" in result.stdout


@pytest.mark.parametrize("fullscreen", [True, False])
def test_play_list_branch_and_fullscreen(monkeypatch, fullscreen):
    # Simulate last search results as playlist
    class DummyFile:
        def __init__(self, path):
            self._path = path
            self.name = os.path.basename(path)
            self.parent = os.path.dirname(path)

        def __str__(self):
            return self._path

    class DummyResult:
        def __init__(self, path):
            self.file = DummyFile(path)

    class DummyResults(list):
        pass

    # load_search_results returns (pattern, results, stats)
    monkeypatch.setattr(
        "mf.cli_main.load_search_results",
        lambda: (
            "pattern",
            DummyResults([DummyResult("/tmp/a.mp4"), DummyResult("/tmp/b.mp4")]),
            {},
        ),
    )

    monkeypatch.setattr("mf.cli_main.get_vlc_command", lambda: "vlc")
    monkeypatch.setattr(
        "mf.cli_main.read_config", lambda: {"fullscreen_playback": fullscreen}
    )

    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)

    result = runner.invoke(app_mf, ["play", "list"])
    assert result.exit_code == 0
    assert "VLC launched successfully" in result.stdout


def test_play_random_file_branch(monkeypatch):
    # Exercise random branch by returning a deterministic list
    class DummyFile:
        def __init__(self, path):
            self._path = path
            self.name = os.path.basename(path)
            self.parent = os.path.dirname(path)

        def __str__(self):
            return self._path

    class DummyResult:
        def __init__(self, path):
            self.file = DummyFile(path)

    monkeypatch.setattr(
        "mf.cli_main.FindQuery",
        lambda p: type(
            "Q",
            (),
            {
                "execute": lambda self: [
                    DummyResult("/tmp/a.mp4"),
                    DummyResult("/tmp/b.mp4"),
                ]
            },
        )(),
    )
    monkeypatch.setattr("mf.cli_main.get_vlc_command", lambda: "vlc")

    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)

    result = runner.invoke(app_mf, ["play"])
    assert result.exit_code == 0
    assert "VLC launched successfully" in result.stdout


def test_play_by_index_valid(monkeypatch):
    """Test play with valid numeric index."""
    class DummyFile:
        name = "movie.mp4"
        parent = "/tmp"

        def __str__(self):
            return "/tmp/movie.mp4"

    class DummyResult:
        file = DummyFile()

    monkeypatch.setattr("mf.cli_main.get_result_by_index", lambda i: DummyResult())
    monkeypatch.setattr("mf.cli_main.save_last_played", lambda fr: None)
    monkeypatch.setattr("mf.cli_main.get_vlc_command", lambda: "vlc")

    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)

    result = runner.invoke(app_mf, ["play", "5"])
    assert result.exit_code == 0
    assert "VLC launched successfully" in result.stdout


def test_play_by_index_out_of_bounds(monkeypatch):
    """Test play with invalid index raises error."""
    import typer

    def raise_exit(i):
        from mf.utils.console import print_and_raise
        print_and_raise(f"Index {i} not found")

    monkeypatch.setattr("mf.cli_main.get_result_by_index", raise_exit)

    result = runner.invoke(app_mf, ["play", "999"])
    assert result.exit_code != 0


def test_play_random_empty_collection(monkeypatch):
    """Test play random when no files exist."""
    class DummyQuery:
        def execute(self):
            return []

    monkeypatch.setattr("mf.cli_main.FindQuery", lambda p: DummyQuery())

    result = runner.invoke(app_mf, ["play"])
    assert result.exit_code != 0
    assert "No media files found" in (result.stdout + result.stderr)


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


@pytest.mark.parametrize("display_paths", [True, False])
def test_find_display_paths_setting(monkeypatch, tmp_path, display_paths):
    """Test that display_paths setting controls whether file paths are shown."""
    from mf.utils.search import print_search_results
    from mf.utils.file import FileResult, FileResults

    # Create a test media file with a distinctive parent directory name
    media_dir = tmp_path / "unique_test_dir_12345"
    media_dir.mkdir()
    test_file = media_dir / "test_movie.mkv"
    test_file.write_text("test content")

    # Mock get_last_played_index to avoid cache file dependency
    monkeypatch.setattr("mf.utils.search.get_last_played_index", lambda: None)

    # Create test results
    results = FileResults([FileResult(test_file)])

    # Capture output by calling print_search_results directly
    from io import StringIO
    from mf.utils.console import console

    buffer = StringIO()
    test_console = console.__class__(file=buffer, force_terminal=True, width=80)
    monkeypatch.setattr("mf.utils.search.console", test_console)

    # Pass display_paths directly as a parameter
    print_search_results("Test Results", results, display_paths)
    output = buffer.getvalue()

    # Check that file name is always present
    assert "test_movie.mkv" in output

    # Check that file path is present/absent based on setting
    if display_paths:
        # When paths are shown, the parent directory name should appear
        assert "unique_test_dir_12345" in output
    else:
        # When paths are hidden, the parent directory name shouldn't appear
        assert "unique_test_dir_12345" not in output
