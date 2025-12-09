from typer.testing import CliRunner

import mf.cli_cache as cli_cache


def test_cli_cache_clear_prints_success(monkeypatch, tmp_path):
    runner = CliRunner()

    fake_cache = tmp_path / "library.json"
    fake_cache.write_text("{}")

    monkeypatch.setattr(cli_cache, "get_library_cache_file", lambda: fake_cache)

    result = runner.invoke(cli_cache.app_cache, ["clear"])

    assert result.exit_code == 0
    assert "Cleared the library cache." in result.stdout
    assert not fake_cache.exists()
