import os
from pathlib import Path

from mf.utils.file import (
    FileResults,
    get_search_cache_file,
)
from mf.utils.search import load_search_results, save_search_results


def test_save_and_load_cache(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME", str(tmp_path)
    )
    cache_file = get_search_cache_file()
    assert cache_file.parent.exists()

    relative_paths = [
        Path("/tmp/movie1.mp4"),
        Path("/tmp/movie2.mkv"),
    ]

    results = FileResults.from_paths(relative_paths)
    save_search_results("*movie*", results)

    pattern, loaded_results, timestamp = load_search_results()
    assert pattern == "*movie*"

    for expected, actual in zip(relative_paths, loaded_results):
        assert expected.as_posix() in str(actual)
        print(expected.as_posix(), str(actual))

    assert timestamp is not None
