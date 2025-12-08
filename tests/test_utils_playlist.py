import json
from pathlib import Path

import pytest
import typer

from mf.utils.file import FileResult
from mf.utils.playlist import (
    get_last_played_index,
    get_next,
    save_last_played,
)


def make_cache(tmp_path: Path, results: list[str], last_played_index=None) -> Path:
    cache_file = tmp_path / "last_search.json"
    data = {"results": results}
    if last_played_index is not None:
        data["last_played_index"] = last_played_index
    cache_file.write_text(json.dumps(data), encoding="utf-8")
    return cache_file


def test_save_and_get_last_played(monkeypatch, tmp_path: Path):
    paths = ["/tmp/a.mp4", "/tmp/b.mp4", "/tmp/c.mp4"]
    # Ensure cache paths match FileResult.__str__ representation
    cache_paths = [str(FileResult.from_string(p)) for p in paths]
    cache_file = make_cache(tmp_path, cache_paths)

    # Point code to temp cache path
    monkeypatch.setattr("mf.utils.playlist.get_search_cache_file", lambda: cache_file)

    # Save b.mp4
    save_last_played(FileResult.from_string(paths[1]))

    # Verify index stored
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert data["last_played_index"] == 1

    # get_last_played_index returns int
    assert get_last_played_index() == 1


def test_get_last_played_index_missing(monkeypatch, tmp_path: Path):
    cache_file = make_cache(tmp_path, ["/tmp/a.mp4"])  # no last_played_index
    monkeypatch.setattr("mf.utils.playlist.get_search_cache_file", lambda: cache_file)
    assert get_last_played_index() is None


def test_get_next_happy_path(monkeypatch, tmp_path: Path):
    paths = ["/tmp/a.mp4", "/tmp/b.mp4", "/tmp/c.mp4"]
    cache_file = make_cache(tmp_path, paths, last_played_index=0)
    monkeypatch.setattr("mf.utils.playlist.get_search_cache_file", lambda: cache_file)
    nxt = get_next()
    assert isinstance(nxt, FileResult)
    assert str(nxt.file).endswith("b.mp4")


def test_get_next_raises_on_end(monkeypatch, tmp_path: Path):
    paths = ["/tmp/a.mp4"]
    cache_file = make_cache(tmp_path, paths, last_played_index=0)
    monkeypatch.setattr("mf.utils.playlist.get_search_cache_file", lambda: cache_file)
    # IndexError triggers print_and_raise -> typer.Exit
    with pytest.raises(typer.Exit):
        get_next()
