import os
import subprocess
from pathlib import Path

import pytest

from mf._app_mf import play
from mf.utils import add_search_path, read_config, save_search_results, write_config


class DummyPopen:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def test_play_invokes_vlc(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    movie = media_dir / "sample.mp4"
    movie.write_text("x")
    cfg = add_search_path(cfg, str(media_dir))
    write_config(cfg)
    # Cache a search result so play(index) works
    save_search_results("*", [(1, movie)])

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: DummyPopen(*a, **k))
    # Force windows path expectation independent of platform by monkeypatching os.name if needed
    # Not strictly necessary; simulate generic behavior
    play(index=1)
