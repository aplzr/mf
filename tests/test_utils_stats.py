import math

import pytest

from mf.utils.stats import (
    create_log_bins,
    get_log_bin_centers,
    get_log_histogram,
    get_string_counts,
    group_values_by_bins,
    show_histogram,
)


def test_create_log_bins_clamps_min():
    bins = create_log_bins(min_size=0.5, max_size=1000, bins_per_decade=4)
    assert pytest.approx(bins[0], rel=1e-6) == 1.0
    assert len(bins) >= 1


def test_get_log_bin_centers_geometric_mean():
    edges = [1, 10, 100]
    centers = get_log_bin_centers(edges)
    assert len(centers) == 2
    # Geometric means
    assert pytest.approx(centers[0], rel=1e-6) == math.sqrt(1 * 10)
    assert pytest.approx(centers[1], rel=1e-6) == math.sqrt(10 * 100)


def test_group_values_by_bins_clamping():
    edges = [1, 10, 100]
    values = [-5, 1, 9, 10, 99, 100, 500]
    bins = group_values_by_bins(values, edges)
    # Expect 2 bins for 3 edges
    assert len(bins) == 2
    # Below first edge and first edge values land in first bin
    assert -5 in bins[0]
    assert 1 in bins[0]
    # Edge value 10 belongs to the lower bin with current implementation
    assert 10 in bins[0]
    # Over max clamps to last bin
    assert 500 in bins[1]


def test_get_string_counts_basic():
    counts = get_string_counts(["a", "b", "a", "c", "b", "a"])
    # Validate as set for order-insensitivity
    assert set(counts) == {("a", 3), ("b", 2), ("c", 1)}


def test_get_log_histogram_and_labels():
    values = [100_000, 1_000_000, 10_000_000]
    bin_centers, bin_counts = get_log_histogram(values, bins_per_decade=3)
    # Returns tuple of (bin_centers: list[float], bin_counts: list[int])
    assert isinstance(bin_centers, list)
    assert isinstance(bin_counts, list)
    assert all(isinstance(center, float) for center in bin_centers)
    assert all(isinstance(count, (int, float)) for count in bin_counts)
    # Counts must sum to number of values
    assert sum(bin_counts) == len(values)
    # Bin centers should be positive numbers
    assert all(center > 0 for center in bin_centers)


def test_show_histogram_runs_without_error():
    bins = [(".mp4", 3), (".mkv", 2), (".avi", 1)]
    # Exercise sort and top_n branches
    show_histogram(bins, title="Extensions", sort=True, sort_reverse=False, top_n=2)


def test_print_extension_histogram_all_files(tmp_path):
    """Test extension histogram for all files."""
    from pathlib import Path

    from mf.utils.file import FileResults
    from mf.utils.stats import print_extension_histogram

    # Create test files
    files = [
        tmp_path / "movie.mp4",
        tmp_path / "show.mkv",
        tmp_path / "other.txt",
        tmp_path / "another.mp4",
    ]
    for f in files:
        f.touch()

    results = FileResults.from_paths([str(f) for f in files])
    # Should run without error
    print_extension_histogram(results, type="all_files")


def test_print_extension_histogram_media_files(tmp_path):
    """Test extension histogram for media files only."""
    from pathlib import Path

    from mf.utils.file import FileResults
    from mf.utils.stats import print_extension_histogram

    # Create test files
    files = [tmp_path / "movie.mp4", tmp_path / "show.mkv"]
    for f in files:
        f.touch()

    results = FileResults.from_paths([str(f) for f in files])
    # Should run without error
    print_extension_histogram(results, type="media_files")


def test_print_resolution_histogram(tmp_path):
    """Test resolution histogram."""
    from pathlib import Path

    from mf.utils.file import FileResults
    from mf.utils.stats import print_resolution_histogram

    # Create test files with resolutions that can be parsed
    files = [tmp_path / "movie.1080p.mp4", tmp_path / "show.720p.mkv"]
    for f in files:
        f.touch()

    results = FileResults.from_paths([str(f) for f in files])
    # Should run without error
    print_resolution_histogram(results)


def test_print_file_size_histogram(tmp_path):
    """Test file size histogram."""
    import os
    from pathlib import Path

    from mf.utils.file import FileResult, FileResults
    from mf.utils.stats import print_file_size_histogram

    # Create test files with different sizes
    files = []
    for i, size in enumerate([1000, 5000, 10000]):
        f = tmp_path / f"file{i}.mp4"
        f.write_bytes(b"0" * size)
        files.append(f)

    # Create FileResults with stat info
    results = FileResults(
        [FileResult(str(f), os.stat(f)) for f in files]
    )

    # Should run without error
    print_file_size_histogram(results)
