import os

from mf.utils import (
    add_media_extension,
    get_config_file,
    read_config,
    remove_media_extension,
)


def test_add_remove_media_extension(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    cfg = add_media_extension(cfg, "MP4")
    assert ".mp4" in cfg["media_extensions"]
    cfg = remove_media_extension(cfg, "mp4")
    assert ".mp4" not in cfg["media_extensions"]
