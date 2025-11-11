import os
import subprocess

from mf.utils import scan_path_with_python, start_editor


def test_start_editor_uses_visual(monkeypatch, tmp_path):
    file_ = tmp_path / "config.toml"
    file_.write_text("x")
    monkeypatch.setenv("VISUAL", "echo")
    # Replace subprocess.run to capture call
    calls = {}

    def fake_run(cmd):
        calls["cmd"] = cmd

    monkeypatch.setattr(subprocess, "run", fake_run)
    start_editor(file_)
    # On Windows subprocess arg may retain backslashes; normalize both
    played = calls["cmd"][-1].replace("\\", "/")
    assert "cmd" in calls and file_.as_posix() in played


def test_scan_permission_error(monkeypatch, tmp_path):
    # Create directory and remove permissions
    # (simulate by raising PermissionError in scandir)
    target = tmp_path / "restricted"
    target.mkdir()

    def fake_scandir(path):
        raise PermissionError

    monkeypatch.setattr(os, "scandir", fake_scandir)
    res = scan_path_with_python(target, include_mtime=False)
    assert res == []


def test_scan_include_mtime(monkeypatch, tmp_path):
    d = tmp_path / "media"
    d.mkdir()
    f = d / "vid.mp4"
    f.write_text("x")
    res = scan_path_with_python(d, include_mtime=True)
    assert res and hasattr(res[0], "mtime") and res[0].mtime is not None
