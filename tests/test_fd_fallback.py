import os
import subprocess

from mf.utils import add_search_path, find_media_files, read_config, write_config


def test_fd_fallback_missing_binary(tmp_path, monkeypatch):
    # Force config
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "Film.mp4").write_text("x")
    cfg = read_config()
    cfg = add_search_path(cfg, str(media_dir))
    write_config(cfg)

    # Monkeypatch get_fd_binary to raise FileNotFoundError
    import mf.utils.scan_utils as u

    def raise_fn():
        raise FileNotFoundError

    monkeypatch.setattr(u, "get_fd_binary", raise_fn)

    results = find_media_files("film", prefer_fd=True, sort_by_mtime=False)
    assert any(p.name == "Film.mp4" for _, p in results)


def test_fd_fallback_subprocess_error(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "Clip.mp4").write_text("x")
    cfg = read_config()
    cfg = add_search_path(cfg, str(media_dir))
    write_config(cfg)

    # Force get_fd_binary to return something but make subprocess run raise
    import mf.utils.scan_utils as u

    monkeypatch.setattr(u, "get_fd_binary", lambda: media_dir / "fd")

    def raise_run(*a, **k):
        raise subprocess.CalledProcessError(1, "fd")

    monkeypatch.setattr(subprocess, "run", raise_run)

    results = find_media_files("clip", prefer_fd=True, sort_by_mtime=False)
    assert any(p.name == "Clip.mp4" for _, p in results)
