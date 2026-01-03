import json
from pathlib import Path

import pytest
import typer

from mf.utils.cache import _load_search_cache


def test_load_search_cache_success(monkeypatch, tmp_path: Path):
    """Test successfully loading a valid search cache."""
    cache_file = tmp_path / "search_cache.json"
    cache_data = {
        "pattern": "*test*",
        "results": ["/tmp/a.mp4", "/tmp/b.mp4"],
        "timestamp": "2024-01-01T00:00:00",
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    monkeypatch.setattr("mf.utils.cache.get_search_cache_file", lambda: cache_file)

    result = _load_search_cache()
    assert result == cache_data


def test_load_search_cache_with_optional_fields(monkeypatch, tmp_path: Path):
    """Test loading cache with optional last_played_index."""
    cache_file = tmp_path / "search_cache.json"
    cache_data = {
        "pattern": "*test*",
        "results": ["/tmp/a.mp4", "/tmp/b.mp4"],
        "timestamp": "2024-01-01T00:00:00",
        "last_played_index": 1,
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    monkeypatch.setattr("mf.utils.cache.get_search_cache_file", lambda: cache_file)

    result = _load_search_cache()
    assert result == cache_data
    assert result["last_played_index"] == 1


def test_load_search_cache_missing_file(monkeypatch, tmp_path: Path):
    """Test error when cache file doesn't exist."""
    cache_file = tmp_path / "nonexistent.json"

    monkeypatch.setattr("mf.utils.cache.get_search_cache_file", lambda: cache_file)

    with pytest.raises(typer.Exit):
        _load_search_cache()


def test_load_search_cache_invalid_json(monkeypatch, tmp_path: Path):
    """Test error when cache file contains invalid JSON."""
    cache_file = tmp_path / "search_cache.json"
    cache_file.write_text("not valid json", encoding="utf-8")

    monkeypatch.setattr("mf.utils.cache.get_search_cache_file", lambda: cache_file)

    with pytest.raises(typer.Exit):
        _load_search_cache()


def test_load_search_cache_missing_required_keys(monkeypatch, tmp_path: Path):
    """Test error when cache is missing required keys."""
    cache_file = tmp_path / "search_cache.json"
    incomplete_cache = {
        "pattern": "*test*",
        # Missing "results" and "timestamp"
    }
    cache_file.write_text(json.dumps(incomplete_cache), encoding="utf-8")

    monkeypatch.setattr("mf.utils.cache.get_search_cache_file", lambda: cache_file)

    with pytest.raises(typer.Exit):
        _load_search_cache()


def test_load_search_cache_empty_json(monkeypatch, tmp_path: Path):
    """Test error when cache file is empty JSON object."""
    cache_file = tmp_path / "search_cache.json"
    cache_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("mf.utils.cache.get_search_cache_file", lambda: cache_file)

    with pytest.raises(typer.Exit):
        _load_search_cache()
