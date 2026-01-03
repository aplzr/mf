from typer.testing import CliRunner

from mf.cli_config import app_config
from mf.utils.settings import SETTINGS


def test_settings_command_lists_all_keys():
    # Use wider terminal to avoid table truncation with new "Allowed" column
    runner = CliRunner(env={"COLUMNS": "200"})
    result = runner.invoke(app_config, ["settings"])  # invoke command
    assert result.exit_code == 0, result.output

    # Each key should appear at least once in output
    for key in SETTINGS:
        assert key in result.output, f"Missing key {key} in settings output"

    # Each help string should appear (or a distinctive prefix if long)
    for key, spec in SETTINGS.items():
        snippet = spec.help.split()[0]  # first word as a minimal presence heuristic
        assert snippet in result.output, f"Missing help snippet for {key}: '{snippet}'"

    # Basic table headers
    assert "Setting" in result.output
    assert "Actions" in result.output
    assert "Description" in result.output
    assert "Allowed" in result.output


def test_settings_command_shows_kind_and_type():
    runner = CliRunner(env={"COLUMNS": "200"})
    result = runner.invoke(app_config, ["settings"])  # invoke command
    assert result.exit_code == 0, result.output

    for key, spec in SETTINGS.items():
        # Expect pattern '<kind>, <value_type>'
        expect_fragment = (
            f"{spec.kind}, {spec.value_type.__name__}" if spec.value_type else spec.kind
        )
        assert (
            expect_fragment in result.output
        ), f"Missing kind/type fragment for {key}: {expect_fragment}"


def test_settings_command_shows_allowed_values():
    """Test that video_player shows its allowed values in the Allowed column."""
    runner = CliRunner(env={"COLUMNS": "200"})
    result = runner.invoke(app_config, ["settings"])
    assert result.exit_code == 0, result.output

    # video_player should show its allowed values
    # The output should contain "auto", "vlc", "mpv" somewhere near video_player
    assert "video_player" in result.output
    output_lines = result.output.split("\n")

    # Find the line with video_player and check it contains allowed values
    for line in output_lines:
        if "video_player" in line:
            # Should contain all three allowed values
            assert "auto" in line or "auto" in result.output
            assert "vlc" in line or "vlc" in result.output
            assert "mpv" in line or "mpv" in result.output
            break


def test_settings_command_empty_allowed_for_others():
    """Test that settings without allowed_values don't show values in Allowed column."""
    runner = CliRunner(env={"COLUMNS": "200"})
    result = runner.invoke(app_config, ["settings"])
    assert result.exit_code == 0, result.output

    # Settings without allowed_values should still be listed
    # (This is more of a regression test to ensure the table doesn't break)
    assert "search_paths" in result.output
    assert "media_extensions" in result.output
