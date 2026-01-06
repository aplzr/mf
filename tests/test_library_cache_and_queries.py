import json
import os
import pickle
from datetime import datetime
from pathlib import Path

import pytest

from mf.utils.cache import PICKLE_PROTOCOL, load_library_cache
from mf.utils.config import get_config, write_config
from mf.utils.file import (
    FileResult,
    FileResults,
    get_cache_dir,
    get_library_cache_file,
)
from mf.utils.library import split_by_search_path
from mf.utils.scan import FindQuery, NewQuery, scan_search_paths
from mf.utils.search import get_result_by_index, save_search_results


@pytest.fixture()
def isolated_media_dir(tmp_path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    # Update config to use this search path only
    cfg = get_config()
    cfg["search_paths"] = [media_dir.as_posix()]
    cfg["cache_library"] = True
    cfg["library_cache_interval"] = 600  # non-zero default for most tests
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
    cfg = get_config()
    cfg["library_cache_interval"] = "0"
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
    # Write corrupt pickle then call load_library_cache; should warn and rebuild.
    create_files(isolated_media_dir, ["d1.mkv"])  # seed directory
    cache_file = get_library_cache_file()
    cache_file.write_bytes(b"invalid pickle data")
    results = load_library_cache()
    captured = capsys.readouterr()
    assert "Cache corrupted" in captured.out
    assert any(r.file.name == "d1.mkv" for r in results)


def test_scan_for_media_files_fd_fallback(monkeypatch, isolated_media_dir):
    # Force fd failure to exercise fallback branch.
    create_files(isolated_media_dir, ["fd1.mkv"])  # seed directory

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "fd")  # type: ignore[name-defined]

    import subprocess

    monkeypatch.setattr(subprocess, "run", fake_run)
    cfg = get_config()
    cfg["prefer_fd"] = True
    write_config(cfg)
    results = scan_search_paths(cache_stat=False, prefer_fd=True)
    assert any(r.file.name == "fd1.mkv" for r in results)


def test_new_query_cache_enabled(monkeypatch, isolated_media_dir):
    # Build pre-existing (non-expired) cache file; ensure NewQuery uses cached path.
    file_path = isolated_media_dir / "new1.mkv"
    file_path.write_text("x")
    stat_info = [0] * 10
    cache_file = get_library_cache_file()
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "files": [(file_path.as_posix(), stat_info)],
    }
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "wb") as f:
        pickle.dump(cache_data, f, protocol=PICKLE_PROTOCOL)

    # Monkeypatch scan_search_paths to raise if called (we expect cached path).
    monkeypatch.setattr(
        "mf.utils.scan.scan_search_paths",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("should not scan")),
    )
    # Use direct instantiation with explicit parameters (no need to mock get_config!)
    results = NewQuery(
        5, cache_library=True, media_extensions=[".mkv"], match_extensions=True
    ).execute()
    assert [r.file.name for r in results] == ["new1.mkv"]


def test_find_query_cache_enabled(monkeypatch, isolated_media_dir):
    # Build a pre-existing cache file and ensure FindQuery uses it instead of scanning.
    file_path = isolated_media_dir / "find1.mkv"
    file_path.write_text("x")
    other_path = isolated_media_dir / "other.txt"
    other_path.write_text("x")
    stat_info = [0] * 10
    cache_file = get_library_cache_file()
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "files": [
            (file_path.as_posix(), stat_info),
            (other_path.as_posix(), stat_info),
        ],
    }
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "wb") as f:
        pickle.dump(cache_data, f, protocol=PICKLE_PROTOCOL)
    monkeypatch.setattr(
        "mf.utils.scan.scan_search_paths",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("should not scan")),
    )
    # Use direct instantiation with explicit parameters (no need to mock get_config!)
    results = FindQuery(
        "*.mkv",
        auto_wildcards=False,
        cache_library=True,
        media_extensions=[".mkv"],
        match_extensions=True,
    ).execute()
    # Only the .mkv file should remain after filtering
    assert [r.file.name for r in results] == ["find1.mkv"]


