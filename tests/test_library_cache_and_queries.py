import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from mf.utils import read_config, write_config
from mf.utils.file_utils import (
    FileResult,
    FindQuery,
    NewQuery,
    filter_scan_results,
    get_library_cache_file,
    get_result_by_index,
    load_library_cache,
    save_search_results,
    scan_for_media_files,
    sort_scan_results,
)


@pytest.fixture()
def isolated_media_dir(tmp_path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    # Update config to use this search path only
    cfg = read_config()
    cfg["search_paths"] = [media_dir.as_posix()]
    cfg["cache_library"] = True
    cfg["library_cache_interval"] = "10m"  # non-zero default for most tests
    write_config(cfg)
    return media_dir


def create_files(directory: Path, names: list[str]):
    files = []
    for name in names:
        p = directory / name
        p.write_text("x")
        files.append(p)
    return files


def test_library_cache_rebuild_on_missing(isolated_media_dir):
    # Initially cache file does not exist, so load_library_cache should rebuild.
    create_files(isolated_media_dir, ["a.mkv", "b.mp4"])  # two media files
    cache_file = get_library_cache_file()
    assert not cache_file.exists()
    results = load_library_cache()
    assert cache_file.exists()
    # Rebuild sorts by mtime descending; ensure both present
    names = {r.file.name for r in results}
    assert names == {"a.mkv", "b.mp4"}


def test_library_cache_no_expiry_zero_interval(isolated_media_dir):
    # Set interval to zero so cache never expires.
    cfg = read_config()
    cfg["library_cache_interval"] = "0s"
    write_config(cfg)
    create_files(isolated_media_dir, ["c1.mkv"])  # one file
    results_first = load_library_cache()
    cache_file = get_library_cache_file()
    first_mtime = cache_file.stat().st_mtime
    # Touch underlying file to change its mtime; cache should NOT rebuild.
    os.utime(isolated_media_dir / "c1.mkv", None)
    results_second = load_library_cache()
    second_mtime = cache_file.stat().st_mtime
    assert first_mtime == second_mtime  # unchanged => not rebuilt
    assert results_first[0].file == results_second[0].file


def test_library_cache_corruption_rebuild(isolated_media_dir, capsys):
    # Write corrupt library.json then call load_library_cache; should warn and rebuild.
    create_files(isolated_media_dir, ["d1.mkv"])  # seed directory
    cache_file = get_library_cache_file()
    cache_file.write_text("{ invalid json")
    results = load_library_cache()
    captured = capsys.readouterr()
    assert "Cache corrupted" in captured.out
    assert any(r.file.name == "d1.mkv" for r in results)


def test_get_result_by_index_file_deleted(isolated_media_dir, capsys):
    # Save search results then delete file; get_result_by_index should print an error.
    f = create_files(isolated_media_dir, ["gone.mkv"])[0]
    save_search_results("*", [FileResult(f)])
    f.unlink()
    import click

    with pytest.raises(click.exceptions.Exit):
        get_result_by_index(1)
    captured = capsys.readouterr()
    assert "File no longer exists" in captured.out


def test_filter_scan_results_pattern_and_extension():
    # Build sample FileResult list
    files = [
        FileResult(Path("/tmp/movie1.mkv")),
        FileResult(Path("/tmp/clip.avi")),
        FileResult(Path("/tmp/movie2.mp4")),
        FileResult(Path("/tmp/other.txt")),
    ]
    media_exts = {".mkv", ".mp4"}
    # Pattern that matches 'movie*'
    filtered = filter_scan_results(files, "movie*", media_exts, match_extensions=True)
    names = [f.file.name for f in filtered]
    assert names == ["movie1.mkv", "movie2.mp4"]


def test_sort_scan_results_alphabetical():
    # Unsorted alphabetical
    files = [
        FileResult(Path("/tmp/B.mkv")),
        FileResult(Path("/tmp/a.mkv")),
        FileResult(Path("/tmp/C.mkv")),
    ]
    sorted_results = sort_scan_results(files)
    assert [f.file.name for f in sorted_results] == ["a.mkv", "B.mkv", "C.mkv"]


def test_scan_for_media_files_fd_fallback(monkeypatch, isolated_media_dir):
    # Force fd failure to exercise fallback branch.
    create_files(isolated_media_dir, ["fd1.mkv"])  # seed directory

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "fd")  # type: ignore[name-defined]

    import subprocess

    monkeypatch.setattr(subprocess, "run", fake_run)
    cfg = read_config()
    cfg["prefer_fd"] = True
    write_config(cfg)
    results = scan_for_media_files("*", with_mtime=False, prefer_fd=True)
    assert any(r.file.name == "fd1.mkv" for r in results)


def test_new_query_cache_enabled(monkeypatch, isolated_media_dir):
    # Build pre-existing (non-expired) cache file; ensure NewQuery uses cached path.
    file_path = isolated_media_dir / "new1.mkv"
    file_path.write_text("x")
    cache_file = get_library_cache_file()
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "files": [file_path.as_posix()],
    }
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache_data))

    # Monkeypatch scan_for_media_files to raise if called (we expect cached path).
    monkeypatch.setattr(
        "mf.utils.file_utils.scan_for_media_files",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("should not scan")),
    )
    results = NewQuery(5).execute()
    assert [r.file.name for r in results] == ["new1.mkv"]


def test_find_query_cache_enabled(monkeypatch, isolated_media_dir):
    # Build a pre-existing cache file and ensure FindQuery uses it instead of scanning.
    file_path = isolated_media_dir / "find1.mkv"
    file_path.write_text("x")
    other_path = isolated_media_dir / "other.txt"
    other_path.write_text("x")
    cache_file = get_library_cache_file()
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "files": [file_path.as_posix(), other_path.as_posix()],
    }
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache_data))
    monkeypatch.setattr(
        "mf.utils.file_utils.scan_for_media_files",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("should not scan")),
    )
    results = FindQuery("*.mkv").execute()
    # Only the .mkv file should remain after filtering
    assert [r.file.name for r in results] == ["find1.mkv"]
