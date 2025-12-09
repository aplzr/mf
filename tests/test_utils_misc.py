import os
from pathlib import Path

import pytest

from mf.utils.misc import get_vlc_command, validate_search_paths


def test_validate_search_paths_mixed(monkeypatch, tmp_path: Path):
    existing = tmp_path / "exists"
    existing.mkdir()

    monkeypatch.setattr(
        "mf.utils.misc.read_config",
        lambda: {
            "search_paths": [existing.as_posix(), (tmp_path / "missing").as_posix()]
        },
    )

    validated = validate_search_paths()
    assert validated == [existing]


def test_validate_search_paths_none(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "mf.utils.misc.read_config",
        lambda: {"search_paths": [(tmp_path / "missing").as_posix()]},
    )

    with pytest.raises(Exception):
        validate_search_paths()


@pytest.mark.skipif(
    os.name != "nt",
    reason="Test requires Windows (monkeypatching os.name causes Path instantiation errors on POSIX)"
)
def test_get_vlc_command_windows_paths():
    # Validate Windows VLC path logic
    cmd = get_vlc_command()
    assert cmd == "vlc" or cmd.endswith("vlc.exe")
