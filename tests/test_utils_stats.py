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
    hist = get_log_histogram(values, bins_per_decade=3)
    # Returns list of (label, count)
    assert all(isinstance(lbl, str) and isinstance(cnt, int) for lbl, cnt in hist)
    # Counts must sum to number of values
    assert sum(cnt for _, cnt in hist) == len(values)
    # Labels are human-readable sizes
    assert any("kB" in lbl or "MB" in lbl or "GB" in lbl for lbl, _ in hist)


def test_show_histogram_runs_without_error():
    bins = [(".mp4", 3), (".mkv", 2), (".avi", 1)]
    # Exercise sort and top_n branches
    show_histogram(bins, title="Extensions", sort=True, sort_reverse=False, top_n=2)
