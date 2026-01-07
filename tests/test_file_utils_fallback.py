import os
import subprocess
import time
from pathlib import Path

from mf.utils.config import get_raw_config, write_config
from mf.utils.scan import scan_search_paths


def _set_search_paths(tmp_path: Path, paths: list[Path], prefer_fd: bool = True):
    cfg = get_raw_config()
    cfg["search_paths"] = [p.as_posix() for p in paths]
    cfg["prefer_fd"] = prefer_fd
    write_config(cfg)


def test_fd_fallback_calledprocesserror(monkeypatch, tmp_path):
    """When fd raises CalledProcessError, fallback to python scanner is used."""
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    f = media_dir / "a.mp4"
    f.write_text("x")
    _set_search_paths(tmp_path, [media_dir], prefer_fd=True)

    # Monkeypatch scan_path_with_fd to raise CalledProcessError
    import mf.utils.scan as scan

    def raise_cpe(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["fd"])  # noqa: F841

    monkeypatch.setattr(scan, "scan_path_with_fd", raise_cpe)
    results = scan_search_paths()
    assert any(res.file.name == "a.mp4" for res in results)


def test_fd_fallback_file_not_found(monkeypatch, tmp_path):
    """FileNotFoundError from fd path triggers fallback."""
    media_dir = tmp_path / "media2"
    media_dir.mkdir()
    f = media_dir / "b.mp4"
    f.write_text("x")
    _set_search_paths(tmp_path, [media_dir], prefer_fd=True)
    import mf.utils.scan as scan

    def raise_fnf(*args, **kwargs):
        raise FileNotFoundError("fd")

    monkeypatch.setattr(scan, "scan_path_with_fd", raise_fnf)
    results = scan_search_paths()
    assert any(res.file.name == "b.mp4" for res in results)


def test_mtime_sorting(tmp_path):
    """Results with mtime (with_mtime=True) are sorted newest first."""
    media_dir = tmp_path / "media3"
    media_dir.mkdir()
    first = media_dir / "first.mp4"
    second = media_dir / "second.mp4"
    first.write_text("x")
    time.sleep(0.01)  # ensure distinct mtime
    second.write_text("y")
    _set_search_paths(tmp_path, [media_dir], prefer_fd=False)
    # Request mtimes so results contain mtime and `sort_scan_results` will
    # order by mtime descending.
    results = scan_search_paths(cache_stat=True)
    results.sort(by_mtime=True)
    names = [r.file.name for r in results]
    assert names[:2] == ["second.mp4", "first.mp4"]


def test_permission_error_in_python_scanner(monkeypatch, tmp_path):
    """PermissionError inside python recursion should skip directory gracefully."""
    media_dir = tmp_path / "media4"
    protected = media_dir / "protected"
    media_dir.mkdir()
    protected.mkdir()
    good = media_dir / "ok.mp4"
    good.write_text("x")
    _set_search_paths(tmp_path, [media_dir], prefer_fd=False)

    original_scandir = os.scandir

    def fake_scandir(path):
        # Only perform Path comparison for path-like inputs; some environments
        # may invoke os.scandir with non-path integers during teardown or plugin
        # activity. Guard to prevent TypeError when constructing Path(int).
        if isinstance(path, (str | bytes | os.PathLike)) and Path(path) == protected:
            raise PermissionError("denied")
        return original_scandir(path)

    monkeypatch.setattr(os, "scandir", fake_scandir)
    results = scan_search_paths()
    assert any(r.file.name == "ok.mp4" for r in results)
