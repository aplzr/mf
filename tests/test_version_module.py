import json

import pytest
import typer
from packaging.version import Version

from mf.version import check_version, get_pypi_version
from urllib.error import URLError

class DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_pypi_version_success(monkeypatch):
    payload = {"info": {"version": "9.9.9"}}
    monkeypatch.setattr("urllib.request.urlopen", lambda url: DummyResponse(payload))
    v = get_pypi_version()
    assert isinstance(v, Version)
    assert str(v) == "9.9.9"


def test_get_pypi_version_error(monkeypatch):
    def boom(url):
        raise URLError("network down")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(typer.Exit):
        get_pypi_version()


def test_check_version_branches(monkeypatch, capsys):
    # Simulate newer available version
    monkeypatch.setattr("mf.version.get_pypi_version", lambda: Version("9.9.9"))
    check_version()
    out = capsys.readouterr().out + capsys.readouterr().err
    assert "newer version" in out or "upgrade" in out

    # Simulate latest installed
    monkeypatch.setattr("mf.version.get_pypi_version", lambda: Version("0.7.0"))
    check_version()
    out2 = capsys.readouterr().out + capsys.readouterr().err
    assert "latest version" in out2
