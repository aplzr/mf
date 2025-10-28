import os

from mf.utils import add_search_path, find_media_files, read_config, write_config


def test_find_media_files_python_scanner(tmp_path, monkeypatch):
    # Ensure config points to tmp path
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()

    media_dir = tmp_path / "media"
    media_dir.mkdir()
    # Create sample files
    (media_dir / "MovieOne.mp4").write_text("test")
    (media_dir / "Another.mkv").write_text("test")
    (media_dir / "note.txt").write_text("ignore")

    # Add path to config
    cfg = add_search_path(cfg, str(media_dir))
    write_config(cfg)

    # pattern is wildcarded automatically; we search for 'movie'
    results = find_media_files("movie", sort_by_mtime=False, prefer_fd=False)
    names = [p.name.lower() for _, p in results]
    # Expect normalized pattern wrapping, filename matches '*movie*'
    assert any("movieone" in name for name in names)


def test_find_newest_media_files(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    # Create files with different mtimes
    f1 = media_dir / "a1.mp4"
    f1.write_text("a1")
    f2 = media_dir / "a2.mp4"
    f2.write_text("a2")
    # Artificially modify mtime of first file to be older
    os.utime(f1, (f1.stat().st_atime, f1.stat().st_mtime - 100))

    cfg = add_search_path(cfg, str(media_dir))
    write_config(cfg)

    results = find_media_files("*", sort_by_mtime=True, prefer_fd=False)
    # Expect first result to be the newer file
    assert results[0][1].name == "a2.mp4"
