import subprocess

from typer.testing import CliRunner

from mf._app_mf import app_mf
from mf.utils import read_config, save_search_results, write_config

runner = CliRunner()


def test_play_no_fullscreen(monkeypatch, tmp_path):
    media = tmp_path / "video.mp4"
    media.write_text("x")
    save_search_results("*", [media])
    cfg = read_config()
    cfg["fullscreen_playback"] = False
    write_config(cfg)

    captured = {}

    def fake_popen(args, **kwargs):
        captured["args"] = args

        class P:  # minimal process stub
            pass

        return P()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    r = runner.invoke(app_mf, ["play", "1"])
    assert r.exit_code == 0
    assert "VLC launched successfully" in r.stdout
    assert not any(a.startswith("--fullscreen") for a in captured["args"])
