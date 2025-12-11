import time

import pytest

from mf.utils.cache import is_cache_expired, load_library_cache, rebuild_library_cache
from mf.utils.config import read_config, write_config
from mf.utils.file import (
    get_library_cache_file,
)


@pytest.fixture()
def media_dir(tmp_path):
    d = tmp_path / "media"
    d.mkdir()
    cfg = read_config()
    cfg["search_paths"] = [d.as_posix()]
    cfg["cache_library"] = True
    cfg["library_cache_interval"] = 1  # very short expiry
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


def test_get_fd_binary_unsupported(monkeypatch):
    # Force unsupported platform combination
    monkeypatch.setattr("platform.system", lambda: "weirdOS")
    monkeypatch.setattr("platform.machine", lambda: "mysteryArch")
    from mf.utils.file import get_fd_binary

    with pytest.raises(RuntimeError):
        get_fd_binary()


def test_load_library_cache_with_caching_disabled(tmp_path):
    """Regression test: load_library_cache should rebuild cache even when
    cache_library=False, as long as cache file doesn't exist.

    This test would have caught the bug where is_cache_expired() returned False
    when cache_library=False, causing load_library_cache() to try opening a
    non-existent cache file and crash with FileNotFoundError.
    """
    # Setup: disable caching, create search path with a file
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "test.mkv").write_text("x")

    cfg = read_config()
    cfg["search_paths"] = [media_dir.as_posix()]
    cfg["cache_library"] = False  # Key: caching disabled
    write_config(cfg)

    # Ensure cache doesn't exist
    cache_file = get_library_cache_file()
    if cache_file.exists():
        cache_file.unlink()

    # This should rebuild the cache instead of crashing
    # (Bug: would crash with FileNotFoundError)
    results = load_library_cache()

    # Verify cache was built and contains the file
    assert cache_file.exists()
    assert len(results) == 1
    assert results[0].file.name == "test.mkv"
