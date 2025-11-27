import time

import pytest

from mf.utils.cache import is_cache_expired, rebuild_library_cache
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
