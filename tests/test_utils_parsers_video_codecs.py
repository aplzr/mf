from mf.utils.file import FileResults
from mf.utils.parsers import parse_video_codecs


def test_parse_video_codecs_h264_variants():
    """Test H.264 variants are correctly parsed and normalized."""
    files = FileResults.from_paths(
        [
            "movie.h264.mkv",
            "show.H.264.mp4",
            "video.AVC.avi",
            "film.x264.mkv",
        ]
    )

    codecs = parse_video_codecs(files)

    assert "H.264" in codecs  # h264
    assert "H.264" in codecs  # H.264
    assert "H.264" in codecs  # AVC
    assert "x264" in codecs  # x264 (encoder-specific)


def test_parse_video_codecs_h265_variants():
    """Test H.265 variants are correctly parsed and normalized."""
    files = FileResults.from_paths(
        [
            "movie.h265.mkv",
            "show.H.265.mp4",
            "video.HEVC.avi",
            "film.x265.mkv",
        ]
    )

    codecs = parse_video_codecs(files)

    assert "H.265" in codecs  # h265
    assert "H.265" in codecs  # H.265
    assert "H.265" in codecs  # HEVC
    assert "x265" in codecs  # x265 (encoder-specific)


def test_parse_video_codecs_modern_codecs():
    """Test modern codecs (VP8, VP9, AV1)."""
    files = FileResults.from_paths(
        [
            "video.VP8.webm",
            "clip.vp9.webm",
            "movie.AV1.mkv",
        ]
    )

    codecs = parse_video_codecs(files)

    assert "VP8" in codecs
    assert "VP9" in codecs
    assert "AV1" in codecs


def test_parse_video_codecs_legacy_codecs():
    """Test legacy codecs (XviD, DivX, MPEG-2)."""
    files = FileResults.from_paths(
        [
            "old.XviD.avi",
            "vintage.divx.avi",
            "classic.MPEG-2.mpg",
            "broadcast.MPEG2.ts",
        ]
    )

    codecs = parse_video_codecs(files)

    assert "XviD" in codecs
    assert "DivX" in codecs
    assert "MPEG-2" in codecs  # MPEG-2
    assert "MPEG-2" in codecs  # MPEG2


def test_parse_video_codecs_professional_codecs():
    """Test professional codecs (ProRes, DNxHD, DNxHR)."""
    files = FileResults.from_paths(
        [
            "footage.ProRes.mov",
            "edit.ProRes422.mov",
            "master.ProRes4444.mov",
            "clip.DNxHD.mxf",
            "final.DNxHR.mov",
        ]
    )

    codecs = parse_video_codecs(files)

    assert "ProRes" in codecs
    assert "ProRes422" in codecs
    assert "ProRes4444" in codecs
    assert "DNxHD" in codecs
    assert "DNxHR" in codecs


def test_parse_video_codecs_case_insensitive():
    """Test that codec detection is case insensitive."""
    files = FileResults.from_paths(
        [
            "video.h264.mkv",
            "video.H264.mkv",
            "video.H.264.mkv",
            "video.h.264.mkv",
        ]
    )

    codecs = parse_video_codecs(files)

    # All should normalize to H.264
    assert all(codec == "H.264" for codec in codecs)
    assert len(codecs) == 4


def test_parse_video_codecs_no_matches():
    """Test that files without codec info return empty list."""
    files = FileResults.from_paths(
        [
            "movie.mkv",
            "video.1080p.mp4",
            "show.BluRay.avi",
        ]
    )

    codecs = parse_video_codecs(files)

    assert codecs == []


def test_parse_video_codecs_mixed_content():
    """Test parsing mixed filenames with various codecs."""
    files = FileResults.from_paths(
        [
            "Movie.2023.1080p.BluRay.x264.DTS-HD.MA.mkv",
            "Show.S01E01.2160p.WEB-DL.H.265.AAC.mp4",
            "Documentary.720p.HDTV.XviD.AC3.avi",
            "Animation.1080p.VP9.Opus.webm",
        ]
    )

    codecs = parse_video_codecs(files)

    assert "x264" in codecs
    assert "H.265" in codecs
    assert "XviD" in codecs
    assert "VP9" in codecs
    assert len(codecs) == 4


def test_parse_video_codecs_word_boundaries():
    """Test that codec matching respects word boundaries."""
    files = FileResults.from_paths(
        [
            "box264.mkv",  # Should NOT match x264
            "movie.x264.mkv",  # Should match x264
            "h264custom.mp4",  # Should NOT match h264
            "video.h264.mp4",  # Should match h264
        ]
    )

    codecs = parse_video_codecs(files)

    # Only the proper codecs should be matched
    assert len(codecs) == 2
    assert "x264" in codecs
    assert "H.264" in codecs


def test_parse_video_codecs_special_formats():
    """Test special video formats (Hi10P, lossless codecs)."""
    files = FileResults.from_paths(
        [
            "anime.Hi10P.mkv",
            "archive.FFV1.mkv",
            "lossless.HuffYUV.avi",
            "master.UT Video.mov",
        ]
    )

    codecs = parse_video_codecs(files)

    assert "Hi10P" in codecs
    assert "FFV1" in codecs
    assert "HuffYUV" in codecs
    assert "UT Video" in codecs
