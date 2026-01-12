"""Tests for RAR archive extraction and handling."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from mf.constants import TEMP_DIR_PREFIX
from mf.utils.file import (
    FileResult,
    FileResults,
    extract_rar,
    is_unrar_present,
    remove_temp_paths,
)


class TestFileResultIsRar:
    """Tests for FileResult.is_rar() method."""

    def test_is_rar_with_rar_extension(self):
        """Test that .rar files are identified correctly."""
        result = FileResult(Path("/path/to/movie.rar"))
        assert result.is_rar() is True

    def test_is_rar_with_uppercase_extension(self):
        """Test that .RAR files (uppercase) are identified correctly."""
        result = FileResult(Path("/path/to/movie.RAR"))
        assert result.is_rar() is True

    def test_is_rar_with_mixed_case_extension(self):
        """Test that .RaR files (mixed case) are identified correctly."""
        result = FileResult(Path("/path/to/movie.RaR"))
        assert result.is_rar() is True

    def test_is_rar_with_video_extension(self):
        """Test that video files return False."""
        result = FileResult(Path("/path/to/movie.mp4"))
        assert result.is_rar() is False

    def test_is_rar_with_no_extension(self):
        """Test that files without extension return False."""
        result = FileResult(Path("/path/to/movie"))
        assert result.is_rar() is False


class TestFileResultsIsRar:
    """Tests for FileResults.is_rar() method."""

    def test_is_rar_with_all_rar_files(self):
        """Test that collection with all RAR files returns True."""
        results = FileResults([
            FileResult(Path("/path/to/movie1.rar")),
            FileResult(Path("/path/to/movie2.rar")),
        ])
        assert results.is_rar() is True

    def test_is_rar_with_one_rar_file(self):
        """Test that collection with one RAR file returns True."""
        results = FileResults([
            FileResult(Path("/path/to/movie1.mp4")),
            FileResult(Path("/path/to/movie2.rar")),
            FileResult(Path("/path/to/movie3.mkv")),
        ])
        assert results.is_rar() is True

    def test_is_rar_with_no_rar_files(self):
        """Test that collection with no RAR files returns False."""
        results = FileResults([
            FileResult(Path("/path/to/movie1.mp4")),
            FileResult(Path("/path/to/movie2.mkv")),
        ])
        assert results.is_rar() is False

    def test_is_rar_with_empty_collection(self):
        """Test that empty collection returns False."""
        results = FileResults([])
        assert results.is_rar() is False


class TestIsUnrarPresent:
    """Tests for is_unrar_present() function."""

    @patch("mf.utils.file.supported_formats")
    def test_is_unrar_present_with_rar_support(self, mock_supported):
        """Test when RAR extraction is available."""
        mock_supported.return_value = ["zip", "rar", "tar"]
        assert is_unrar_present() is True
        mock_supported.assert_called_once_with(operations=["extract"])

    @patch("mf.utils.file.supported_formats")
    def test_is_unrar_present_without_rar_support(self, mock_supported):
        """Test when RAR extraction is not available."""
        mock_supported.return_value = ["zip", "tar"]
        assert is_unrar_present() is False
        mock_supported.assert_called_once_with(operations=["extract"])


class TestExtractRar:
    """Tests for extract_rar() function."""

    @patch("mf.utils.file.is_unrar_present")
    def test_extract_rar_without_unrar_tool(self, mock_is_present):
        """Test that error is raised when no extraction tool is available."""
        mock_is_present.return_value = False
        result = FileResult(Path("/path/to/movie.rar"))

        with pytest.raises(typer.Exit):
            extract_rar(result, [".mp4", ".mkv"])

    @patch("mf.utils.file.is_unrar_present")
    @patch("mf.utils.file.extract_archive")
    @patch("mf.utils.file.tempfile.mkdtemp")
    def test_extract_rar_success(self, mock_mkdtemp, mock_extract, mock_is_present, tmp_path):
        """Test successful RAR extraction."""
        mock_is_present.return_value = True
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)
        mock_extract.return_value = str(temp_dir)

        # Create a fake extracted video file
        video_file = temp_dir / "movie.mp4"
        video_file.write_text("video data")

        result = FileResult(Path("/path/to/movie.rar"))
        extracted = extract_rar(result, [".mp4", ".mkv", ".avi"])

        assert extracted.file == video_file
        mock_mkdtemp.assert_called_once_with(prefix=TEMP_DIR_PREFIX)
        mock_extract.assert_called_once_with(str(result.file), outdir=str(temp_dir))

    @patch("mf.utils.file.is_unrar_present")
    @patch("mf.utils.file.extract_archive")
    @patch("mf.utils.file.tempfile.mkdtemp")
    def test_extract_rar_empty_archive(self, mock_mkdtemp, mock_extract, mock_is_present, tmp_path):
        """Test extraction of empty archive."""
        mock_is_present.return_value = True
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)
        mock_extract.return_value = str(temp_dir)

        result = FileResult(Path("/path/to/empty.rar"))

        with pytest.raises(typer.Exit):
            extract_rar(result, [".mp4", ".mkv"])

    @patch("mf.utils.file.is_unrar_present")
    @patch("mf.utils.file.extract_archive")
    @patch("mf.utils.file.tempfile.mkdtemp")
    def test_extract_rar_no_video_files(self, mock_mkdtemp, mock_extract, mock_is_present, tmp_path):
        """Test extraction when archive contains no video files."""
        mock_is_present.return_value = True
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)
        mock_extract.return_value = str(temp_dir)

        # Create a fake extracted non-video file
        text_file = temp_dir / "readme.txt"
        text_file.write_text("readme")

        result = FileResult(Path("/path/to/movie.rar"))

        with pytest.raises(typer.Exit):
            extract_rar(result, [".mp4", ".mkv"])

    @patch("mf.utils.file.is_unrar_present")
    @patch("mf.utils.file.extract_archive")
    @patch("mf.utils.file.tempfile.mkdtemp")
    def test_extract_rar_multiple_video_files(self, mock_mkdtemp, mock_extract, mock_is_present, tmp_path):
        """Test extraction when archive contains multiple video files (picks largest)."""
        mock_is_present.return_value = True
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)
        mock_extract.return_value = str(temp_dir)

        # Create multiple video files with different sizes
        small_video = temp_dir / "small.mp4"
        small_video.write_text("small")

        large_video = temp_dir / "large.mp4"
        large_video.write_text("large video content")

        result = FileResult(Path("/path/to/movie.rar"))
        extracted = extract_rar(result, [".mp4", ".mkv"])

        # Should return the largest video file
        assert extracted.file == large_video

    @patch("mf.utils.file.is_unrar_present")
    @patch("mf.utils.file.extract_archive")
    @patch("mf.utils.file.tempfile.mkdtemp")
    def test_extract_rar_nested_directory(self, mock_mkdtemp, mock_extract, mock_is_present, tmp_path):
        """Test extraction when video is in nested directory."""
        mock_is_present.return_value = True
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        nested_dir = temp_dir / "subfolder"
        nested_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)
        mock_extract.return_value = str(temp_dir)

        # Create a video file in nested directory
        video_file = nested_dir / "movie.mp4"
        video_file.write_text("video data")

        result = FileResult(Path("/path/to/movie.rar"))
        extracted = extract_rar(result, [".mp4", ".mkv"])

        assert extracted.file == video_file


class TestRemoveTempPaths:
    """Tests for remove_temp_paths() function."""

    def test_remove_temp_paths_no_directories(self, tmp_path, monkeypatch):
        """Test when no temporary directories exist."""
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        # Should not raise any errors
        remove_temp_paths()

    def test_remove_temp_paths_old_directory(self, tmp_path, monkeypatch):
        """Test removal of old temporary directory."""
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

        old_dir = tmp_path / f"{TEMP_DIR_PREFIX}old"
        old_dir.mkdir()

        # Set mtime to 4 hours ago (older than default 3 hour threshold)
        import time
        old_mtime = time.time() - 14400
        os.utime(old_dir, (old_mtime, old_mtime))

        remove_temp_paths(max_age=10800)  # 3 hours

        assert not old_dir.exists()

    def test_remove_temp_paths_recent_directory(self, tmp_path, monkeypatch):
        """Test that recent temporary directories are not removed."""
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

        recent_dir = tmp_path / f"{TEMP_DIR_PREFIX}recent"
        recent_dir.mkdir()

        # Directory is new, should not be removed
        remove_temp_paths(max_age=10800)  # 3 hours

        assert recent_dir.exists()

    def test_remove_temp_paths_mixed_ages(self, tmp_path, monkeypatch):
        """Test removal with both old and recent directories."""
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

        import time
        old_mtime = time.time() - 14400

        old_dir1 = tmp_path / f"{TEMP_DIR_PREFIX}old1"
        old_dir1.mkdir()
        os.utime(old_dir1, (old_mtime, old_mtime))

        old_dir2 = tmp_path / f"{TEMP_DIR_PREFIX}old2"
        old_dir2.mkdir()
        os.utime(old_dir2, (old_mtime, old_mtime))

        recent_dir = tmp_path / f"{TEMP_DIR_PREFIX}recent"
        recent_dir.mkdir()

        remove_temp_paths(max_age=10800)

        assert not old_dir1.exists()
        assert not old_dir2.exists()
        assert recent_dir.exists()

    def test_remove_temp_paths_with_content(self, tmp_path, monkeypatch):
        """Test removal of directory with files inside."""
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

        import time
        old_mtime = time.time() - 14400

        old_dir = tmp_path / f"{TEMP_DIR_PREFIX}old"
        old_dir.mkdir()

        # Create some files inside
        (old_dir / "file1.txt").write_text("content1")
        (old_dir / "file2.txt").write_text("content2")
        nested = old_dir / "nested"
        nested.mkdir()
        (nested / "file3.txt").write_text("content3")

        os.utime(old_dir, (old_mtime, old_mtime))

        remove_temp_paths(max_age=10800)

        assert not old_dir.exists()

    def test_remove_temp_paths_ignores_other_directories(self, tmp_path, monkeypatch):
        """Test that non-mediafinder directories are ignored."""
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

        import time
        old_mtime = time.time() - 14400

        # Create a directory without the mediafinder prefix
        other_dir = tmp_path / "some_other_temp_dir"
        other_dir.mkdir()
        os.utime(other_dir, (old_mtime, old_mtime))

        remove_temp_paths(max_age=10800)

        # Should not be deleted
        assert other_dir.exists()

    def test_remove_temp_paths_permission_error(self, tmp_path, monkeypatch, capsys):
        """Test handling of permission errors during deletion."""
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

        import time
        old_mtime = time.time() - 14400

        old_dir = tmp_path / f"{TEMP_DIR_PREFIX}old"
        old_dir.mkdir()
        os.utime(old_dir, (old_mtime, old_mtime))

        # Mock rmtree to raise a PermissionError
        with patch("mf.utils.file.rmtree", side_effect=PermissionError("Access denied")):
            remove_temp_paths(max_age=10800)

        # Should print warning but not crash
        captured = capsys.readouterr()
        assert "Could not delete temporary directory" in captured.out

    def test_remove_temp_paths_custom_max_age(self, tmp_path, monkeypatch):
        """Test with custom max_age parameter."""
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

        import time
        # Create directory that's 2 hours old
        two_hours_ago = time.time() - 7200

        dir_2h = tmp_path / f"{TEMP_DIR_PREFIX}2h"
        dir_2h.mkdir()
        os.utime(dir_2h, (two_hours_ago, two_hours_ago))

        # Should be removed with 1 hour threshold
        remove_temp_paths(max_age=3600)
        assert not dir_2h.exists()

        # Create another directory that's 2 hours old
        dir_2h_2 = tmp_path / f"{TEMP_DIR_PREFIX}2h_2"
        dir_2h_2.mkdir()
        os.utime(dir_2h_2, (two_hours_ago, two_hours_ago))

        # Should not be removed with 3 hour threshold
        remove_temp_paths(max_age=10800)
        assert dir_2h_2.exists()
