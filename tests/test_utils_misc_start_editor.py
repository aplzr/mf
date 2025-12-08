from types import SimpleNamespace

import mf.utils.misc as misc_mod


def test_start_editor_windows_fallback(monkeypatch, tmp_path):
    # Create a dummy file to 'edit'
    f = tmp_path / "dummy.txt"
    f.write_text("x")

    # Stub os with Windows and empty env
    monkeypatch.setattr(misc_mod, "os", SimpleNamespace(name="nt", environ={}))

    # Stub shutil.which to simulate notepad exists, others missing
    def which(name: str):
        return "C:/Windows/System32/notepad.exe" if name == "notepad" else None

    monkeypatch.setattr(misc_mod, "shutil", SimpleNamespace(which=which))

    captured = {}

    def fake_run(cmd):
        captured["cmd"] = cmd
        return 0

    monkeypatch.setattr(misc_mod, "subprocess", SimpleNamespace(run=fake_run))

    misc_mod.start_editor(f)

    assert (
        captured["cmd"][0].lower().endswith("notepad.exe")
        or captured["cmd"][0] == "notepad"
    )
    assert str(captured["cmd"][1]) == str(f)
