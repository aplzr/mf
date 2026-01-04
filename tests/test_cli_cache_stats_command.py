from types import SimpleNamespace

from typer.testing import CliRunner

import mf.cli_main as cli_main


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

    monkeypatch.setattr(cli_main, "load_library_cache", lambda: fake_cache)
    monkeypatch.setattr(
        cli_main,
        "get_config",
        lambda: {
            "cache_library": True,
            "media_extensions": [".mp4", ".mkv"],
        },
    )

    # Stub the new utility functions to no-op while tracking calls
    calls = {"extension": 0, "resolution": 0, "file_size": 0}

    def fake_print_extension_histogram(results, type):
        calls["extension"] += 1

    def fake_print_resolution_histogram(results):
        calls["resolution"] += 1

    def fake_print_file_size_histogram(results):
        calls["file_size"] += 1

    monkeypatch.setattr(
        cli_main, "print_extension_histogram", fake_print_extension_histogram
    )
    monkeypatch.setattr(
        cli_main, "print_resolution_histogram", fake_print_resolution_histogram
    )
    monkeypatch.setattr(
        cli_main, "print_file_size_histogram", fake_print_file_size_histogram
    )

    result = runner.invoke(cli_main.app_mf, ["stats"])

    assert result.exit_code == 0
    # Should call extension histogram twice (all files + media files)
    assert calls["extension"] == 2
    # Should call resolution histogram once
    assert calls["resolution"] == 1
    # Should call file size histogram once
    assert calls["file_size"] == 1
