import os

import pytest

from mf.utils.play import get_vlc_command


@pytest.mark.skipif(
    os.name != "nt",
    reason="Test requires Windows (monkeypatching os.name causes Path instantiation errors on POSIX)"
)
def test_get_vlc_command_windows_paths():
    # Validate Windows VLC path logic
    cmd = get_vlc_command()
    assert cmd == "vlc" or cmd.endswith("vlc.exe")
