import subprocess

from typer.testing import CliRunner

from mf.cli_main import app_mf
from mf.utils.config import get_config, write_config
from mf.utils.file import FileResult
from mf.utils.search import save_search_results

runner = CliRunner()


def test_play_no_fullscreen(monkeypatch, tmp_path):
    media = tmp_path / "video.mp4"
    media.write_text("x")
    save_search_results("*", [FileResult(media)])
    cfg = get_config()
    cfg["fullscreen_playback"] = False
    cfg["video_player"] = "auto"
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
    assert "launched successfully" in r.stdout
    assert not any(a.startswith("--fullscreen") for a in captured["args"])
