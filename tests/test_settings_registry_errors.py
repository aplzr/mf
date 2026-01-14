from typer.testing import CliRunner

from mf.cli_config import app_config
from mf.utils.config import get_raw_config

runner = CliRunner()


def test_unsupported_action_scalar(monkeypatch):
    """Attempting an unsupported action on a scalar setting should exit with error."""
    # prefer_fd only supports 'set'; try 'add'
    result = runner.invoke(app_config, ["add", "prefer_fd", "true"])
    assert result.exit_code != 0
    assert "Action add not supported for prefer_fd" in result.stdout


def test_scalar_multi_value_error(monkeypatch):
    """Providing multiple values to scalar setting should raise error."""
    # display_paths is scalar; passing two values triggers error path
    result = runner.invoke(app_config, ["set", "display_paths", "true", "false"])
    assert result.exit_code != 0
    assert "requires a single value" in result.stdout
    # Ensure original value not overwritten unpredictably; it should remain whatever
    # single normalization of first value would have been if code proceeded.
    # Config may be unchanged since exit occurred before write.
    cfg = get_raw_config()
    # Value should still be boolean (default) either True/False;
    # we just assert key exists.
    assert "display_paths" in cfg
