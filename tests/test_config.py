import os

from mf.utils import add_search_path, get_config_file, read_config, remove_search_path


def test_config_file_creation(tmp_path, monkeypatch):
    # Redirect config directory
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    assert "search_paths" in cfg
    assert get_config_file().exists()


def test_add_and_remove_search_path(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    path = tmp_path / "media"
    path.mkdir()
    cfg = add_search_path(cfg, str(path))
    assert str(path.resolve().as_posix()) in cfg["search_paths"]
    cfg = remove_search_path(cfg, str(path))
    assert str(path.resolve().as_posix()) not in cfg["search_paths"]
