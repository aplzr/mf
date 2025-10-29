import os

from typer.testing import CliRunner

from mf._app_config import app_config
from mf.utils import get_config_file, read_config

runner = CliRunner()


def _set_env(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )


def test_config_set_and_list(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    r = runner.invoke(
        app_config, ["set", "search_paths", str(tmp_path / "p1"), str(tmp_path / "p2")]
    )
    assert r.exit_code == 0
    cfg = read_config()
    assert len(cfg["search_paths"]) == 2
    r2 = runner.invoke(app_config, ["list"])  # smoke check output
    assert r2.exit_code == 0


def test_config_add_duplicate_warning(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    runner.invoke(app_config, ["set", "search_paths", str(tmp_path / "p1")])
    r = runner.invoke(app_config, ["add", "search_paths", str(tmp_path / "p1")])
    assert r.exit_code == 0  # handled gracefully


def test_config_remove_missing(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    r = runner.invoke(app_config, ["remove", "search_paths", str(tmp_path / "doesnot")])
    assert "skipping" in r.stdout


def test_config_clear_media_extensions(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    runner.invoke(app_config, ["clear", "media_extensions"])  # ensure clears
    cfg = read_config()
    assert cfg["media_extensions"] == []


def test_config_set_match_extensions(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    r = runner.invoke(app_config, ["set", "match_extensions", "false"])  # disable
    assert r.exit_code == 0
    cfg = read_config()
    assert cfg["match_extensions"] is False


def test_config_set_match_extensions_too_many_values(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    r = runner.invoke(
        app_config, ["set", "match_extensions", "true", "false"]
    )  # invalid
    assert r.exit_code != 0


def test_config_get_prints_boolean(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    runner.invoke(app_config, ["set", "match_extensions", "true"])  # set
    r = runner.invoke(app_config, ["get", "match_extensions"])  # should print 'true'
    assert "match_extensions = true" in r.stdout


def test_config_file_outputs_path(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    r = runner.invoke(app_config, ["file"])  # prints path
    assert r.exit_code == 0
    assert str(get_config_file()) in r.stdout
