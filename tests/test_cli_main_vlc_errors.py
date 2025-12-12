import os

from typer.testing import CliRunner

from mf.cli_main import app_mf

runner = CliRunner()


def _dummy_file_result(path: str):
    class DummyFile:
        def __init__(self, p):
            self._path = p
            self.name = os.path.basename(p)
            self.parent = os.path.dirname(p)

        def __str__(self):
            return self._path

    class DummyResult:
        def __init__(self, p):
            self.file = DummyFile(p)

    return DummyResult(path)


def test_play_vlc_not_found(monkeypatch):
    monkeypatch.setattr(
        "mf.cli_main.get_next", lambda: _dummy_file_result("/tmp/a.mp4")
    )
    monkeypatch.setattr("mf.cli_main.get_vlc_command", lambda: "vlc")
    monkeypatch.setattr(
        "mf.cli_main.get_config", lambda: {"fullscreen_playback": False}
    )

    import subprocess

    def raise_fnf(*a, **k):
        raise FileNotFoundError("vlc missing")

    monkeypatch.setattr(subprocess, "Popen", raise_fnf)

    result = runner.invoke(app_mf, ["play", "next"])
    assert result.exit_code != 0


def test_play_vlc_generic_error(monkeypatch):
    monkeypatch.setattr(
        "mf.cli_main.get_next", lambda: _dummy_file_result("/tmp/a.mp4")
    )
    monkeypatch.setattr("mf.cli_main.get_vlc_command", lambda: "vlc")
    monkeypatch.setattr(
        "mf.cli_main.get_config", lambda: {"fullscreen_playback": False}
    )

    import subprocess

    def raise_generic(*a, **k):
        raise Exception("boom")

    monkeypatch.setattr(subprocess, "Popen", raise_generic)

    result = runner.invoke(app_mf, ["play", "next"])
    assert result.exit_code != 0
