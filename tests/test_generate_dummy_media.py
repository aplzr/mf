from __future__ import annotations

from mf.utils.generate_dummy_media import (
    create_movies,
    create_shows,
    generate_dummy_media,
    summarize,
)


def test_create_movies_and_shows_and_summary(tmp_path):
    base = tmp_path
    movies_first = create_movies(base)
    shows_first = create_shows(base)
    # All should be newly created on first run
    assert all(not c.existed for c in movies_first + shows_first)
    summary_first = summarize(movies_first + shows_first)
    assert "Created" in summary_first and "skipped 0" in summary_first.lower()

    # Second run: all files should already exist
    movies_second = create_movies(base)
    shows_second = create_shows(base)
    assert all(c.existed for c in movies_second + shows_second)
    summary_second = summarize(movies_second + shows_second)
    assert "skipped" in summary_second


def test_generate_dummy_media_default_base(tmp_path, monkeypatch, capsys):
    # Force CWD to tmp_path to exercise base_dir None branch
    monkeypatch.chdir(tmp_path)
    generate_dummy_media()
    out = capsys.readouterr().out
    assert "Base directory:" in out
    assert (tmp_path / "movies").exists()
    assert (tmp_path / "shows").exists()


def test_generate_dummy_media_custom_base(tmp_path, capsys):
    custom = tmp_path / "custom"
    generate_dummy_media(custom)
    out = capsys.readouterr().out
    assert f"Base directory: {custom}" in out
    assert (custom / "movies").exists()
    assert (custom / "shows").exists()
