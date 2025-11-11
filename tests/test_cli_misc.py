from pathlib import Path

import pytest
from typer.testing import CliRunner

from mf._app_config import app_config
from mf._app_mf import app_mf
from mf.utils import read_config, write_config

runner = CliRunner()


def test_version_command(monkeypatch):
    result = runner.invoke(app_mf, ["version"])
    assert result.exit_code == 0
    assert "Version" not in result.stdout  # only version number printed
    # version string should look like semantic version
    assert result.stdout.strip().count(".") >= 1


def test_main_callback_help(monkeypatch):
    # Invoke without subcommand triggers callback
    result = runner.invoke(app_mf, [])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "Version:" in result.stdout


def test_imdb_parse_failure(monkeypatch, tmp_path):
    # Prepare fake cache with a filename guessit can't parse a title from
    cfg = read_config()
    # Ensure at least one search path exists
    test_dir = tmp_path / "media"
    test_dir.mkdir()
    # Create a file with name unlikely to yield title key (e.g., just year)
    bad_file = test_dir / "2024.mkv"
    bad_file.write_text("x")
    cfg["search_paths"] = [test_dir.resolve().as_posix()]
    write_config(cfg)
    # Simulate a previous search cache referencing the file
    from mf.utils import save_search_results
    from mf.utils.file_utils import FileResult

    save_search_results("*", [FileResult(bad_file)])
    result = runner.invoke(app_mf, ["imdb", "1"])
    assert result.exit_code != 0
    assert "Could not parse a title" in result.stdout


def test_config_clear_paths(monkeypatch):
    cfg = read_config()
    cfg["search_paths"] = [Path.cwd().resolve().as_posix()]
    write_config(cfg)
    result = runner.invoke(app_config, ["clear", "search_paths"])
    assert result.exit_code == 0
    assert read_config()["search_paths"] == []


def test_config_clear_media_extensions(monkeypatch):
    cfg = read_config()
    # Guarantee some entries
    cfg["media_extensions"] = [".mp4", ".mkv"]
    write_config(cfg)
    result = runner.invoke(app_config, ["clear", "media_extensions"])
    assert result.exit_code == 0
    assert read_config()["media_extensions"] == []


def test_invalid_bool_value(monkeypatch):
    # match_extensions set expects 'true' or 'false'; provide invalid
    result = runner.invoke(app_config, ["set", "match_extensions", "notabool"])
    assert result.exit_code != 0
    assert "Invalid boolean value" in result.stdout


def test_duplicate_media_extension_add(monkeypatch):
    cfg = read_config()
    cfg["media_extensions"] = [".mp4"]
    write_config(cfg)
    # Add duplicate
    result = runner.invoke(app_config, ["add", "media_extensions", ".mp4"])
    assert result.exit_code == 0
    # Output should indicate skipping
    assert "already contains" in result.stdout


def test_get_fd_binary_unsupported(monkeypatch):
    # Force an unsupported platform by monkeypatching platform.system/machine
    import platform as platform_module

    monkeypatch.setattr(platform_module, "system", lambda: "PlanetoidOS")
    monkeypatch.setattr(platform_module, "machine", lambda: "AlienCPU")
    from mf.utils import get_fd_binary

    with pytest.raises(RuntimeError):
        get_fd_binary()
