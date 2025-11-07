from typer.testing import CliRunner

from mf._app_config import app_config

runner = CliRunner()


def test_config_unknown_key_clear():
    """Clearing an unknown key should exit non-zero and show an error."""
    result = runner.invoke(app_config, ["clear", "search:_paths"])  # typo variant
    assert result.exit_code != 0
    assert "Unknown configuration key" in result.stdout
    assert "search:_paths" in result.stdout


def test_config_unknown_key_set():
    """Setting an unknown key should exit non-zero and list available keys."""
    result = runner.invoke(app_config, ["set", "unknown_key_xyz", "1"])
    assert result.exit_code != 0
    assert "Unknown configuration key" in result.stdout
    # Should list registry keys
    for expected in [
        "search_paths",
        "media_extensions",
        "match_extensions",
        "fullscreen_playback",
        "prefer_fd",
    ]:
        assert expected in result.stdout
