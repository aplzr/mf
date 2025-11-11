import time
from pathlib import Path

import pytest

from mf.utils.config import read_config, write_config
from mf.utils.file import (
    FileResult,
    get_library_cache_file,
    is_cache_expired,
    rebuild_library_cache,
    sort_scan_results,
)
from mf.utils.normalizers import normalize_timedelta_str


@pytest.fixture()
def media_dir(tmp_path):
    d = tmp_path / "media"
    d.mkdir()
    cfg = read_config()
    cfg["search_paths"] = [d.as_posix()]
    cfg["cache_library"] = True
    cfg["library_cache_interval"] = "1s"  # very short expiry
    write_config(cfg)
    return d


def test_is_cache_expired_true(media_dir):
    # Build initial cache
    (media_dir / "one.mkv").write_text("x")
    rebuild_library_cache()
    cache_file = get_library_cache_file()
    assert cache_file.exists()
    # Sleep past interval
    time.sleep(1.2)
    assert is_cache_expired() is True


def test_sort_scan_results_mtime_branch(tmp_path):
    # Create FileResult entries with mtime set; ensure mtime sorting path taken
    f1 = FileResult(Path("/tmp/x1.mkv"), 1000.0)
    f2 = FileResult(Path("/tmp/x2.mkv"), 2000.0)
    results = sort_scan_results([f1, f2])
    assert [r.file.name for r in results] == ["x2.mkv", "x1.mkv"]


def test_normalize_timedelta_str_invalid(capsys):
    import click

    with pytest.raises(click.exceptions.Exit):
        normalize_timedelta_str("badformat")
    captured = capsys.readouterr()
    assert "Invalid format" in captured.out


def test_get_fd_binary_unsupported(monkeypatch):
    # Force unsupported platform combination
    monkeypatch.setattr("platform.system", lambda: "weirdOS")
    monkeypatch.setattr("platform.machine", lambda: "mysteryArch")
    from mf.utils.file import get_fd_binary

    with pytest.raises(RuntimeError):
        get_fd_binary()
