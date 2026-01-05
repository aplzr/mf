from typer.testing import CliRunner

import mf.cli_main as cli_main


def test_cli_stats_command_runs(monkeypatch):
    """Test that stats command executes print_stats."""
    runner = CliRunner()

    # Track whether print_stats was called
    called = []

    def fake_print_stats():
        called.append(True)

    # Mock print_stats since cli command just delegates to it
    monkeypatch.setattr(cli_main, "print_stats", fake_print_stats)

    result = runner.invoke(cli_main.app_mf, ["stats"])

    assert result.exit_code == 0
    assert len(called) == 1
