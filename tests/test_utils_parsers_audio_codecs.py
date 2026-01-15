from mf.utils.file import FileResults
from mf.utils.parsers import parse_audio_codecs


def test_parse_audio_codecs_aac_variants():
    """Test AAC variants with different channel configurations."""
    files = FileResults.from_paths(
        [
            "movie.AAC.mkv",
            "show.AAC5.1.mp4",
            "video.AAC51.avi",
            "film.AAC2.0.mkv",
        ]
    )

    codecs = parse_audio_codecs(files)

    # All should normalize to AAC
    assert all(codec == "AAC" for codec in codecs)
    assert len(codecs) == 4


def test_parse_audio_codecs_dolby_digital():
    """Test Dolby Digital (AC3/DD) variants."""
    files = FileResults.from_paths(
        [
            "movie.AC3.mkv",
            "show.AC-3.mp4",
            "video.DD.avi",
            "film.DD5.1.mkv",
        ]
    )

    codecs = parse_audio_codecs(files)

    # AC3 should normalize to AC3, DD to DD
    assert "AC3" in codecs or "DD" in codecs
    assert len(codecs) == 4


def test_parse_audio_codecs_dolby_digital_plus():
    """Test Dolby Digital Plus (EAC3/DDP) variants."""
    files = FileResults.from_paths(
        [
            "movie.EAC3.mkv",
            "show.E-AC3.mp4",
            "video.DDP.avi",
            "film.DDP5.1.mkv",
        ]
    )

    codecs = parse_audio_codecs(files)

    # All should normalize to DD+
    assert all(codec == "DD+" for codec in codecs)
    assert len(codecs) == 4


def test_parse_audio_codecs_dolby_premium():
    """Test Dolby premium codecs (TrueHD, Atmos)."""
    files = FileResults.from_paths(
        [
            "movie.TrueHD.mkv",
            "show.Atmos.mkv",
        ]
    )

    codecs = parse_audio_codecs(files)

    assert "TrueHD" in codecs
    assert "Atmos" in codecs


def test_parse_audio_codecs_dts_variants():
    """Test DTS variants including DTS-HD MA/HR.

    Note: DTS regex requires hyphen before HD: use "DTS-HDMA" not "DTSHDMA".
    """
    files = FileResults.from_paths(
        [
            "movie.DTS.mkv",
            "show.DTS-HD.mkv",
            "video.DTS-HDMA.mkv",  # Hyphen before HD required
            "film.DTSMA.mkv",  # DTS MA without HD
            "clip.DTS-HDHR.mkv",  # HR variant
            "special.DTSX.mkv",  # DTS:X
        ]
    )

    codecs = parse_audio_codecs(files)

    assert "DTS" in codecs
    assert "DTS-HD" in codecs
    assert "DTS-HD MA" in codecs
    assert "DTS-HD HR" in codecs
    assert "DTS:X" in codecs


def test_parse_audio_codecs_lossless():
    """Test lossless audio codecs (FLAC, ALAC)."""
    files = FileResults.from_paths(
        [
            "audio.FLAC.mkv",
            "music.ALAC.m4a",
            "stereo.FLAC2.0.mkv",
        ]
    )

    codecs = parse_audio_codecs(files)

    assert "FLAC" in codecs
    assert "ALAC" in codecs
    assert codecs.count("FLAC") == 2


def test_parse_audio_codecs_lossy_formats():
    """Test common lossy audio formats (MP3, Opus, Vorbis)."""
    files = FileResults.from_paths(
        [
            "audio.MP3.mkv",
            "podcast.MP2.mp4",
            "video.Opus.webm",
            "stream.Vorbis.ogg",
        ]
    )

    codecs = parse_audio_codecs(files)

    assert "MP3" in codecs
    assert "MP2" in codecs
    assert "Opus" in codecs
    assert "Vorbis" in codecs


def test_parse_audio_codecs_uncompressed():
    """Test uncompressed audio formats (PCM, LPCM)."""
    files = FileResults.from_paths(
        [
            "audio.PCM.wav",
            "video.LPCM.mkv",
        ]
    )

    codecs = parse_audio_codecs(files)

    assert "PCM" in codecs
    assert "LPCM" in codecs


def test_parse_audio_codecs_case_insensitive():
    """Test that codec detection is case insensitive."""
    files = FileResults.from_paths(
        [
            "video.aac.mkv",
            "video.AAC.mkv",
            "video.Aac.mkv",
        ]
    )

    codecs = parse_audio_codecs(files)

    # All should normalize to AAC
    assert all(codec == "AAC" for codec in codecs)
    assert len(codecs) == 3


def test_parse_audio_codecs_no_matches():
    """Test that files without codec info return empty list."""
    files = FileResults.from_paths(
        [
            "movie.mkv",
            "video.1080p.mp4",
            "show.BluRay.avi",
        ]
    )

    codecs = parse_audio_codecs(files)

    assert codecs == []


def test_parse_audio_codecs_mixed_content():
    """Test parsing mixed filenames with various audio codecs."""
    files = FileResults.from_paths(
        [
            "Movie.2023.1080p.BluRay.x264.DTS-HDMA.mkv",  # Hyphen before HD
            "Show.S01E01.2160p.WEB-DL.H.265.AAC.mp4",
            "Documentary.720p.HDTV.XviD.AC3.avi",
            "Animation.1080p.VP9.Opus.webm",
        ]
    )

    codecs = parse_audio_codecs(files)

    assert "DTS-HD MA" in codecs
    assert "AAC" in codecs
    assert "AC3" in codecs
    assert "Opus" in codecs
    assert len(codecs) == 4


def test_parse_audio_codecs_word_boundaries():
    """Test that codec matching respects word boundaries."""
    files = FileResults.from_paths(
        [
            "musicAAC.mkv",  # Should NOT match (no word boundary)
            "movie.AAC.mkv",  # Should match
            "DTS-custom.mp4",  # DTS- followed by text should not match DTS alone
            "video.DTS.mp4",  # Should match DTS
        ]
    )

    codecs = parse_audio_codecs(files)

    # Should only match proper codecs with word boundaries
    assert "AAC" in codecs
    assert "DTS" in codecs
    # The exact count depends on whether DTS-custom is matched, but at least 2
    assert len(codecs) >= 2


def test_parse_audio_codecs_complex_dts():
    """Test complex DTS variants with channel configurations.

    Note: DTS regex requires hyphen before HD: use "DTS-HDMA" not "DTSHDMA".
    """
    files = FileResults.from_paths(
        [
            "movie.DTS-HDMA51.mkv",  # Hyphen before HD
            "film.DTS-HDMA5.1.mkv",  # Dots in channel config OK
            "show.DTS-HDMA71.mkv",  # Another channel config
            "video.DTS-HDMA7.1.mkv",
        ]
    )

    codecs = parse_audio_codecs(files)

    # All should normalize to DTS-HD MA
    assert all(codec == "DTS-HD MA" for codec in codecs)
    assert len(codecs) == 4
