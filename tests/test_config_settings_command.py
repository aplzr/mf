from typer.testing import CliRunner

from mf.cli_config import app_config
from mf.utils.settings import REGISTRY


def test_settings_command_lists_all_keys():
    runner = CliRunner()
    result = runner.invoke(app_config, ["settings"])  # invoke command
    assert result.exit_code == 0, result.output

    # Each key should appear at least once in output
    for key in REGISTRY:
        assert key in result.output, f"Missing key {key} in settings output"

    # Each help string should appear (or a distinctive prefix if long)
    for key, spec in REGISTRY.items():
        snippet = spec.help.split()[0]  # first word as a minimal presence heuristic
        assert snippet in result.output, f"Missing help snippet for {key}: '{snippet}'"

    # Basic table headers
    assert "Setting" in result.output
    assert "Actions" in result.output
    assert "Description" in result.output


def test_settings_command_shows_kind_and_type():
    runner = CliRunner()
    result = runner.invoke(app_config, ["settings"])  # invoke command
    assert result.exit_code == 0, result.output

    for key, spec in REGISTRY.items():
        # Expect pattern '<kind>, <value_type>'
        expect_fragment = (
            f"{spec.kind}, {spec.value_type.__name__}" if spec.value_type else spec.kind
        )
        assert (
            expect_fragment in result.output
        ), f"Missing kind/type fragment for {key}: {expect_fragment}"
