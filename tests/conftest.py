from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest

from mf.utils.config import get_raw_config, write_config
from mf.utils.file import get_config_file

# --- Fixtures for test isolation ---


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    """Provide an isolated config & cache directory per test.

    Sets XDG/LOCALAPPDATA env vars to a fresh temporary directory so tests never
    touch the user's real configuration or cache files. Automatically creates
    a fresh default config on first access.
    """
    # Clear global config cache before each test
    import mf.utils.config
    mf.utils.config._config = None

    # Mock console.is_terminal to return True by default (rich output mode)
    # Tests can override this to test plain mode explicitly
    from mf.utils.search import console
    with patch.object(type(console), 'is_terminal', new_callable=PropertyMock, return_value=True):
        tmp_root = Path(tempfile.mkdtemp(prefix="mf-test-"))
        if os.name == "nt":
            monkeypatch.setenv("LOCALAPPDATA", str(tmp_root))
        else:
            monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_root))
            monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_root))
        # Force re-load to create default config in isolated dir
        cfg = get_raw_config()
        write_config(cfg)
        # No direct monkeypatch of get_cache_file: environment vars ensure isolation.
        # Tests that need a different cache location can override env vars themselves.
        yield tmp_root
        shutil.rmtree(tmp_root, ignore_errors=True)


@pytest.fixture
def isolated_cache(monkeypatch, isolated_config):
    """Return path to the per-test isolated cache file (ensures fresh state)."""
    cache_path = Path(isolated_config) / "mf" / "last_search.json"
    if cache_path.exists():
        cache_path.unlink()
    return cache_path


@pytest.fixture
def fresh_config():
    """Return a mutable copy of the current (isolated) config TOML document."""
    return get_raw_config()


@pytest.fixture
def config_path() -> Path:
    """Return path to the isolated test config file."""
    return get_config_file()
