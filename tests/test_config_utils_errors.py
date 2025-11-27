import pytest
import typer

from mf.utils.config import read_config, write_config
from mf.utils.misc import validate_search_paths


def test_get_validated_search_paths_empty(monkeypatch):
    cfg = read_config()
    cfg["search_paths"] = []
    write_config(cfg)
    with pytest.raises(typer.Exit):
        validate_search_paths()


def test_get_validated_search_paths_all_missing(monkeypatch):
    cfg = read_config()
    cfg["search_paths"] = ["/unlikely/path/that/does/not/exist/for/tests"]
    write_config(cfg)
    with pytest.raises(typer.Exit):
        validate_search_paths()
