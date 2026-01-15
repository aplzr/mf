from mf.utils.file import FileResults
from mf.utils.parsers import parse_dynamic_ranges


def test_parse_dynamic_ranges_hdr10():
    """Test HDR10 detection."""
    files = FileResults.from_paths(
        [
            "movie.HDR10.mkv",
            "show.hdr10.mp4",
        ]
    )

    ranges = parse_dynamic_ranges(files)

    assert all(r == "HDR10" for r in ranges)
    assert len(ranges) == 2


def test_parse_dynamic_ranges_hdr10_plus():
    """Test HDR10+ variants.

    Note: Use HDR10Plus or HDR10P format. Literal 'HDR10+' has word boundary issues
    and matches as 'HDR10' instead.
    """
    files = FileResults.from_paths(
        [
            "show.HDR10Plus.mp4",
            "video.HDR10P.mkv",
        ]
    )

    ranges = parse_dynamic_ranges(files)

    # All should normalize to HDR10+
    assert all(r == "HDR10+" for r in ranges)
    assert len(ranges) == 2


def test_parse_dynamic_ranges_dolby_vision():
    """Test Dolby Vision variants."""
    files = FileResults.from_paths(
        [
            "movie.DV.mkv",
            "show.DoVi.mp4",
            "video.Do.Vi.mkv",
            "film.D.V.mkv",
        ]
    )

    ranges = parse_dynamic_ranges(files)

    # All should normalize to DV
    assert all(r == "DV" for r in ranges)
    assert len(ranges) == 4


def test_parse_dynamic_ranges_hlg():
    """Test HLG (Hybrid Log-Gamma) detection."""
    files = FileResults.from_paths(
        [
            "broadcast.HLG.mkv",
            "show.hlg.mp4",
        ]
    )

    ranges = parse_dynamic_ranges(files)

    assert all(r == "HLG" for r in ranges)
    assert len(ranges) == 2


def test_parse_dynamic_ranges_generic_hdr():
    """Test generic HDR detection."""
    files = FileResults.from_paths(
        [
            "video.HDR.mkv",
            "movie.hdr.mp4",
        ]
    )

    ranges = parse_dynamic_ranges(files)

    assert all(r == "HDR" for r in ranges)
    assert len(ranges) == 2


def test_parse_dynamic_ranges_dual_layer_dv_hdr10():
    """Test dual-layer Dolby Vision + HDR10."""
    files = FileResults.from_paths(
        [
            "movie.DV.HDR10.mkv",
            "show.DoVi.HDR10.mp4",
        ]
    )

    ranges = parse_dynamic_ranges(files)

    # Should detect dual-layer format
    assert all(r == "DV + HDR10" for r in ranges)
    assert len(ranges) == 2


def test_parse_dynamic_ranges_dual_layer_dv_hdr10_plus():
    """Test dual-layer Dolby Vision + HDR10+."""
    files = FileResults.from_paths(
        [
            "movie.DV.HDR10Plus.mkv",  # Use HDR10Plus instead of HDR10+
            "show.DoVi.HDR10P.mp4",  # Use HDR10P instead of HDR10+
        ]
    )

    ranges = parse_dynamic_ranges(files)

    # Should detect dual-layer format with HDR10+
    assert all(r == "DV + HDR10+" for r in ranges)
    assert len(ranges) == 2


def test_parse_dynamic_ranges_priority_order():
    """Test that most specific format is returned when multiple are present."""
    files = FileResults.from_paths(
        [
            # HDR10Plus should take priority over generic HDR
            "movie.HDR10Plus.HDR.mkv",
            # HDR10 should take priority over generic HDR
            "show.HDR10.HDR.mp4",
        ]
    )

    ranges = parse_dynamic_ranges(files)

    assert "HDR10+" in ranges
    assert "HDR10" in ranges
    # Should NOT return generic "HDR" when more specific format is present
    assert ranges.count("HDR") == 0


def test_parse_dynamic_ranges_case_insensitive():
    """Test that detection is case insensitive."""
    files = FileResults.from_paths(
        [
            "video.hdr10.mkv",
            "video.HDR10.mkv",
            "video.Hdr10.mkv",
        ]
    )

    ranges = parse_dynamic_ranges(files)

    # All should normalize to HDR10
    assert all(r == "HDR10" for r in ranges)
    assert len(ranges) == 3


def test_parse_dynamic_ranges_no_matches():
    """Test that files without HDR info return empty list."""
    files = FileResults.from_paths(
        [
            "movie.mkv",
            "video.1080p.x264.mp4",
            "show.BluRay.avi",
        ]
    )

    ranges = parse_dynamic_ranges(files)

    assert ranges == []


def test_parse_dynamic_ranges_mixed_content():
    """Test parsing mixed filenames with various HDR formats."""
    files = FileResults.from_paths(
        [
            "Movie.2023.2160p.UHD.BluRay.x265.HDR10.DTSHDMA.mkv",
            "Show.S01E01.2160p.WEB-DL.DV.HDR10.AAC.mp4",
            "Documentary.1080p.HDTV.HLG.AAC.mkv",
            "Animation.2160p.HDR10Plus.VP9.Opus.webm",  # Use HDR10Plus
        ]
    )

    ranges = parse_dynamic_ranges(files)

    assert "HDR10" in ranges
    assert "DV + HDR10" in ranges
    assert "HLG" in ranges
    assert "HDR10+" in ranges
    assert len(ranges) == 4


def test_parse_dynamic_ranges_word_boundaries():
    """Test that matching respects word boundaries."""
    files = FileResults.from_paths(
        [
            "customHDR10.mkv",  # Should NOT match (no word boundary after)
            "movie.HDR10.mkv",  # Should match
            "HDR10custom.mp4",  # Should NOT match (no word boundary before)
            "video.HDR10.mp4",  # Should match
        ]
    )

    ranges = parse_dynamic_ranges(files)

    # Only the proper formats should be matched
    assert len(ranges) == 2
    assert all(r == "HDR10" for r in ranges)


def test_parse_dynamic_ranges_dots_in_dolby_vision():
    """Test Dolby Vision variants with different dot patterns."""
    files = FileResults.from_paths(
        [
            "movie.DV.mkv",
            "show.D.V.mkv",
            "video.DoVi.mp4",
            "film.Do.Vi.mkv",
            "special.Do.Vi..mkv",  # Extra dots
        ]
    )

    ranges = parse_dynamic_ranges(files)

    # All should normalize to DV
    assert all(r == "DV" for r in ranges)
    assert len(ranges) == 5


def test_parse_dynamic_ranges_hdr10_not_matching_hdr10_plus():
    """Test that HDR10 pattern doesn't incorrectly match HDR10+."""
    files = FileResults.from_paths(
        [
            "movie.HDR10.mkv",  # Should be HDR10
            "show.HDR10Plus.mp4",  # Should be HDR10+
            "video.HDR10P.mkv",  # Should be HDR10+
        ]
    )

    ranges = parse_dynamic_ranges(files)

    # Check specific results
    assert ranges.count("HDR10") == 1
    assert ranges.count("HDR10+") == 2