def test_library_cache_json_removal_and_rebuild(isolated_media_dir, capsys):
    """Test automatic removal of old JSON cache and rebuild in pickle format."""
    # Create old JSON cache with dummy data
    create_files(isolated_media_dir, ["migrate_test.mkv"])
    json_cache = get_cache_dir() / "library.json"
    json_cache.parent.mkdir(parents=True, exist_ok=True)

    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "files": [("fake_path.mkv", [0] * 10)],
    }
    with open(json_cache, "w", encoding="utf-8") as f:
        json.dump(cache_data, f)

    # Verify JSON exists, pickle doesn't
    assert json_cache.exists()
    assert not get_library_cache_file().exists()

    # Load cache - should delete JSON and rebuild with pickle
    results = load_library_cache()
    captured = capsys.readouterr()

    # Verify old cache removed and new one built
    assert "Removed old JSON cache" in captured.out
    assert not json_cache.exists()  # JSON removed
    assert get_library_cache_file().exists()  # Pickle created
    # Should have real file from rebuild, not fake_path from old JSON
    assert any(r.file.name == "migrate_test.mkv" for r in results)

    # Verify pickle format is valid
    with open(get_library_cache_file(), "rb") as f:
        loaded_data = pickle.load(f)
    assert "timestamp" in loaded_data
    assert "files" in loaded_data


def test_split_by_search_path_basic(tmp_path):
    """Test basic splitting of files by search path."""
    # Create two search paths with files
    path1 = tmp_path / "media1"
    path2 = tmp_path / "media2"
    path1.mkdir()
    path2.mkdir()

    # Create files in each path
    file1 = path1 / "movie1.mp4"
    file2 = path1 / "movie2.mkv"
    file3 = path2 / "show1.mp4"
    file4 = path2 / "show2.mkv"

    for f in [file1, file2, file3, file4]:
        f.touch()

    # Create FileResults
    results = FileResults.from_paths([str(f) for f in [file1, file2, file3, file4]])

    # Split by search paths
    split = split_by_search_path(results, [path1, path2])

    # Verify split
    assert len(split[str(path1)]) == 2
    assert len(split[str(path2)]) == 2
    assert file1 in [r.get_path() for r in split[str(path1)]]
    assert file2 in [r.get_path() for r in split[str(path1)]]
    assert file3 in [r.get_path() for r in split[str(path2)]]
    assert file4 in [r.get_path() for r in split[str(path2)]]


def test_split_by_search_path_empty_results(tmp_path):
    """Test splitting empty FileResults."""
    path1 = tmp_path / "media1"
    path1.mkdir()

    results = FileResults()
    split = split_by_search_path(results, [path1])

    assert len(split[str(path1)]) == 0


def test_split_by_search_path_no_matches(tmp_path):
    """Test splitting when no files match any search path."""
    path1 = tmp_path / "media1"
    path2 = tmp_path / "other"
    path1.mkdir()
    path2.mkdir()

    # Create file outside search paths
    file1 = path2 / "movie.mp4"
    file1.touch()

    results = FileResults.from_paths([str(file1)])
    split = split_by_search_path(results, [path1])

    # File doesn't match any search path, so it shouldn't appear
    assert len(split[str(path1)]) == 0


def test_split_by_search_path_nested_paths(tmp_path):
    """Test that files are assigned to correct path when paths are nested."""
    # Note: This assumes search paths don't overlap (validated elsewhere)
    # But test the assignment logic works correctly
    path1 = tmp_path / "media"
    path2 = tmp_path / "other"
    path1.mkdir()
    path2.mkdir()

    file1 = path1 / "subdir" / "movie.mp4"
    file1.parent.mkdir()
    file1.touch()

    file2 = path2 / "show.mkv"
    file2.touch()

    results = FileResults.from_paths([str(file1), str(file2)])
    split = split_by_search_path(results, [path1, path2])

    assert len(split[str(path1)]) == 1
    assert len(split[str(path2)]) == 1
    assert file1 in [r.get_path() for r in split[str(path1)]]
    assert file2 in [r.get_path() for r in split[str(path2)]]
