import os
from pathlib import Path

from typer.testing import CliRunner

from mf._app_cache import app_cache
from mf.utils import get_cache_file, save_search_results

runner = CliRunner()


def _set_env(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME", str(tmp_path)
    )


def test_cache_show_empty_exits(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    r = runner.invoke(app_cache, ["show"])
    assert r.exit_code != 0


def test_cache_show_after_save(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    save_search_results("*foo*", [(1, Path("/tmp/foo.mp4"))])
    r = runner.invoke(app_cache, ["show"])
    assert r.exit_code == 0
    assert "*foo*" in r.stdout


def test_cache_file_outputs_path(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    r = runner.invoke(app_cache, ["file"])
    assert r.exit_code == 0
    # Normalize output by removing newlines introduced by rich wrapping or console
    normalized_stdout = r.stdout.replace("\n", "")
    assert str(get_cache_file()).replace("\\", "/") in normalized_stdout.replace(
        "\\", "/"
    )


def test_cache_clear_removes_file(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    save_search_results("x", [(1, Path("/tmp/x.mp4"))])
    assert get_cache_file().exists()
    r = runner.invoke(app_cache, ["clear"])
    assert r.exit_code == 0
    assert not get_cache_file().exists()


def test_cache_default_invokes_show(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    save_search_results("pattern", [(1, Path("/tmp/a.mp4"))])
    r = runner.invoke(app_cache, [])
    assert r.exit_code == 0
    assert "Cached results:" in r.stdout
