import os
import subprocess

import pytest
import typer

from mf.utils import (
    add_search_path,
    find_media_files,
    normalize_bool_str,
    normalize_media_extension,
    read_config,
    remove_search_path,
    start_editor,
    write_config,
)


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific branch")
def test_editor_windows_notepadpp(monkeypatch, tmp_path):
    # Ensure VISUAL/EDITOR unset so Windows branch executes
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    # Force Windows behavior
    monkeypatch.setattr(os, "name", "nt")
    # Provide notepad++
    import shutil as _sh

    def fake_which(name):
        return (
            "C:/Program Files/Notepad++/notepad++.exe" if name == "notepad++" else None
        )

    monkeypatch.setattr(_sh, "which", fake_which)
    calls = []

    def fake_run(cmd):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    file_path = tmp_path / "a.txt"
    file_path.write_text("x")
    start_editor(file_path)
    assert calls and calls[0][0].lower().startswith("notepad++")


@pytest.mark.skipif(os.name == "nt", reason="POSIX-only branch")
def test_editor_posix_editor_found(monkeypatch, tmp_path):
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(os, "name", "posix")
    import shutil as _sh

    def fake_which(name):
        return "/usr/bin/vim" if name == "vim" else None

    monkeypatch.setattr(_sh, "which", fake_which)
    calls = []

    def fake_run(cmd):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    file_path = tmp_path / "b.txt"
    file_path.write_text("x")
    start_editor(file_path)
    assert calls and calls[0][0] == "vim"


def test_add_search_path_duplicate(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    # Add path first
    cfg = add_search_path(cfg, str(tmp_path))
    write_config(cfg)
    # Add again to exercise duplicate warning branch
    cfg = add_search_path(cfg, str(tmp_path))
    write_config(cfg)


def test_remove_search_path_missing(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    with pytest.raises(typer.Exit):
        remove_search_path(cfg, str(tmp_path / "does_not_exist"))


def test_normalize_media_extension_empty(monkeypatch):
    import click

    with pytest.raises(ValueError):
        normalize_media_extension("")
    with pytest.raises(click.exceptions.Exit):
        normalize_media_extension("   ")


def test_normalize_bool_str_invalid(monkeypatch):
    import click

    with pytest.raises(click.exceptions.Exit):
        normalize_bool_str("maybe")


def test_scan_fd_global_fallback(monkeypatch, tmp_path):
    # Setup config with media file
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "movie.mp4").write_text("x")
    cfg = read_config()
    cfg = add_search_path(cfg, str(media_dir))
    write_config(cfg)

    # Force get_fd_binary to raise OSError so full fallback triggers
    import mf.utils.scan_utils as su

    def raise_os_error():
        raise OSError("boom")

    monkeypatch.setattr(su, "get_fd_binary", raise_os_error)
    results = find_media_files("movie", prefer_fd=True, sort_by_mtime=False)
    assert any(p.name == "movie.mp4" for _, p in results)
