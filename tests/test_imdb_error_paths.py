from typer.testing import CliRunner

from mf.cli_main import app_mf
from mf.utils.file import FileResult, save_search_results

runner = CliRunner()


def _seed_cache(tmp_path):
    f = tmp_path / "movie.mkv"
    f.write_text("x")
    save_search_results("*", [FileResult(f)])


def test_imdb_parse_failure(monkeypatch, tmp_path):
    _seed_cache(tmp_path)
    import mf.cli_main as app_mod

    monkeypatch.setattr(app_mod, "guessit", lambda _name: {})  # no 'title'
    r = runner.invoke(app_mf, ["imdb", "1"])
    assert r.exit_code != 0
    assert "Could not parse" in r.stdout
