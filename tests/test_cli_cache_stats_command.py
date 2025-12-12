from types import SimpleNamespace

from typer.testing import CliRunner

import mf.cli_cache as cli_cache


class FakeResults:
    def __init__(self, paths):
        self._paths = paths

    def copy(self):
        return FakeResults(self._paths[:])

    def filter_by_extension(self, exts):
        # no-op for test
        return self

    def get_paths(self):
        return self._paths

    def __iter__(self):
        class R:
            def __init__(self, size):
                self.stat = SimpleNamespace(st_size=size)

        return iter([R(100), R(200), R(300)])


def test_cli_cache_stats_invokes_histograms(monkeypatch, tmp_path):
    runner = CliRunner()

    # Fake cache with three files
    cache_paths = [tmp_path / "a.mp4", tmp_path / "b.mkv", tmp_path / "c.txt"]
    fake_cache = FakeResults(cache_paths)

    monkeypatch.setattr(cli_cache, "load_library_cache", lambda: fake_cache)
    monkeypatch.setattr(
        cli_cache, "get_config", lambda: {"media_extensions": [".mp4", ".mkv"]}
    )

    # Stub dependent functions to no-op while tracking calls
    calls = {"console": 0, "hist": 0}

    def fake_console_print(*args, **kwargs):
        calls["console"] += 1

    def fake_show_histogram(*args, **kwargs):
        calls["hist"] += 1

    def fake_parse_resolutions(results):
        return ["1080p", "720p"]

    monkeypatch.setattr(cli_cache, "console", SimpleNamespace(print=fake_console_print))
    monkeypatch.setattr(cli_cache, "show_histogram", fake_show_histogram)
    monkeypatch.setattr(cli_cache, "parse_resolutions", fake_parse_resolutions)

    result = runner.invoke(cli_cache.app_cache, ["stats"])

    assert result.exit_code == 0
    # At least one console print and multiple histograms called
    assert calls["console"] >= 1
    assert calls["hist"] >= 3
