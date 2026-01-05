import math
import os

import pytest
from rich.panel import Panel

from mf.utils.console import ColumnLayout, PanelFormat
from mf.utils.stats import (
    create_log_bins,
    get_log_bin_centers,
    get_log_histogram,
    get_string_counts,
    group_values_by_bins,
    make_histogram,
    print_stats,
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


def test_get_log_histogram_empty_values_raises():
    """Test that get_log_histogram raises ValueError for empty values."""
    with pytest.raises(ValueError, match="'values' can't be empty"):
        get_log_histogram([])


def test_make_histogram_returns_panel():
    """Test that make_histogram returns a Rich Panel object."""
    format = PanelFormat(panel_width=50)
    bins = [(".mp4", 3), (".mkv", 2), (".avi", 1)]

    panel = make_histogram(bins, title="Extensions", format=format)

    assert isinstance(panel, Panel)
    assert panel.title == "[bold cyan]Extensions[/bold cyan]"
    assert panel.padding == format.padding
    assert panel.expand is False


def test_make_histogram_sorts_and_limits():
    """Test sorting and top_n parameters."""
    format = PanelFormat(panel_width=50)
    bins = [(".mp4", 3), (".mkv", 2), (".avi", 1)]

    # Should return only top 2 when sorted
    panel = make_histogram(
        bins, title="Extensions", format=format, sort=True,
        sort_key=lambda x: x[1], sort_reverse=True, top_n=2
    )

    assert isinstance(panel, Panel)
    # Title should include "(top 2)"
    assert "(top 2)" in str(panel.title)


def test_make_extension_histogram_all_files(tmp_path):
    """Test extension histogram for all files returns Panel."""
    from pathlib import Path

    from mf.utils.file import FileResults
    from mf.utils.stats import make_extension_histogram

    format = PanelFormat(panel_width=50)

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
    panel = make_extension_histogram(results, type="all_files", format=format)

    assert isinstance(panel, Panel)
    assert "file extensions" in str(panel.title).lower()
    # Should include top_n in title
    assert "(top" in str(panel.title)


def test_make_extension_histogram_media_files(tmp_path):
    """Test extension histogram for media files returns Panel."""
    from pathlib import Path

    from mf.utils.file import FileResults
    from mf.utils.stats import make_extension_histogram

    format = PanelFormat(panel_width=50)

    # Create test files
    files = [tmp_path / "movie.mp4", tmp_path / "show.mkv"]
    for f in files:
        f.touch()

    results = FileResults.from_paths([str(f) for f in files])
    panel = make_extension_histogram(results, type="media_files", format=format)

    assert isinstance(panel, Panel)
    assert "media file extensions" in str(panel.title).lower()


def test_make_resolution_histogram(tmp_path):
    """Test resolution histogram returns Panel."""
    from pathlib import Path

    from mf.utils.file import FileResults
    from mf.utils.stats import make_resolution_histogram

    format = PanelFormat(panel_width=50)

    # Create test files with resolutions that can be parsed
    files = [tmp_path / "movie.1080p.mp4", tmp_path / "show.720p.mkv"]
    for f in files:
        f.touch()

    results = FileResults.from_paths([str(f) for f in files])
    panel = make_resolution_histogram(results, format)

    assert isinstance(panel, Panel)
    assert "resolution" in str(panel.title).lower()


def test_make_filesize_histogram(tmp_path):
    """Test file size histogram returns Panel."""
    import os
    from pathlib import Path

    from mf.utils.file import FileResult, FileResults
    from mf.utils.stats import make_filesize_histogram

    format = PanelFormat(panel_width=50)

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

    panel = make_filesize_histogram(results, format)

    assert isinstance(panel, Panel)
    assert "size" in str(panel.title).lower()


def test_column_layout_basic_initialization():
    """Test basic ColumnLayout initialization."""
    format = PanelFormat(panel_width=50, padding=(1, 1), title_align="left")
    layout = ColumnLayout(n_columns=2, panel_format=format)

    assert layout.n_columns == 2
    assert layout.panel_format.panel_width == 50
    assert layout.terminal_width is None
    assert layout.panel_format.padding == (1, 1)
    assert layout.panel_format.title_align == "left"


def test_panel_format_is_frozen():
    """Test that PanelFormat is immutable."""
    format = PanelFormat(panel_width=50)

    # Should not be able to modify frozen dataclass
    with pytest.raises(Exception):  # FrozenInstanceError
        format.panel_width = 100


def test_column_layout_from_terminal_standard_80_cols(monkeypatch):
    """Test layout for standard 80-column terminal."""
    # Mock terminal size to return 80 columns
    class FakeTerminalSize:
        def __init__(self, columns, lines):
            self.columns = columns
            self.lines = lines

    def fake_get_terminal_size(fallback):
        return FakeTerminalSize(80, 24)

    import shutil
    monkeypatch.setattr(shutil, "get_terminal_size", fake_get_terminal_size)

    layout = ColumnLayout.from_terminal()

    # 80 cols should fit 2 columns at min_width 39
    # 39 * 2 + 1 (spacing) = 79
    assert layout.n_columns == 2
    assert layout.panel_format.panel_width == 39
    assert layout.terminal_width == 80


def test_column_layout_from_terminal_wide_terminal(monkeypatch):
    """Test layout for wide terminal (160 columns)."""
    class FakeTerminalSize:
        def __init__(self, columns, lines):
            self.columns = columns
            self.lines = lines

    def fake_get_terminal_size(fallback):
        return FakeTerminalSize(160, 24)

    import shutil
    monkeypatch.setattr(shutil, "get_terminal_size", fake_get_terminal_size)

    layout = ColumnLayout.from_terminal()

    # 160 cols should fit 4 columns at min_width 39
    # 39 * 4 + 3 (spacing) = 159
    assert layout.n_columns == 4
    assert layout.panel_format.panel_width == 39
    assert layout.terminal_width == 160


def test_column_layout_from_terminal_narrow_terminal(monkeypatch):
    """Test layout for narrow terminal (< 39 columns)."""
    class FakeTerminalSize:
        def __init__(self, columns, lines):
            self.columns = columns
            self.lines = lines

    def fake_get_terminal_size(fallback):
        return FakeTerminalSize(30, 24)

    import shutil
    monkeypatch.setattr(shutil, "get_terminal_size", fake_get_terminal_size)

    layout = ColumnLayout.from_terminal()

    # Too narrow for min_width, should fall back to 1 column at min_width
    assert layout.n_columns == 1
    assert layout.panel_format.panel_width == 39


def test_column_layout_from_terminal_respects_max_width(monkeypatch):
    """Test that panel width is capped at max_width."""
    class FakeTerminalSize:
        def __init__(self, columns, lines):
            self.columns = columns
            self.lines = lines

    def fake_get_terminal_size(fallback):
        return FakeTerminalSize(200, 24)

    import shutil
    monkeypatch.setattr(shutil, "get_terminal_size", fake_get_terminal_size)

    layout = ColumnLayout.from_terminal(max_width=60)

    # Should fit 5 columns at min_width 39
    # 39 * 5 + 4 (spacing) = 199
    assert layout.n_columns == 5
    # Available width: 200 - 4 (spacing) = 196 / 5 = 39.2
    # Should be capped at max_width, but also can't exceed calculated width
    assert layout.panel_format.panel_width <= 60


def test_column_layout_from_terminal_custom_min_width(monkeypatch):
    """Test from_terminal with custom min_width."""
    class FakeTerminalSize:
        def __init__(self, columns, lines):
            self.columns = columns
            self.lines = lines

    def fake_get_terminal_size(fallback):
        return FakeTerminalSize(100, 24)

    import shutil
    monkeypatch.setattr(shutil, "get_terminal_size", fake_get_terminal_size)

    layout = ColumnLayout.from_terminal(min_width=50)

    # 100 cols with min_width 50: should fit 1 column
    # 50 * 2 + 1 = 101 > 100, so only 1 column fits
    assert layout.n_columns == 1
    assert layout.panel_format.panel_width >= 50


def test_column_layout_from_terminal_respects_max_columns(monkeypatch):
    """Test that n_columns is capped at max_columns."""
    class FakeTerminalSize:
        def __init__(self, columns, lines):
            self.columns = columns
            self.lines = lines

    def fake_get_terminal_size(fallback):
        return FakeTerminalSize(300, 24)

    import shutil
    monkeypatch.setattr(shutil, "get_terminal_size", fake_get_terminal_size)

    layout = ColumnLayout.from_terminal(max_columns=3)

    # Even though 300 cols could fit many columns, should be capped at 3
    assert layout.n_columns <= 3


def test_column_layout_from_terminal_uses_fallback(monkeypatch):
    """Test that from_terminal uses fallback when terminal size unavailable."""
    # shutil.get_terminal_size returns fallback when running without a terminal
    layout = ColumnLayout.from_terminal()

    # Should successfully create a layout (using 80x24 fallback)
    assert layout.n_columns >= 1
    assert layout.panel_format.panel_width >= 39


def test_print_stats_runs_without_error(monkeypatch, tmp_path):
    """Test that print_stats executes without error."""
    from pathlib import Path

    from mf.utils.file import FileResult, FileResults

    # Create test files with resolution info in filenames for parse_resolutions
    files = []
    test_files = [
        ("movie.1080p.mp4", 10000),
        ("show.720p.mkv", 5000),
        ("video.4k.mp4", 20000),
    ]
    for filename, size in test_files:
        f = tmp_path / filename
        f.write_bytes(b"0" * size)
        files.append(f)

    # Create FileResults with stat info - FileResult expects Path, not str
    results = FileResults([FileResult(f, os.stat(f)) for f in files])

    # Mock dependencies
    monkeypatch.setattr(
        "mf.utils.stats.get_config",
        lambda: {
            "media_extensions": [".mp4", ".mkv"],
            "search_paths": [str(tmp_path)],
        },
    )
    monkeypatch.setattr("mf.utils.stats.load_library", lambda: results)

    # Should run without error
    print_stats()


def test_print_stats_without_configured_extensions(monkeypatch, tmp_path):
    """Test print_stats when no media extensions are configured."""
    from pathlib import Path

    from mf.utils.file import FileResult, FileResults

    # Create test files with resolution info
    files = []
    test_files = ["movie.1080p.mp4", "show.720p.mkv", "video.4k.mp4"]
    for filename in test_files:
        f = tmp_path / filename
        f.write_bytes(b"0" * 1000)
        files.append(f)

    # FileResult expects Path, not str
    results = FileResults([FileResult(f, os.stat(f)) for f in files])

    # Mock with no media extensions configured
    monkeypatch.setattr(
        "mf.utils.stats.get_config",
        lambda: {
            "media_extensions": [],
            "search_paths": [str(tmp_path)],
        },
    )
    monkeypatch.setattr("mf.utils.stats.load_library", lambda: results)

    # Should run without error (won't create media_files histograms)
    print_stats()
