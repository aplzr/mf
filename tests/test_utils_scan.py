import os
from pathlib import Path
from types import SimpleNamespace
from mf.utils.file import FileResult, FileResults
from mf.utils.scan import (
    FindQuery,
    NewQuery,
    _scan_with_progress_bar,
    scan_path_with_python,
    ProgressCounter,
    get_max_workers,
    _process_completed_futures,
    concatenate_fileresults,
    get_scan_strategy,
    FdScanStrategy,
    PythonScanStrategy,
    PythonSilentScanStrategy,
    PythonProgressScanStrategy,
)
from mf.utils.config import get_raw_config
from concurrent.futures import Future


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
        futures,  # type: ignore[arg-type]
        estimated_total=None,
        progress_counter=ProgressCounter(),
    )
    # FileResults returned should contain file-like entries; assert callable interface
    assert hasattr(res, "extend") and hasattr(res, "__iter__")


def test_find_query_filters_and_sorts(monkeypatch, tmp_path: Path):
    # Configure to not use cache and to match extensions
    monkeypatch.setattr(
        "mf.utils.scan.Configuration.from_config",
        lambda: SimpleNamespace(cache_library=False,
                        prefer_fd=False,
                        media_extensions=[".mp4", ".mkv"],
                        search_paths=[tmp_path.as_posix()],
                        auto_wildcards=True,
                        parallel_search=True)
    )
    # Create files
    (tmp_path / "b.mkv").write_text("x")
    (tmp_path / "a.mp4").write_text("x")
    (tmp_path / "c.txt").write_text("x")

    # Avoid validate_search_paths side effects by returning our tmp_path
    monkeypatch.setattr("mf.utils.scan.validate_search_paths", lambda paths: [tmp_path])
    # Use direct instantiation with explicit parameters (no need to mock get_config!)
    q = FindQuery(
        "*",
        auto_wildcards=False,
        cache_library=False,
        media_extensions=[".mp4", ".mkv"],
    )
    results = q.execute()
    names = [r.file.name for r in results]
    assert names == ["a.mp4", "b.mkv"]


def test_new_query_latest(monkeypatch, tmp_path: Path):
    # No cache; collect mtimes and sort by newest first
    # Create files with different mtimes
    f1 = tmp_path / "a.mp4"
    f2 = tmp_path / "b.mp4"
    f1.write_text("x")
    f2.write_text("x")

    # Ensure different mtimes
    os.utime(f1, (os.path.getatime(f1), os.path.getmtime(f1) - 10))

    monkeypatch.setattr("mf.utils.scan.validate_search_paths", lambda paths: [tmp_path])
    # Use direct instantiation with explicit parameters (no need to mock get_config!)
    q = NewQuery(2, cache_library=False, media_extensions=[".mp4"])
    results = q.execute()
    names = [r.file.name for r in results]
    assert names == ["b.mp4", "a.mp4"]

def test_find_query_auto_wildcards_setting():
    """Test FindQuery pattern setting respects auto_wildcards parameter."""
    # With auto_wildcards=True, pattern should be wrapped
    # Use direct instantiation with explicit parameters (no need to mock get_config!)
    query = FindQuery(
        "batman",
        auto_wildcards=True,
        cache_library=False,
        media_extensions=[".mp4"],
    )
    assert query.pattern == "*batman*"

    # With auto_wildcards=False, pattern should stay as-is
    query = FindQuery(
        "batman",
        auto_wildcards=False,
        cache_library=False,
        media_extensions=[".mp4"],
    )
    assert query.pattern == "batman"

def test_get_max_workers(monkeypatch, tmp_path: Path):
    assert get_max_workers([Path("path_1"), Path("path_2")], parallel_search=True) == 2
    assert get_max_workers([Path("path_1"), Path("path_2")], parallel_search=False) == 1

def test_process_completed_futures():
    completed_future_1 = Future()
    completed_future_2 = Future()
    pending_future = Future()

    result_1 = FileResult(Path("/path/to/file1.mp4"))
    result_2 = FileResult(Path("/path/to/file2.mp4"))
    completed_future_1.set_result(result_1)
    completed_future_2.set_result(result_2)

    results = FileResults()
    futures = [completed_future_1, pending_future, completed_future_2]
    remaining = _process_completed_futures(futures, results)

    assert len(results) == 2
    assert results[0] == result_1
    assert results[1] == result_2
    assert len(remaining) == 1
    assert remaining[0] is pending_future


def test_concatenate_fileresults():
    """Test concatenation of multiple FileResults objects."""
    # Create individual FileResults
    results1 = FileResults([
        FileResult(Path("/path/to/file1.mp4")),
        FileResult(Path("/path/to/file2.mp4")),
    ])
    results2 = FileResults([
        FileResult(Path("/path/to/file3.mkv")),
    ])
    results3 = FileResults()  # Empty

    # Concatenate
    concatenated = concatenate_fileresults([results1, results2, results3])

    assert len(concatenated) == 3
    assert concatenated[0].file == Path("/path/to/file1.mp4")
    assert concatenated[1].file == Path("/path/to/file2.mp4")
    assert concatenated[2].file == Path("/path/to/file3.mkv")


