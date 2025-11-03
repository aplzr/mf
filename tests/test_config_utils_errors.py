import pytest
import typer

from mf.utils import get_validated_search_paths, read_config, write_config


def test_get_validated_search_paths_empty(monkeypatch):
    cfg = read_config()
    cfg["search_paths"] = []
    write_config(cfg)
    with pytest.raises(typer.Exit):
        get_validated_search_paths()


def test_get_validated_search_paths_all_missing(monkeypatch):
    cfg = read_config()
    cfg["search_paths"] = ["/unlikely/path/that/does/not/exist/for/tests"]
    write_config(cfg)
    with pytest.raises(typer.Exit):
        get_validated_search_paths()
