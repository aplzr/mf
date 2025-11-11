import platform

import pytest

from mf.utils.file_utils import get_fd_binary


def test_get_fd_binary_linux_x86_64(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    path = get_fd_binary()
    assert path.name.endswith("linux-gnu")


def test_get_fd_binary_darwin_arm64(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    path = get_fd_binary()
    assert "aarch64" in path.name or "arm" in path.name


def test_get_fd_binary_unsupported(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Solaris")
    monkeypatch.setattr(platform, "machine", lambda: "sparc")
    with pytest.raises(RuntimeError):
        get_fd_binary()
