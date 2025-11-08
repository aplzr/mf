from typer.testing import CliRunner

from mf._app_mf import app_mf
from mf.utils import save_search_results

runner = CliRunner()


def _seed_cache(tmp_path):
    f = tmp_path / "movie.mkv"
    f.write_text("x")
    save_search_results("*", [f])


def test_imdb_parse_failure(monkeypatch, tmp_path):
    _seed_cache(tmp_path)
    import mf._app_mf as app_mod

    monkeypatch.setattr(app_mod, "guessit", lambda _name: {})  # no 'title'
    r = runner.invoke(app_mf, ["imdb", "1"])
    assert r.exit_code != 0
    assert "Could not parse" in r.stdout


def test_imdb_network_exception(monkeypatch, tmp_path):
    _seed_cache(tmp_path)
    import mf._app_mf as app_mod

    class FakeIMDb:
        def search_movie(self, title):  # noqa: D401
            raise RuntimeError("netfail")

    monkeypatch.setattr(app_mod, "IMDb", lambda: FakeIMDb())
    r = runner.invoke(app_mf, ["imdb", "1"])
    # Command continues after error printing; may not exit depending on code path
    # We assert error message presence.
    assert "IMDb lookup failed" in r.stdout


def test_imdb_no_results(monkeypatch, tmp_path):
    _seed_cache(tmp_path)
    import mf._app_mf as app_mod

    class FakeIMDbEmpty:
        def search_movie(self, title):  # noqa: D401
            return []

    monkeypatch.setattr(app_mod, "IMDb", lambda: FakeIMDbEmpty())
    r = runner.invoke(app_mf, ["imdb", "1"])
    assert "No IMDb results" in r.stdout
