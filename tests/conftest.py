from __future__ import annotations

import os
import shutil
import tempfile
import pathlib
from pathlib import Path

import pytest

from mf.utils.config import get_config_file, read_config, write_config

# --- Defensive guard against global Path class drift on CI ---
# Some older Python/pytest combos can end up with pathlib.Path bound to
# WindowsPath on POSIX if os.name is globally mutated by a test or plugin.
# Ensure pathlib.Path matches the platform to avoid pytest INTERNALERRORs.
if os.name != "nt":
    try:
        _p = pathlib.Path("")
    except NotImplementedError:
        pathlib.Path = pathlib.PosixPath  # type: ignore[attr-defined]
elif os.name == "nt":
    try:
        _p = pathlib.Path("")
    except NotImplementedError:
        pathlib.Path = pathlib.WindowsPath  # type: ignore[attr-defined]

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
