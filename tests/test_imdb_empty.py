import os

import click
import pytest

from mf._app_mf import imdb
from mf.utils import add_search_path, read_config, save_search_results, write_config


class DummyIMDb:
    def search_movie(self, title):
        return []


def test_imdb_no_results(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    # Use a filename that guessit might or might not parse; we monkeypatch guessit anyway
    movie = media_dir / "Some.Movie.2024.1080p.mp4"
    movie.write_text("x")
    cfg = add_search_path(cfg, str(media_dir))
    write_config(cfg)
    save_search_results("*", [(1, movie)])

    # Monkeypatch IMDb class used inside imdb command
    import mf._app_mf as app_mf_module

    app_mf_module.IMDb = lambda: DummyIMDb()

    # Monkeypatch guessit to ensure a parsed title is present so we test IMDb empty branch
    app_mf_module.guessit = lambda filestem: {"title": "Some Movie"}

    with pytest.raises(click.exceptions.Exit) as exc:
        imdb(index=1)
    assert exc.value.exit_code == 1
