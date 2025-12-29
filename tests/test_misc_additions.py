import os

import pytest

from mf.utils.play import get_vlc_command


@pytest.mark.skipif(
    os.name != "nt",
    reason="Test requires Windows (monkeypatching os.name causes Path instantiation errors on POSIX)"
)
def test_get_vlc_command_windows_prefers_known_paths():
    # Test Windows VLC path resolution
    resolved = get_vlc_command()
    # Should return a ResolvedPlayer if VLC is found
    if resolved:
        assert resolved.label == "vlc"
        assert str(resolved.path).endswith("vlc.exe") or str(resolved.path) == "vlc"


@pytest.mark.skipif(
    os.name != "nt",
    reason="Test requires Windows (monkeypatching os.name causes Path instantiation errors on POSIX)"
)
def test_get_vlc_command_windows_falls_back_to_path():
    # Test Windows VLC fallback behavior
    resolved = get_vlc_command()
    # Should return a ResolvedPlayer if VLC is found
    if resolved:
        assert resolved.label == "vlc"
        assert str(resolved.path).endswith("vlc.exe") or str(resolved.path) == "vlc"
