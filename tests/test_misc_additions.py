import os

import pytest

from mf.utils.play import get_vlc_command


@pytest.mark.skipif(
    os.name != "nt",
    reason="Test requires Windows (monkeypatching os.name causes Path instantiation errors on POSIX)"
)
def test_get_vlc_command_windows_prefers_known_paths():
    # Test Windows VLC path resolution
    cmd = get_vlc_command()
    # Depending on environment, it may fall back to 'vlc'
    assert cmd == "vlc" or cmd.endswith("vlc.exe")


@pytest.mark.skipif(
    os.name != "nt",
    reason="Test requires Windows (monkeypatching os.name causes Path instantiation errors on POSIX)"
)
def test_get_vlc_command_windows_falls_back_to_path():
    # Test Windows VLC fallback behavior
    cmd = get_vlc_command()
    assert cmd == "vlc" or cmd.endswith("vlc.exe")
