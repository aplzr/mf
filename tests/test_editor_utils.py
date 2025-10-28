import os
import subprocess

import pytest

from mf.utils import start_editor


def test_start_editor_visual(monkeypatch, tmp_path):
    test_file = tmp_path / "f.txt"
    test_file.write_text("x")
    monkeypatch.setenv("VISUAL", "myeditor")
    calls = []

    def fake_run(cmd):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    start_editor(test_file)
    assert calls and calls[0][0] == "myeditor"


def test_start_editor_windows_notepad(monkeypatch, tmp_path):
    # Simulate Windows environment
    monkeypatch.setattr(os, "name", "nt")
    test_file = tmp_path / "f.txt"
    test_file.write_text("x")
    # Ensure VISUAL/EDITOR unset
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)

    # Simulate that notepad++ not found but notepad found implicitly
    import shutil as _sh

    def fake_which(name):
        return None  # always not found so code uses notepad

    monkeypatch.setattr(_sh, "which", fake_which)

    calls = []

    def fake_run(cmd):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    start_editor(test_file)
    # Should have launched notepad
    assert calls and calls[0][0] == "notepad"


@pytest.mark.skipif(os.name == "nt", reason="POSIX-only test")
def test_start_editor_posix_no_editors(monkeypatch, tmp_path):
    test_file = tmp_path / "f.txt"
    test_file.write_text("x")
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(os, "name", "posix")

    import shutil as _sh

    def fake_which(name):  # Always return None to trigger 'no editor found'
        return None

    monkeypatch.setattr(_sh, "which", fake_which)

    # Capture console output
    from mf.utils import console

    outputs = []

    def fake_print(*args, **kwargs):
        # Rich console.print: just capture text segments
        outputs.append(" ".join(str(a) for a in args))

    monkeypatch.setattr(console, "print", fake_print)

    # Replace run to ensure it's not called
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Should not run")),
    )

    start_editor(test_file)
    assert any("No editor found" in o for o in outputs)
