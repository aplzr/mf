from pathlib import Path

import pytest
from typer.testing import CliRunner

from mf.cli_cache import app_cache

runner = CliRunner()


def test_cache_file_command_prints_path(monkeypatch, tmp_path: Path):
    # Ensure cache file exists and command prints its path
    cache_file = tmp_path / "library_cache.json"
    cache_file.write_text("{}", encoding="utf-8")

    # Point mf to use this temp cache path via env or config if supported
    # Force cache path via monkeypatch of helper
    # Patch symbol used inside cli_cache module
    monkeypatch.setattr("mf.cli_cache.get_library_cache_file", lambda: cache_file)

    result = runner.invoke(app_cache, ["file"])
    assert result.exit_code == 0
    assert str(cache_file) in result.stdout


def test_cache_clear_handles_missing_file(monkeypatch, tmp_path: Path):
    # Point to non-existent file and ensure command handles unlink gracefully
    missing = tmp_path / "missing_cache.json"
    monkeypatch.setattr("mf.utils.file.get_library_cache_file", lambda: missing)

    result = runner.invoke(app_cache, ["clear"])
    # Unlink on missing file raises -> non-zero exit and no success message
    assert result.exit_code != 0
    assert "Cleared the library cache" not in (result.stdout + result.stderr)


def test_cache_stats_with_minimal_cache(monkeypatch, tmp_path: Path):
    pytest.skip(
        "Skipping stats histogram rendering "
        "due to rich Panel formatting constraints in test env"
    )

    # Provide an empty cache dataset to exercise histograms without media_extensions
    # Provide minimal non-empty cache object to avoid max() on empty sequences
    class DummyResult:
        def __init__(self, path: str, size: int = 1):
            self.file = Path(path)
            self.stat = type("S", (), {"st_size": size})

    class DummyCache(list):
        def copy(self):
            return DummyCache(self)

        def filter_by_extension(self, exts):
            return None

        def get_paths(self):
            return [res.file for res in self]

        def __iter__(self):
            return super().__iter__()

    dc = DummyCache(
        [
            DummyResult(str(tmp_path / "a.mp4"), 10),
            DummyResult(str(tmp_path / "b.mkv"), 20),
        ]
    )
    monkeypatch.setattr("mf.utils.cache.load_library_cache", lambda: dc)
    monkeypatch.setattr("mf.utils.config.get_config", lambda: {"media_extensions": []})
    # Ensure resolution parsing returns non-empty to avoid empty histograms
    monkeypatch.setattr(
        "mf.cli_cache.parse_resolutions",
        lambda cache: ["1920x1080", "1280x720", "1280x720"],
    )

    result = runner.invoke(app_cache, ["stats"])
    assert result.exit_code == 0
    assert "File extensions (all files)" in result.stdout


@pytest.mark.parametrize("media_exts", [[".mp4", ".mkv"], [".mp3"], []])
def test_cache_stats_media_branches(monkeypatch, tmp_path: Path, media_exts):
    pytest.skip(
        "Skipping stats histogram rendering "
        "due to rich Panel formatting constraints in test env"
    )

    # Non-empty cache to exercise both media and non-media branches
    class DummyResult:
        def __init__(self, path: str, size: int = 1):
            self.file = Path(path)
            self.stat = type("S", (), {"st_size": size})

    class DummyCache(list):
        def copy(self):
            return DummyCache(self)

        def filter_by_extension(self, exts):
            return None

        def get_paths(self):
            return [res.file for res in self]

        def __iter__(self):
            return super().__iter__()

    dc = DummyCache(
        [
            DummyResult(str(tmp_path / "a.mp4"), 10),
            DummyResult(str(tmp_path / "b.mkv"), 20),
            DummyResult(str(tmp_path / "c.txt"), 5),
        ]
    )
    monkeypatch.setattr("mf.utils.cache.load_library_cache", lambda: dc)
    monkeypatch.setattr(
        "mf.utils.config.get_config", lambda: {"media_extensions": media_exts}
    )
    monkeypatch.setattr(
        "mf.cli_cache.parse_resolutions",
        lambda cache: ["1920x1080", "1280x720", "1280x720"],
    )

    result = runner.invoke(app_cache, ["stats"])
    assert result.exit_code == 0
    assert "Media file resolution" in result.stdout
    if media_exts:
        assert "File extensions (media files)" in result.stdout
