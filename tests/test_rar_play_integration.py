"""Integration tests for playing RAR archives."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from mf.cli_main import app_mf
from mf.utils.file import FileResult, FileResults

runner = CliRunner()


class TestPlayRarIntegration:
    """Integration tests for playing RAR files with mf play command."""

    @patch("mf.cli_main.launch_video_player")
    @patch("mf.cli_main.extract_rar")
    @patch("mf.cli_main.resolve_play_target")
    def test_play_rar_file_by_index(
        self,
        mock_resolve,
        mock_extract,
        mock_launch,
        tmp_path,
    ):
        """Test playing a RAR file by index."""
        rar_file = FileResult(Path("/path/to/movie.rar"))
        extracted_file = FileResult(tmp_path / "movie.mp4")

        mock_resolve.return_value = rar_file
        mock_extract.return_value = extracted_file

        result = runner.invoke(app_mf, ["play", "1"])

        assert result.exit_code == 0
        mock_extract.assert_called_once()
        mock_launch.assert_called_once()
        # Verify that the extracted file was passed to launch_video_player
        call_args = mock_launch.call_args
        assert call_args[0][0] == extracted_file

    @patch("mf.cli_main.launch_video_player")
    @patch("mf.cli_main.resolve_play_target")
    def test_play_regular_video_file(
        self,
        mock_resolve,
        mock_launch,
        tmp_path,
    ):
        """Test playing a regular video file (not RAR)."""
        video_file = FileResult(tmp_path / "movie.mp4")
        mock_resolve.return_value = video_file

        result = runner.invoke(app_mf, ["play", "1"])

        assert result.exit_code == 0
        mock_launch.assert_called_once()
        # Should pass the original file without extraction
        call_args = mock_launch.call_args
        assert call_args[0][0] == video_file

    @patch("mf.cli_main.resolve_play_target")
    def test_play_list_with_rar_file_errors(self, mock_resolve):
        """Test that playing list with RAR files shows error."""
        results = FileResults([
            FileResult(Path("/path/to/movie1.mp4")),
            FileResult(Path("/path/to/movie2.rar")),
        ])
        mock_resolve.return_value = results

        result = runner.invoke(app_mf, ["play", "list"])

        assert result.exit_code == 1
        assert ".rar files" in result.stdout or "not supported" in result.stdout

    @patch("mf.cli_main.launch_video_player")
    @patch("mf.cli_main.resolve_play_target")
    def test_play_list_without_rar_files(self, mock_resolve, mock_launch):
        """Test that playing list works when no RAR files are present."""
        results = FileResults([
            FileResult(Path("/path/to/movie1.mp4")),
            FileResult(Path("/path/to/movie2.mkv")),
        ])
        mock_resolve.return_value = results

        result = runner.invoke(app_mf, ["play", "list"])

        assert result.exit_code == 0
        mock_launch.assert_called_once()

    @patch("mf.cli_main.extract_rar")
    @patch("mf.cli_main.resolve_play_target")
    def test_play_rar_extraction_fails(self, mock_resolve, mock_extract):
        """Test error handling when RAR extraction fails."""
        rar_file = FileResult(Path("/path/to/movie.rar"))
        mock_resolve.return_value = rar_file

        # Mock extract_rar to raise SystemExit (like print_and_raise does)
        mock_extract.side_effect = SystemExit(1)

        result = runner.invoke(app_mf, ["play", "1"])

        assert result.exit_code == 1
        mock_extract.assert_called_once()


class TestPlayRarWithConfig:
    """Test RAR playback with different config settings."""

    @patch("mf.cli_main.launch_video_player")
    @patch("mf.cli_main.extract_rar")
    @patch("mf.cli_main.resolve_play_target")
    def test_play_rar_respects_media_extensions(
        self,
        mock_resolve,
        mock_extract,
        mock_launch,
        tmp_path,
    ):
        """Test that extract_rar is called with media_extensions from config."""
        rar_file = FileResult(Path("/path/to/movie.rar"))
        extracted_file = FileResult(tmp_path / "movie.mp4")

        mock_resolve.return_value = rar_file
        mock_extract.return_value = extracted_file

        result = runner.invoke(app_mf, ["play", "1"])

        assert result.exit_code == 0
        # Verify extract_rar was called with media_extensions
        mock_extract.assert_called_once()
        call_args = mock_extract.call_args
        # Second argument should be the media_extensions list
        assert isinstance(call_args[0][1], list)
        assert ".mp4" in call_args[0][1] or ".mkv" in call_args[0][1]


class TestMainCallbackCleanup:
    """Test that main_callback calls remove_temp_paths."""

    @patch("mf.cli_main.remove_temp_paths")
    def test_main_callback_removes_temp_paths(self, mock_remove):
        """Test that remove_temp_paths is called on startup."""
        # Use no arguments to trigger callback without subcommand
        result = runner.invoke(app_mf, [])

        assert result.exit_code == 0
        mock_remove.assert_called_once()

    @patch("mf.cli_main.remove_temp_paths")
    @patch("mf.cli_main.FindQuery")
    def test_main_callback_cleanup_on_find_command(self, mock_query, mock_remove):
        """Test that cleanup happens when running commands."""
        mock_instance = MagicMock()
        mock_instance.execute.return_value = []
        mock_query.return_value = mock_instance

        result = runner.invoke(app_mf, ["find", "test"])

        # remove_temp_paths should be called
        mock_remove.assert_called_once()
