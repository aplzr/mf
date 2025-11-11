import os

from mf.utils.config_utils import get_config_file, read_config


def test_config_file_creation(tmp_path, monkeypatch):
    # Redirect config directory
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )
    cfg = read_config()
    assert "search_paths" in cfg
    assert get_config_file().exists()
