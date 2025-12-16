import pickle
from pathlib import Path

from typer.testing import CliRunner

import mf.cli_cache as cli_cache
from mf.utils.cache import PICKLE_PROTOCOL


def test_cli_cache_file_outputs_path(monkeypatch, tmp_path):
    runner = CliRunner()

    fake_cache = tmp_path / "library.pkl"
    with open(fake_cache, "wb") as f:
        pickle.dump({"timestamp": "2025-01-01T00:00:00", "files": []}, f, protocol=PICKLE_PROTOCOL)

    monkeypatch.setattr(cli_cache, "get_library_cache_file", lambda: fake_cache)

    result = runner.invoke(cli_cache.app_cache, ["file"])

    assert result.exit_code == 0
    # Should print the path
    out = result.stdout.strip()
    assert Path(out) == fake_cache
