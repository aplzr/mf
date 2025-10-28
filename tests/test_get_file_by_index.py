import os
from pathlib import Path

from mf.utils import get_file_by_index, save_search_results


def test_get_file_by_index_valid(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME", str(tmp_path)
    )
    movie_path = tmp_path / "some_movie.mp4"
    movie_path.write_text("data")
    save_search_results("*", [(1, movie_path)])
    assert get_file_by_index(1) == movie_path


def test_get_file_by_index_invalid(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME", str(tmp_path)
    )
    movie_path = Path("/tmp/some_movie.mp4")
    save_search_results("*", [(1, movie_path)])
    import click
    import pytest

    with pytest.raises(click.exceptions.Exit) as exc:
        get_file_by_index(2)
    assert exc.value.exit_code == 1
