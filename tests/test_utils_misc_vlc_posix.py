from types import SimpleNamespace

import mf.utils.misc as misc_mod


def test_get_vlc_command_posix(monkeypatch):
    # Force POSIX branch
    monkeypatch.setattr(misc_mod, "os", SimpleNamespace(name="posix"))
    assert misc_mod.get_vlc_command() == "vlc"
