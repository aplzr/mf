from pathlib import Path

from typer.testing import CliRunner

import mf.cli_cache as cli_cache
from mf.cli_cache import app_cache

runner = CliRunner()


def test_cache_clear_happy_path(monkeypatch, tmp_path: Path):
    cache_file = tmp_path / "library_cache.json"
    cache_file.write_text("{}")

    # Ensure cli uses our temp cache file (Path, not str)
    monkeypatch.setattr(cli_cache, "get_library_cache_file", lambda: cache_file)

    result = runner.invoke(app_cache, ["clear"])
    assert result.exit_code == 0
    assert not cache_file.exists()
