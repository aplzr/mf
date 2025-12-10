import os
from pathlib import Path

from mf.utils.file import FileResult
from mf.utils.scan import (
    FindQuery,
    NewQuery,
    _scan_with_progress_bar,
    scan_path_with_python,
    ProgressCounter,
    get_max_workers

)
from mf.utils.config import read_config


def test_scan_path_with_python_basic(tmp_path: Path):
    d = tmp_path / "root"
    d.mkdir()
    (d / "a.txt").write_text("x")
    (d / "b.mp4").write_text("y")

    results = scan_path_with_python(d, with_mtime=False)
    paths = {r.file.name for r in results}
    assert paths == {"a.txt", "b.mp4"}


def test_scan_path_with_python_permission_error(monkeypatch, tmp_path: Path, capsys):
    d = tmp_path / "root"
    d.mkdir()

    # Simulate PermissionError in scandir
    class FakeEntries:
        def __enter__(self):
            raise PermissionError("no access")

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_scandir(path):
        return FakeEntries()

    # Patch the helper used within scan_path_with_python by replacing os module locally
    import mf.utils.scan as scan_mod
    class _Os:
        @staticmethod
        def scandir(path):
            return fake_scandir(path)
    monkeypatch.setattr(scan_mod, "os", _Os())
    results = scan_path_with_python(d, with_mtime=False)
    assert len(results) == 0


def test__scan_with_progress_bar_no_estimate(tmp_path: Path):
    # Simulate completed futures list
    class DummyFuture:
        def __init__(self, paths):
            self._paths = paths

        def done(self):
            return True

        def result(self):
            frs = [FileResult.from_string(p) for p in self._paths]
            return type("FRs", (), {"extend": None, "__iter__": lambda s: iter(frs)})()

    futures = [DummyFuture([str(tmp_path / "a"), str(tmp_path / "b")])]
    import threading

    lock = threading.Lock()
    res = _scan_with_progress_bar(
        futures,
        estimated_total=None,
        progress_counter=ProgressCounter(),
    )
    # FileResults returned should contain file-like entries; assert callable interface
    assert hasattr(res, "extend") and hasattr(res, "__iter__")


def test_find_query_filters_and_sorts(monkeypatch, tmp_path: Path):
    # Configure to not use cache and to match extensions
    monkeypatch.setattr(
        "mf.utils.scan.read_config",
        lambda: {
            "cache_library": False,
            "prefer_fd": False,
            "media_extensions": [".mp4", ".mkv"],
            "match_extensions": True,
            "search_paths": [tmp_path.as_posix()],
            "auto_wildcards": True,
            "parallel_search": True,
        },
    )
    # Create files
    (tmp_path / "b.mkv").write_text("x")
    (tmp_path / "a.mp4").write_text("x")
    (tmp_path / "c.txt").write_text("x")

    # Avoid validate_search_paths side effects by returning our tmp_path
    monkeypatch.setattr("mf.utils.scan.validate_search_paths", lambda: [tmp_path])
    q = FindQuery("*")
    results = q.execute()
    names = [r.file.name for r in results]
    assert names == ["a.mp4", "b.mkv"]


def test_new_query_latest(monkeypatch, tmp_path: Path):
    # No cache; collect mtimes and sort by newest first
    monkeypatch.setattr(
        "mf.utils.scan.read_config",
        lambda: {
            "cache_library": False,
            "prefer_fd": False,
            "media_extensions": [".mp4"],
            "match_extensions": True,
            "search_paths": [tmp_path.as_posix()],
            "parallel_search": True,
        },
    )

    # Create files with different mtimes
    f1 = tmp_path / "a.mp4"
    f2 = tmp_path / "b.mp4"
    f1.write_text("x")
    f2.write_text("x")

    # Ensure different mtimes
    os.utime(f1, (os.path.getatime(f1), os.path.getmtime(f1) - 10))

    monkeypatch.setattr("mf.utils.scan.validate_search_paths", lambda: [tmp_path])
    q = NewQuery(2)
    results = q.execute()
    names = [r.file.name for r in results]
    assert names == ["b.mp4", "a.mp4"]

def test_find_query_auto_wildcards_setting(monkeypatch):
    """Test FindQuery pattern setting respects auto_wildcards config."""
    # With auto_wildcards=True, pattern should be wrapped
    monkeypatch.setattr("mf.utils.scan.read_config", lambda: {
        "auto_wildcards": True,
        "cache_library": False,
        "prefer_fd": False,
        "media_extensions": [".mp4"],
        "match_extensions": True,
    })
    query = FindQuery("batman")
    assert query.pattern == "*batman*"

    # With auto_wildcards=False, pattern should stay as-is
    monkeypatch.setattr("mf.utils.scan.read_config", lambda: {
        "auto_wildcards": False,
        "cache_library": False,
        "prefer_fd": False,
        "media_extensions": [".mp4"],
        "match_extensions": True,
    })
    query = FindQuery("batman")
    assert query.pattern == "batman"

def test_get_max_workers(monkeypatch, tmp_path: Path):
    assert get_max_workers(["path_1", "path_2"], parallel_search=True) == 2
    assert get_max_workers(["path_1", "path_2"], parallel_search=False) == 1
