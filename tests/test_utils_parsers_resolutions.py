from mf.utils.file import FileResults
from mf.utils.parsers import parse_resolutions


def test_parse_resolutions_mixed_formats():
    files = FileResults.from_paths(
        [
            "video.854x480.mp4",
            "movie 1080p.mkv",
            "clip.640x360.avi",
            "interlaced 1080i.ts",
            "upper 720P.mov",
            "unknown.1234x1234.mp4",
        ]
    )

    res = parse_resolutions(files)

    # Expected normalized resolutions
    assert "480p" in res  # 854x480
    assert "1080p" in res  # 1080p
    assert "360p" in res  # 640x360
    assert "1080i" in res  # interlaced format retained
    assert ("720p" in res) or ("720P" in res)  # uppercase input retained
    # Unknown dimensions should be passed through as-is
    assert "1234x1234" in res
