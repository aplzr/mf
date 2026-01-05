from pathlib import Path
from mf.utils.config import get_config, write_config
from mf.utils.validation import validate_search_paths

import pytest
import typer



def test_validate_search_paths_none_raises(monkeypatch):
    with pytest.raises(typer.Exit):
        validate_search_paths([])


def test_get_validated_search_paths_all_missing(monkeypatch):
    with pytest.raises(typer.Exit):
        validate_search_paths(["/unlikely/path/that/does/not/exist/for/tests"])


def test_validate_search_paths_none(monkeypatch, tmp_path: Path):
    with pytest.raises(Exception):
        validate_search_paths([(tmp_path / "missing").as_posix()])


def test_validate_search_paths_mixed(monkeypatch, tmp_path: Path):
    existing = tmp_path / "exists"
    existing.mkdir()

    validated = validate_search_paths([existing.as_posix(), (tmp_path / "missing").as_posix()])
    assert validated == [existing]


def test_validate_search_paths_mixed_valid_and_invalid(monkeypatch, tmp_path: Path):
    valid1 = tmp_path / "Movies"
    valid2 = tmp_path / "Shows"
    valid1.mkdir()
    valid2.mkdir()
    invalid = tmp_path / "Missing"

    validated = validate_search_paths([str(valid1), str(invalid), str(valid2)])
    assert validated == [valid1, valid2]
