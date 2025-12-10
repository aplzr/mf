from pathlib import Path

from typer.testing import CliRunner

import mf.cli_cache as cli_cache


def test_cli_cache_file_outputs_path(monkeypatch, tmp_path):
    runner = CliRunner()

    fake_cache = tmp_path / "library.json"
    fake_cache.write_text("{}")

    monkeypatch.setattr(cli_cache, "get_library_cache_file", lambda: fake_cache)

    result = runner.invoke(cli_cache.app_cache, ["file"])

    assert result.exit_code == 0
    # Should print the path
    out = result.stdout.strip()
    assert Path(out) == fake_cache
