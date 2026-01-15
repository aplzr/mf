from mf.utils.file import FileResults
from mf.utils.parsers import parse_release_years


def test_parse_release_years_basic():
    """Test basic year parsing from filenames."""
    files = FileResults.from_paths(
        [
            "Movie 2023.mkv",
            "Show.2022.S01E01.mp4",
            "Documentary.1999.720p.avi",
        ]
    )

    years = parse_release_years(files)

    assert "2023" in years
    assert "2022" in years
    assert "1999" in years
    assert len(years) == 3


def test_parse_release_years_range():
    """Test parsing years from different centuries."""
    files = FileResults.from_paths(
        [
            "Classic.1920.mkv",
            "OldFilm.1950.mp4",
            "Retro.1985.avi",
            "Modern.2020.mkv",
        ]
    )

    years = parse_release_years(files)

    assert "1920" in years
    assert "1950" in years
    assert "1985" in years
    assert "2020" in years


def test_parse_release_years_not_at_start():
    """Test that years at the start of filename are NOT matched."""
    files = FileResults.from_paths(
        [
            "2023.Movie.mkv",  # Should NOT match (at start)
            "Movie.2023.mkv",  # Should match
            "Show 2022.mp4",  # Should match
        ]
    )

    years = parse_release_years(files)

    # Should not include year at start
    assert "2023" in years
    assert "2022" in years
    assert len(years) == 2  # Only 2, not 3


def test_parse_release_years_not_at_start_with_dot():
    """Test that years at start with dot are NOT matched."""
    files = FileResults.from_paths(
        [
            ".1917.Movie.mkv",  # Should NOT match (starts with dot + year)
            "Movie.1917.mkv",  # Should match
        ]
    )

    years = parse_release_years(files)

    # Should only match the second one
    assert len(years) == 1
    assert "1917" in years


def test_parse_release_years_word_boundaries():
    """Test that year matching respects word boundaries."""
    files = FileResults.from_paths(
        [
            "Movie.2023.mkv",  # Should match
            "Show.x2022.mp4",  # Should NOT match (no word boundary before)
            "Video.2021x.avi",  # Should NOT match (no word boundary after)
            "Film 2020 HD.mkv",  # Should match
        ]
    )

    years = parse_release_years(files)

    assert "2023" in years
    assert "2020" in years
    assert "2022" not in years
    assert "2021" not in years
    assert len(years) == 2


def test_parse_release_years_multiple_years():
    """Test files with multiple years.

    Note: Parser only finds ONE year per file (the first match), not all years.
    """
    files = FileResults.from_paths(
        [
            "Movie.2020.Remastered.2023.mkv",
            "Show.1999.Anniversary.2024.mp4",
        ]
    )

    years = parse_release_years(files)

    # Should only match first year from each file
    assert "2020" in years
    assert "1999" in years
    # Should NOT match later years in same filename
    assert "2023" not in years
    assert "2024" not in years
    assert len(years) == 2


def test_parse_release_years_no_matches():
    """Test that files without years return empty list."""
    files = FileResults.from_paths(
        [
            "movie.mkv",
            "video.1080p.mp4",
            "show.BluRay.avi",
        ]
    )

    years = parse_release_years(files)

    assert years == []


def test_parse_release_years_invalid_years():
    """Test that invalid year ranges are not matched."""
    files = FileResults.from_paths(
        [
            "Movie.1899.mkv",  # Before 1900 - should NOT match
            "Show.2100.mp4",  # After 2099 - should NOT match
            "Video.1234.avi",  # Not a valid year range - should NOT match
            "Film.2024.mkv",  # Valid year - should match
        ]
    )

    years = parse_release_years(files)

    # Only valid years (1900-2099) should match
    assert "2024" in years
    assert "1899" not in years
    assert "2100" not in years
    assert "1234" not in years
    assert len(years) == 1


def test_parse_release_years_resolution_confusion():
    """Test that resolutions with numbers aren't confused with years."""
    files = FileResults.from_paths(
        [
            "Movie.2023.1080p.mkv",  # Year should match, not resolution
            "Show.720p.2022.mp4",  # Year should match, not resolution
            "Video.1920x1080.avi",  # Resolution dimensions should NOT match
        ]
    )

    years = parse_release_years(files)

    assert "2023" in years
    assert "2022" in years
    # Resolutions should not be matched
    assert "1080" not in years
    assert "720" not in years
    assert "1920" not in years


def test_parse_release_years_common_patterns():
    """Test common real-world filename patterns."""
    files = FileResults.from_paths(
        [
            "The.Matrix.1999.1080p.BluRay.x264.mkv",
            "Breaking.Bad.S01E01.2008.720p.WEB-DL.mkv",
            "Inception (2010) [1080p].mp4",
            "Avatar 2009 EXTENDED 2160p UHD.mkv",
        ]
    )

    years = parse_release_years(files)

    assert "1999" in years
    assert "2008" in years
    assert "2010" in years
    assert "2009" in years
    assert len(years) == 4


def test_parse_release_years_edge_cases():
    """Test edge cases for year detection."""
    files = FileResults.from_paths(
        [
            "Movie.2000.mkv",  # Millennium year
            "Show.1999.mp4",  # Last year of 20th century
            "Video.2099.avi",  # Last valid year in range
            "Film.1900.mkv",  # First valid year in range
        ]
    )

    years = parse_release_years(files)

    assert "2000" in years
    assert "1999" in years
    assert "2099" in years
    assert "1900" in years
    assert len(years) == 4
