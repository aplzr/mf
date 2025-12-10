from typer.testing import CliRunner

import mf.cli_cache as cli_cache
from mf.cli_cache import app_cache

runner = CliRunner()


def test_cache_rebuild_invokes(monkeypatch):
    called = {"v": False}
    monkeypatch.setattr(
        cli_cache, "rebuild_library_cache", lambda: called.__setitem__("v", True)
    )
    result = runner.invoke(app_cache, ["rebuild"])
    assert result.exit_code == 0
    assert called["v"] is True
