import json
from pathlib import Path

import pytest
import typer

from mf.utils.validation import validate_search_cache, validate_search_paths


def test_validate_search_cache_valid():
    """Test validation passes with all required keys."""
    valid_cache = {
        "pattern": "*test*",
        "results": ["/tmp/a.mp4", "/tmp/b.mp4"],
        "timestamp": "2024-01-01T00:00:00",
    }
    result = validate_search_cache(valid_cache)
    assert result == valid_cache


def test_validate_search_cache_with_optional_key():
    """Test validation passes with optional last_played_index."""
    valid_cache = {
        "pattern": "*test*",
        "results": ["/tmp/a.mp4", "/tmp/b.mp4"],
        "timestamp": "2024-01-01T00:00:00",
        "last_played_index": 1,
    }
    result = validate_search_cache(valid_cache)
    assert result == valid_cache


def test_validate_search_cache_missing_pattern():
    """Test validation fails when pattern is missing."""
    invalid_cache = {
        "results": ["/tmp/a.mp4"],
        "timestamp": "2024-01-01T00:00:00",
    }
    with pytest.raises(KeyError, match="pattern"):
        validate_search_cache(invalid_cache)


def test_validate_search_cache_missing_results():
    """Test validation fails when results is missing."""
    invalid_cache = {
        "pattern": "*test*",
        "timestamp": "2024-01-01T00:00:00",
    }
    with pytest.raises(KeyError, match="results"):
        validate_search_cache(invalid_cache)


def test_validate_search_cache_missing_timestamp():
    """Test validation fails when timestamp is missing."""
    invalid_cache = {
        "pattern": "*test*",
        "results": ["/tmp/a.mp4"],
    }
    with pytest.raises(KeyError, match="timestamp"):
        validate_search_cache(invalid_cache)


def test_validate_search_cache_missing_all_keys():
    """Test validation fails when all required keys are missing."""
    invalid_cache = {}
    with pytest.raises(KeyError, match="Cache missing required keys"):
        validate_search_cache(invalid_cache)


def test_validate_search_cache_extra_keys():
    """Test validation allows extra keys beyond required ones."""
    cache_with_extra = {
        "pattern": "*test*",
        "results": ["/tmp/a.mp4"],
        "timestamp": "2024-01-01T00:00:00",
        "extra_key": "extra_value",
    }
    result = validate_search_cache(cache_with_extra)
    assert result == cache_with_extra
    assert "extra_key" in result


# Search path validation tests


def test_validate_search_paths_all_exist(monkeypatch, tmp_path: Path):
    """Test validation when all configured paths exist."""
    # Create two directories
    dir1 = tmp_path / "media1"
    dir2 = tmp_path / "media2"
    dir1.mkdir()
    dir2.mkdir()
    path_strings = [str(dir1), str(dir2)]

    result = validate_search_paths(path_strings)
    assert len(result) == 2
    assert dir1 in result
    assert dir2 in result


def test_validate_search_paths_some_exist(monkeypatch, tmp_path: Path):
    """Test validation when only some paths exist (should warn and return existing)."""
    # Create only one directory
    existing_dir = tmp_path / "media1"
    existing_dir.mkdir()
    nonexistent_dir = tmp_path / "media2_does_not_exist"
    path_strings = [str(existing_dir), str(nonexistent_dir)]

    result = validate_search_paths(path_strings)
    assert len(result) == 1
    assert existing_dir in result
    assert Path(nonexistent_dir) not in result


def test_validate_search_paths_none_exist(monkeypatch, tmp_path: Path):
    """Test validation fails when no paths exist."""
    # Use paths that don't exist
    nonexistent1 = tmp_path / "fake1"
    nonexistent2 = tmp_path / "fake2"
    path_strings = [str(nonexistent1), str(nonexistent2)]

    with pytest.raises(typer.Exit):
        validate_search_paths(path_strings)


def test_validate_search_paths_empty_list(monkeypatch):
    """Test validation fails when search paths list is empty."""
    with pytest.raises(typer.Exit):
        validate_search_paths([])
