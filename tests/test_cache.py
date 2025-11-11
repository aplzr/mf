import os
from pathlib import Path

from mf.utils.file import (
    FileResult,
    get_search_cache_file,
    load_search_results,
    save_search_results,
)


def test_save_and_load_cache(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME", str(tmp_path)
    )
    cache_file = get_search_cache_file()
    assert cache_file.parent.exists()

    results = [FileResult(Path("/tmp/movie1.mp4")), FileResult(Path("/tmp/movie2.mkv"))]
    save_search_results("*movie*", results)

    pattern, loaded_results, timestamp = load_search_results()
    assert pattern == "*movie*"
    assert [r.file for r in loaded_results] == [
        Path("/tmp/movie1.mp4"),
        Path("/tmp/movie2.mkv"),
    ]
    assert timestamp is not None