def test_concatenate_fileresults_empty():
    """Test concatenation with empty list."""
    concatenated = concatenate_fileresults([])
    assert len(concatenated) == 0
    assert isinstance(concatenated, FileResults)


def test_get_scan_strategy_prefer_fd():
    """Test get_scan_strategy returns FdScanStrategy when prefer_fd=True and cache_stat=False."""
    strategy = get_scan_strategy(cache_stat=False, prefer_fd=True, show_progress=False)
    assert isinstance(strategy, FdScanStrategy)


def test_get_scan_strategy_cache_stat():
    """Test get_scan_strategy returns PythonSilentScanStrategy when cache_stat=True."""
    strategy = get_scan_strategy(cache_stat=True, prefer_fd=True, show_progress=False)
    assert isinstance(strategy, PythonSilentScanStrategy)
    assert strategy.cache_stat is True


def test_get_scan_strategy_no_prefer_fd():
    """Test get_scan_strategy returns PythonProgressScanStrategy when prefer_fd=False."""
    strategy = get_scan_strategy(cache_stat=False, prefer_fd=False, show_progress=True)
    assert isinstance(strategy, PythonProgressScanStrategy)
    assert strategy.cache_stat is False


def test_python_scan_strategy_basic(tmp_path: Path):
    """Test PythonSilentScanStrategy.scan() with basic files."""
    # Create test files
    (tmp_path / "file1.mp4").write_text("x")
    (tmp_path / "file2.mkv").write_text("y")

    strategy = PythonSilentScanStrategy(cache_stat=False)
    results = strategy.scan([tmp_path], max_workers=1)

    assert len(results) == 2
    names = {r.file.name for r in results}
    assert names == {"file1.mp4", "file2.mkv"}


def test_python_scan_strategy_with_mtime(tmp_path: Path):
    """Test PythonSilentScanStrategy.scan() with cache_stat=True collects mtime."""
    (tmp_path / "file1.mp4").write_text("x")

    strategy = PythonSilentScanStrategy(cache_stat=True)
    results = strategy.scan([tmp_path], max_workers=1)

    assert len(results) == 1
    # When cache_stat=True, stat info should be collected
    assert results[0].stat is not None
    assert results[0].stat.st_mtime is not None


def test_python_scan_strategy_multiple_paths(tmp_path: Path):
    """Test PythonSilentScanStrategy.scan() with multiple search paths."""
    path1 = tmp_path / "dir1"
    path2 = tmp_path / "dir2"
    path1.mkdir()
    path2.mkdir()

    (path1 / "file1.mp4").write_text("x")
    (path2 / "file2.mkv").write_text("y")

    strategy = PythonSilentScanStrategy(cache_stat=False)
    results = strategy.scan([path1, path2], max_workers=2)

    assert len(results) == 2
    names = {r.file.name for r in results}
    assert names == {"file1.mp4", "file2.mkv"}


def test_fd_scan_strategy_basic(tmp_path: Path, monkeypatch):
    """Test FdScanStrategy.scan() successfully scans with fd."""
    # Create test files
    (tmp_path / "file1.mp4").write_text("x")
    (tmp_path / "file2.mkv").write_text("y")

    strategy = FdScanStrategy()

    # This will use the real fd binary if available, or fall back to Python
    results = strategy.scan([tmp_path], max_workers=1)

    assert len(results) == 2
    names = {r.file.name for r in results}
    assert names == {"file1.mp4", "file2.mkv"}


def test_fd_scan_strategy_fallback_to_python(tmp_path: Path, monkeypatch):
    """Test FdScanStrategy.scan() falls back to Python when fd fails."""
    # Create test files
    (tmp_path / "file1.mp4").write_text("x")

    # Mock scan_path_with_fd to raise an error
    def mock_scan_path_with_fd(path):
        raise FileNotFoundError("fd binary not found")

    monkeypatch.setattr("mf.utils.scan.scan_path_with_fd", mock_scan_path_with_fd)

    strategy = FdScanStrategy()
    results = strategy.scan([tmp_path], max_workers=1)

    # Should fall back to Python and still find the file
    assert len(results) == 1
    assert results[0].file.name == "file1.mp4"


def test_fd_scan_strategy_fallback_on_os_error(tmp_path: Path, monkeypatch, capsys):
    """Test FdScanStrategy.scan() falls back on OSError and prints warning."""
    (tmp_path / "file1.mp4").write_text("x")

    # Mock scan_path_with_fd to raise OSError
    def mock_scan_path_with_fd(path):
        raise OSError("Permission denied")

    monkeypatch.setattr("mf.utils.scan.scan_path_with_fd", mock_scan_path_with_fd)

    strategy = FdScanStrategy()
    results = strategy.scan([tmp_path], max_workers=1)

    # Should fall back and find the file
    assert len(results) == 1

    # Check warning was printed
    captured = capsys.readouterr()
    assert "fd scanner unavailable" in captured.out or "fd scanner unavailable" in captured.err
