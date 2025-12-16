import pickle
from pathlib import Path

from typer.testing import CliRunner

from mf.cli_cache import app_cache
from mf.utils.cache import PICKLE_PROTOCOL

runner = CliRunner()


def test_cache_clear_success(monkeypatch, tmp_path: Path):
    cache_file = tmp_path / "library.pkl"
    with open(cache_file, "wb") as f:
        pickle.dump({"timestamp": "2025-01-01T00:00:00", "files": []}, f, protocol=PICKLE_PROTOCOL)

    # Patch the symbol used inside cli_cache module
    monkeypatch.setattr("mf.cli_cache.get_library_cache_file", lambda: cache_file)

    result = runner.invoke(app_cache, ["clear"])
    assert result.exit_code == 0
    assert "Cleared the library cache" in result.stdout
    assert not cache_file.exists()
