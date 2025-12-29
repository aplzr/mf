"""Unit tests for utils/play.py functions."""

from pathlib import Path

import pytest
from click.exceptions import Exit as ClickExit

from mf.utils.file import FileResult, FileResults
from mf.utils.play import launch_video_player, resolve_play_target, ResolvedPlayer


class TestResolvePlayTarget:
    """Tests for resolve_play_target() function."""

    def test_random_file_selection(self, monkeypatch):
        """Test target=None returns a random file from collection."""

        class DummyFile:
            def __init__(self, path):
                self._path = path
                self.name = Path(path).name
                self.parent = Path(path).parent

            def __str__(self):
                return self._path

        class DummyResult:
            def __init__(self, path):
                self.file = DummyFile(path)

        # Mock FindQuery to return a list of files
        class MockQuery:
            def __init__(self, pattern):
                self.pattern = pattern

            def execute(self):
                return [
                    DummyResult("/tmp/movie1.mp4"),
                    DummyResult("/tmp/movie2.mp4"),
                    DummyResult("/tmp/movie3.mp4"),
                ]

        monkeypatch.setattr("mf.utils.play.FindQuery", MockQuery)

        result = resolve_play_target(None)

        # Should return one of the files
        assert hasattr(result, "file")
        assert result.file.name in ["movie1.mp4", "movie2.mp4", "movie3.mp4"]

    def test_random_file_empty_collection_raises(self, monkeypatch):
        """Test target=None with empty collection raises error."""

        class MockQuery:
            def __init__(self, pattern):
                pass

            def execute(self):
                return []

        monkeypatch.setattr("mf.utils.play.FindQuery", MockQuery)

        with pytest.raises(ClickExit):
            resolve_play_target(None)

    def test_next_target(self, monkeypatch):
        """Test target='next' calls get_next and save_last_played."""

        class DummyFile:
            name = "next_movie.mp4"
            parent = Path("/tmp")

        class DummyResult:
            file = DummyFile()

        get_next_called = False
        save_last_played_called = False
        saved_file = None

        def mock_get_next():
            nonlocal get_next_called
            get_next_called = True
            return DummyResult()

        def mock_save_last_played(file_result):
            nonlocal save_last_played_called, saved_file
            save_last_played_called = True
            saved_file = file_result

        monkeypatch.setattr("mf.utils.play.get_next", mock_get_next)
        monkeypatch.setattr("mf.utils.play.save_last_played", mock_save_last_played)

        result = resolve_play_target("next")

        assert get_next_called
        assert save_last_played_called
        assert result.file.name == "next_movie.mp4"
        assert saved_file is result

    def test_list_target(self, monkeypatch):
        """Test target='list' calls load_search_results."""

        class DummyFile:
            def __init__(self, path):
                self._path = path
                self.name = Path(path).name

        class DummyResult:
            def __init__(self, path):
                self.file = DummyFile(path)

        mock_results = FileResults(
            [DummyResult("/tmp/a.mp4"), DummyResult("/tmp/b.mp4")]
        )

        def mock_load_search_results():
            return mock_results, "test_pattern", {}

        monkeypatch.setattr("mf.utils.play.load_search_results", mock_load_search_results)

        result = resolve_play_target("list")

        assert isinstance(result, FileResults)
        assert len(result) == 2

    def test_numeric_index_target(self, monkeypatch):
        """Test target='5' (numeric) calls get_result_by_index and save_last_played."""

        class DummyFile:
            name = "indexed_movie.mp4"
            parent = Path("/tmp")

        class DummyResult:
            file = DummyFile()

        get_result_called_with = None
        save_last_played_called = False

        def mock_get_result_by_index(index):
            nonlocal get_result_called_with
            get_result_called_with = index
            return DummyResult()

        def mock_save_last_played(file_result):
            nonlocal save_last_played_called
            save_last_played_called = True

        monkeypatch.setattr("mf.utils.play.get_result_by_index", mock_get_result_by_index)
        monkeypatch.setattr("mf.utils.play.save_last_played", mock_save_last_played)

        result = resolve_play_target("5")

        assert get_result_called_with == 5
        assert save_last_played_called
        assert result.file.name == "indexed_movie.mp4"

    def test_invalid_target_raises(self, monkeypatch):
        """Test invalid target (non-numeric string) raises error."""
        with pytest.raises(ClickExit):
            resolve_play_target("not-a-number")

    def test_case_insensitive_next(self, monkeypatch):
        """Test that 'NEXT' works (case insensitive)."""

        class DummyFile:
            name = "next.mp4"
            parent = Path("/tmp")

        class DummyResult:
            file = DummyFile()

        monkeypatch.setattr("mf.utils.play.get_next", lambda: DummyResult())
        monkeypatch.setattr("mf.utils.play.save_last_played", lambda x: None)

        result = resolve_play_target("NEXT")
        assert result.file.name == "next.mp4"

    def test_case_insensitive_list(self, monkeypatch):
        """Test that 'LIST' works (case insensitive)."""
        mock_results = FileResults([])

        monkeypatch.setattr(
            "mf.utils.play.load_search_results", lambda: (mock_results, "pattern", {})
        )

        result = resolve_play_target("LIST")
        assert isinstance(result, FileResults)


