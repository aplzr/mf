from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from mf.utils.config import get_config_file, read_config, write_config

# --- Fixtures for test isolation ---


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    """Provide an isolated config & cache directory per test.

    Sets XDG/LOCALAPPDATA env vars to a fresh temporary directory so tests never
    touch the user's real configuration or cache files. Automatically creates
    a fresh default config on first access.
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="mf-test-"))
    if os.name == "nt":
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_root))
    else:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_root))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_root))
    # Force re-load to create default config in isolated dir
    cfg = read_config()
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
    return read_config()


@pytest.fixture
def config_path() -> Path:
    """Return path to the isolated test config file."""
    return get_config_file()


# --- Drift detector: fail fast if pathlib.Path class changes mid-session ---
import pathlib
import sys

def _expected_path_class():
    """Get the expected Path class for the current OS (called each time to avoid pickling issues)."""
    return pathlib.WindowsPath if os.name == "nt" else pathlib.PosixPath

def _current_path_class():
    return type(pathlib.Path(""))

def pytest_sessionstart(session):
    cls = _current_path_class()
    expected = _expected_path_class()
    if cls is not expected:
        raise RuntimeError(f"Path class drift at session start: {cls} != {expected}")

def pytest_runtest_setup(item):
    cls = _current_path_class()
    expected = _expected_path_class()
    if cls is not expected:
        raise RuntimeError(f"Path class drift before test {item.nodeid}: {cls} != {expected}")

def pytest_runtest_teardown(item):
    cls = _current_path_class()
    expected = _expected_path_class()
    if cls is not expected:
        raise RuntimeError(f"Path class drift after test {item.nodeid}: {cls} != {expected}")
