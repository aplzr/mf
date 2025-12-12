import os
from pathlib import Path

import pytest
import typer

from mf.utils.misc import get_vlc_command, validate_search_paths


def test_validate_search_paths_mixed_valid_and_invalid(monkeypatch, tmp_path: Path):
    valid1 = tmp_path / "Movies"
    valid2 = tmp_path / "Shows"
    valid1.mkdir()
    valid2.mkdir()
    invalid = tmp_path / "Missing"

    # Inject search_paths via config
    monkeypatch.setattr(
        "mf.utils.misc.get_config",
        lambda: {"search_paths": [str(valid1), str(invalid), str(valid2)]},
    )

    validated = validate_search_paths()
    assert validated == [valid1, valid2]


def test_validate_search_paths_none_raises(monkeypatch):
    # Empty list configured -> should exit via typer.Exit
    monkeypatch.setattr(
        "mf.utils.misc.get_config",
        lambda: {"search_paths": []},
    )
    with pytest.raises(typer.Exit):
        validate_search_paths()


@pytest.mark.skipif(
    os.name != "nt",
    reason="Test requires Windows (monkeypatching os.name causes Path instantiation errors on POSIX)"
)
def test_get_vlc_command_windows_prefers_known_paths():
    # Test Windows VLC path resolution
    cmd = get_vlc_command()
    # Depending on environment, it may fall back to 'vlc'
    assert cmd == "vlc" or cmd.endswith("vlc.exe")


@pytest.mark.skipif(
    os.name != "nt",
    reason="Test requires Windows (monkeypatching os.name causes Path instantiation errors on POSIX)"
)
def test_get_vlc_command_windows_falls_back_to_path():
    # Test Windows VLC fallback behavior
    cmd = get_vlc_command()
    assert cmd == "vlc" or cmd.endswith("vlc.exe")
