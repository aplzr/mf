import shutil
import sys
from types import SimpleNamespace

import mf.utils.misc as misc_mod
from mf.utils.misc import start_editor
import pytest


def test_start_editor_prefers_visual(monkeypatch, tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("x")
    calls = []

    monkeypatch.setenv("VISUAL", "myeditor")
    # Patch subprocess.run locally within module under test to avoid global effects
    monkeypatch.setattr(misc_mod, "subprocess", SimpleNamespace(run=lambda args: calls.append(tuple(args))))

    start_editor(target)
    assert calls and calls[0][0] == "myeditor"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific editor selection")
def test_start_editor_windows_notepadpp(monkeypatch, tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("x")
    calls = []

    # Inject a stub os with desired platform name locally into module under test
    monkeypatch.setattr(misc_mod, "os", SimpleNamespace(name="nt", environ={}))
    monkeypatch.setattr(misc_mod, "shutil", SimpleNamespace(which=lambda exe: exe == "notepad++"))
    monkeypatch.setattr(misc_mod, "subprocess", SimpleNamespace(run=lambda args: calls.append(tuple(args))))

    start_editor(target)
    assert calls and calls[0][0] == "notepad++"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific editor selection")
def test_start_editor_windows_notepad(monkeypatch, tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("x")
    calls = []

    monkeypatch.setattr(misc_mod, "os", SimpleNamespace(name="nt", environ={}))
    monkeypatch.setattr(misc_mod, "shutil", SimpleNamespace(which=lambda exe: None))
    monkeypatch.setattr(misc_mod, "subprocess", SimpleNamespace(run=lambda args: calls.append(tuple(args))))

    start_editor(target)
    assert calls and calls[0][0] == "notepad"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-specific editor selection")
def test_start_editor_posix_fallback(monkeypatch, tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("x")
    calls = []

    monkeypatch.setattr(misc_mod, "os", SimpleNamespace(name="posix", environ={}))
    # First two missing, third present
    present = {"vim"}
    monkeypatch.setattr(misc_mod, "shutil", SimpleNamespace(which=lambda exe: exe if exe in present else None))
    monkeypatch.setattr(misc_mod, "subprocess", SimpleNamespace(run=lambda args: calls.append(tuple(args))))

    start_editor(target)
    assert calls and calls[0][0] == "vim"