class TestLaunchVideoPlayer:
    """Tests for launch_video_player() function."""

    def test_launch_single_file(self, monkeypatch, capsys):
        """Test launching VLC with a single FileResult."""
        popen_args = None

        def mock_popen(*args, **kwargs):
            nonlocal popen_args
            popen_args = args[0]

        mock_player = ResolvedPlayer("vlc", Path("vlc"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": False, "video_player": "auto"})
        monkeypatch.setattr("mf.utils.play.subprocess.Popen", mock_popen)
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

        # Use real FileResult instance
        test_path = Path("/tmp/movie.mp4")
        dummy_file = FileResult(test_path)
        launch_video_player(dummy_file)

        assert popen_args == ["vlc", str(test_path)]

        # Check console output
        captured = capsys.readouterr()
        assert "Playing:" in captured.out
        assert "movie.mp4" in captured.out
        assert "vlc launched successfully" in captured.out

    def test_launch_playlist(self, monkeypatch, capsys):
        """Test launching VLC with FileResults (playlist)."""
        popen_args = None

        def mock_popen(*args, **kwargs):
            nonlocal popen_args
            popen_args = args[0]

        mock_player = ResolvedPlayer("vlc", Path("vlc"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": False, "video_player": "auto"})
        monkeypatch.setattr("mf.utils.play.subprocess.Popen", mock_popen)
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

        # Use real FileResult instances
        test_path_a = Path("/tmp/a.mp4")
        test_path_b = Path("/tmp/b.mp4")
        playlist = FileResults([
            FileResult(test_path_a),
            FileResult(test_path_b)
        ])

        launch_video_player(playlist)

        assert popen_args == ["vlc", str(test_path_a), str(test_path_b)]

        # Check console output
        captured = capsys.readouterr()
        assert "Last search results as playlist" in captured.out

    def test_fullscreen_enabled(self, monkeypatch):
        """Test that fullscreen flags are added when enabled."""
        popen_args = None

        def mock_popen(*args, **kwargs):
            nonlocal popen_args
            popen_args = args[0]

        mock_player = ResolvedPlayer("vlc", Path("vlc"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": True, "video_player": "auto"})
        monkeypatch.setattr("mf.utils.play.subprocess.Popen", mock_popen)
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

        dummy_file = FileResult(Path("/tmp/movie.mp4"))
        launch_video_player(dummy_file)

        assert "--fullscreen" in popen_args
        assert "--no-video-title-show" in popen_args

    def test_fullscreen_disabled(self, monkeypatch):
        """Test that fullscreen flags are not added when disabled."""
        popen_args = None

        def mock_popen(*args, **kwargs):
            nonlocal popen_args
            popen_args = args[0]

        mock_player = ResolvedPlayer("vlc", Path("vlc"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": False, "video_player": "auto"})
        monkeypatch.setattr("mf.utils.play.subprocess.Popen", mock_popen)
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

        dummy_file = FileResult(Path("/tmp/movie.mp4"))
        launch_video_player(dummy_file)

        assert "--fullscreen" not in popen_args
        assert "--no-video-title-show" not in popen_args

    def test_vlc_not_found(self, monkeypatch):
        """Test error handling when VLC is not found."""

        def mock_popen(*args, **kwargs):
            raise FileNotFoundError("vlc not found")

        mock_player = ResolvedPlayer("vlc", Path("vlc"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": False, "video_player": "auto"})
        monkeypatch.setattr("mf.utils.play.subprocess.Popen", mock_popen)
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

        dummy_file = FileResult(Path("/tmp/movie.mp4"))
        with pytest.raises(ClickExit):
            launch_video_player(dummy_file)

    def test_generic_error(self, monkeypatch):
        """Test error handling for generic exceptions."""

        def mock_popen(*args, **kwargs):
            raise Exception("Something went wrong")

        mock_player = ResolvedPlayer("vlc", Path("vlc"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": False, "video_player": "auto"})
        monkeypatch.setattr("mf.utils.play.subprocess.Popen", mock_popen)
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

        dummy_file = FileResult(Path("/tmp/movie.mp4"))
        with pytest.raises(ClickExit):
            launch_video_player(dummy_file)

    def test_single_file_not_exists(self, monkeypatch, capsys):
        """Test error when trying to play a single file that doesn't exist."""
        mock_player = ResolvedPlayer("vlc", Path("vlc"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": False, "video_player": "auto"})
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False)

        dummy_file = FileResult(Path("/tmp/missing.mp4"))

        with pytest.raises(ClickExit):
            launch_video_player(dummy_file)

        captured = capsys.readouterr()
        assert "File no longer exists" in captured.out
        assert "missing.mp4" in captured.out

    def test_playlist_partial_missing(self, monkeypatch, capsys):
        """Test playlist where some files don't exist - should filter and warn."""
        popen_args = None

        def mock_popen(*args, **kwargs):
            nonlocal popen_args
            popen_args = args[0]

        # Mock exists to return True for a.mp4, False for b.mp4, True for c.mp4
        def mock_exists(self):
            return self.name in ["a.mp4", "c.mp4"]

        mock_player = ResolvedPlayer("vlc", Path("vlc"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": False, "video_player": "auto"})
        monkeypatch.setattr("mf.utils.play.subprocess.Popen", mock_popen)
        monkeypatch.setattr("pathlib.Path.exists", mock_exists)

        test_path_a = Path("/tmp/a.mp4")
        test_path_b = Path("/tmp/b.mp4")
        test_path_c = Path("/tmp/c.mp4")
        playlist = FileResults([
            FileResult(test_path_a),
            FileResult(test_path_b),
            FileResult(test_path_c),
        ])

        launch_video_player(playlist)

        # Should only include existing files
        assert popen_args == ["vlc", str(test_path_a), str(test_path_c)]

        # Check warning was printed
        captured = capsys.readouterr()
        assert "don't exist anymore" in captured.out
        assert "b.mp4" in captured.out

    def test_playlist_all_missing(self, monkeypatch, capsys):
        """Test playlist where all files are missing - should raise error."""
        mock_player = ResolvedPlayer("vlc", Path("vlc"))
        monkeypatch.setattr("mf.utils.play.resolve_configured_player", lambda cfg: mock_player)
        monkeypatch.setattr("mf.utils.play.get_config", lambda: {"fullscreen_playback": False, "video_player": "auto"})
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False)

        playlist = FileResults([
            FileResult(Path("/tmp/a.mp4")),
            FileResult(Path("/tmp/b.mp4")),
        ])

        with pytest.raises(ClickExit):
            launch_video_player(playlist)

        captured = capsys.readouterr()
        assert "All files in playlist don't exist anymore" in captured.out


class TestFileResultsExistence:
    """Tests for FileResults existence checking methods."""

    def test_filter_by_existence(self, monkeypatch, tmp_path):
        """Test filter_by_existence removes non-existent files."""
        # Create one real file
        existing_file = tmp_path / "exists.mp4"
        existing_file.touch()

        missing_file = tmp_path / "missing.mp4"

        results = FileResults([
            FileResult(existing_file),
            FileResult(missing_file),
        ])

        # Should have 2 files before filtering
        assert len(results) == 2

        # Filter in-place
        results.filter_by_existence()

        # Should have 1 file after filtering
        assert len(results) == 1
        assert results[0].file == existing_file

    def test_filter_by_existence_all_exist(self, tmp_path):
        """Test filter_by_existence when all files exist."""
        file1 = tmp_path / "a.mp4"
        file2 = tmp_path / "b.mp4"
        file1.touch()
        file2.touch()

        results = FileResults([
            FileResult(file1),
            FileResult(file2),
        ])

        results.filter_by_existence()

        # Should still have both files
        assert len(results) == 2

    def test_filter_by_existence_none_exist(self, tmp_path):
        """Test filter_by_existence when no files exist."""
        file1 = tmp_path / "missing1.mp4"
        file2 = tmp_path / "missing2.mp4"

        results = FileResults([
            FileResult(file1),
            FileResult(file2),
        ])

        results.filter_by_existence()

        # Should have no files
        assert len(results) == 0

    def test_get_missing(self, tmp_path):
        """Test get_missing returns only non-existent files."""
        existing_file = tmp_path / "exists.mp4"
        existing_file.touch()

        missing_file = tmp_path / "missing.mp4"

        results = FileResults([
            FileResult(existing_file),
            FileResult(missing_file),
        ])

        missing = results.get_missing()

        # Should return new collection with only missing file
        assert len(missing) == 1
        assert missing[0].file == missing_file

        # Original should be unchanged
        assert len(results) == 2

    def test_get_missing_all_exist(self, tmp_path):
        """Test get_missing when all files exist."""
        file1 = tmp_path / "a.mp4"
        file2 = tmp_path / "b.mp4"
        file1.touch()
        file2.touch()

        results = FileResults([
            FileResult(file1),
            FileResult(file2),
        ])

        missing = results.get_missing()

        # Should return empty collection
        assert len(missing) == 0

    def test_get_missing_none_exist(self, tmp_path):
        """Test get_missing when no files exist."""
        file1 = tmp_path / "missing1.mp4"
        file2 = tmp_path / "missing2.mp4"

        results = FileResults([
            FileResult(file1),
            FileResult(file2),
        ])

        missing = results.get_missing()

        # Should return all files
        assert len(missing) == 2
