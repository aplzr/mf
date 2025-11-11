import os
import subprocess

import pytest

from mf.utils.editor_utils import start_editor
from mf.utils.normalizers import normalize_bool_str, normalize_media_extension


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific branch")
def test_editor_windows_notepadpp(monkeypatch, tmp_path):
    # Ensure VISUAL/EDITOR unset so Windows branch executes
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    # Force Windows behavior
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
