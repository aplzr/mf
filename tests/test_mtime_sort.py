import os
import time
from pathlib import Path

from mf.utils import add_search_path, find_media_files, read_config, write_config


def test_mtime_sort(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    f1 = media_dir / "a_old.mp4"
    f2 = media_dir / "b_new.mp4"
    f1.write_text("old")
    time.sleep(0.05)
    f2.write_text("new")
    cfg = add_search_path(cfg, str(media_dir))
    write_config(cfg)
    results = find_media_files("*", sort_by_mtime=True, prefer_fd=False)
    names = [p.name for _, p in results[:2]]
    assert names[0] == "b_new.mp4" and names[1] == "a_old.mp4"
