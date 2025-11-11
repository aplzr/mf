import shutil
import subprocess

from mf.utils.editor_utils import start_editor


def test_editor_prefers_visual(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("VISUAL", "myvisual")

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return 0

    monkeypatch.setattr(subprocess, "run", fake_run)
    start_editor(tmp_path / "file.txt")  # uses fake_run
    assert calls and calls[0][0] == "myvisual"


def test_editor_prefers_editor_env(monkeypatch, tmp_path):
    calls = []
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.setenv("EDITOR", "nanoish")

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return 0

    monkeypatch.setattr(subprocess, "run", fake_run)
    start_editor(tmp_path / "file.txt")  # uses fake_run
    assert calls and calls[0][0] == "nanoish"


def test_editor_windows_notepadpp(monkeypatch, tmp_path):
    calls = []
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)

    def fake_which(cmd):
        if cmd == "notepad++":
            return "C:/Program Files/Notepad++/notepad++.exe"
        return None

    monkeypatch.setattr(shutil, "which", fake_which)

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return 0

    monkeypatch.setattr(subprocess, "run", fake_run)
    start_editor(tmp_path / "file.txt")  # uses fake_run
    assert calls and calls[0][0] == "notepad++"


def test_editor_windows_notepad_fallback(monkeypatch, tmp_path):
    calls = []
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)

    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return 0

    monkeypatch.setattr(subprocess, "run", fake_run)
    start_editor(tmp_path / "file.txt")  # uses fake_run
    assert calls and calls[0][0] == "notepad"


def test_editor_posix_no_editor(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)

    import mf.constants as const

    # Ensure POSIX fallback editors list but simulate that none exist
    monkeypatch.setattr(const, "FALLBACK_EDITORS_POSIX", ["ed1", "ed2"])  # ensure list
    import shutil as _sh

    monkeypatch.setattr(_sh, "which", lambda cmd: None)
    # Force POSIX fallback list but none resolve. On Windows this code path won't
    # produce the POSIX "No editor found" message; assert accordingly.
    # Monkeypatch subprocess.run defensively even for no-editor branch
    import subprocess as _sp

    monkeypatch.setattr(_sp, "run", lambda *a, **k: None)
    start_editor(tmp_path / "file.txt")
    out = capsys.readouterr().out
    import os

    if os.name == "nt":  # Windows path prints guidance differently or opens notepad
        # Should not contain POSIX message
        assert "No editor found" not in out
    else:
        assert "No editor found" in out
