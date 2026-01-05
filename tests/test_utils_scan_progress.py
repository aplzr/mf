from pathlib import Path

from mf.utils.scan import scan_search_paths


def test_scan_search_paths_progress_no_estimate(monkeypatch, tmp_path: Path):
    # Ensure progress branch without estimate
    monkeypatch.setattr(
        "mf.utils.scan.get_config",
        lambda: {
            "prefer_fd": False,
            "cache_stat": False,
            "cache_library": False,
            "media_extensions": [],
            "match_extensions": False,
            "search_paths": [tmp_path.as_posix()],
            "parallel_search": True,
        },
    )

    monkeypatch.setattr("mf.utils.scan.validate_search_paths", lambda paths: [tmp_path])
    # Ensure cache file doesn't exist
    monkeypatch.setattr(
        "mf.utils.file.get_library_cache_file", lambda: tmp_path / "no.json"
    )

    # Create a couple files to trigger first-file-found and silent progress path
    (tmp_path / "x.mp4").write_text("x")
    (tmp_path / "y.txt").write_text("y")

    res = scan_search_paths(cache_stat=False, prefer_fd=False, show_progress=True)
    names = sorted([r.file.name for r in res])
    assert names == ["x.mp4", "y.txt"]
