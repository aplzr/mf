import os

from mf.utils.config import get_config_file, read_config


def test_config_file_creation(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", str(tmp_path)
    )

    # Reset cache AFTER changing environment
    import mf.utils.config

    mf.utils.config._config = None

    cfg = read_config()
    assert "search_paths" in cfg
    assert get_config_file().exists()
