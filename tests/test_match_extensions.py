import os

from mf.utils import add_search_path, find_media_files, read_config, write_config


def test_match_extensions_disabled_includes_non_media(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "video.mp4").write_text("v")
    (media_dir / "document.txt").write_text("d")
    cfg = add_search_path(cfg, str(media_dir))
    # Disable extension matching
    cfg["match_extensions"] = False
    write_config(cfg)
    results = find_media_files("*", prefer_fd=False)
    names = [p.name for _, p in results]
    assert "document.txt" in names
