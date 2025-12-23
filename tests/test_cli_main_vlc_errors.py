"""Integration tests for VLC error handling in play command.

Note: Detailed error handling tests are in test_utils_play.py.
These tests verify errors propagate correctly through the CLI.
"""

from typer.testing import CliRunner

from mf.cli_main import app_mf

runner = CliRunner()


def test_play_error_propagates_to_cli(monkeypatch):
    """Integration test: verify that launch_video_player errors propagate to CLI."""
    from pathlib import Path

    class DummyFile:
        name = "movie.mp4"
        parent = Path("/tmp")

    class DummyResult:
        file = DummyFile()

    def mock_resolve(target):
        return DummyResult()

    def mock_launch_with_error(file_to_play):
        # Simulate launch_video_player raising an error
        from mf.utils.console import print_and_raise

        print_and_raise("VLC not found. Please install VLC media player.")

    monkeypatch.setattr("mf.cli_main.resolve_play_target", mock_resolve)
    monkeypatch.setattr("mf.cli_main.launch_video_player", mock_launch_with_error)

    result = runner.invoke(app_mf, ["play", "next"])
    assert result.exit_code != 0
    assert "VLC not found" in (result.stdout + result.stderr)
