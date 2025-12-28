import os
from types import SimpleNamespace

import mf.utils.play as play_mod
import mf.utils.play


def test_get_vlc_command_posix(monkeypatch):
    # Force POSIX branch - need to include environ since get_vlc_command accesses it
    monkeypatch.setattr(
        play_mod, "os", SimpleNamespace(name="posix", environ=os.environ)
    )
    assert mf.utils.play.get_vlc_command() == "vlc"
