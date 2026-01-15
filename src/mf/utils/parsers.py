"""Parsing utilities for extracting structured data from strings.

Provides functions to parse video resolutions from filenames and time interval
strings into Python objects for use in statistics and configuration.

Functions:
    parse_resolutions: Extract video resolution from filenames
    parse_timedelta_str: Convert time interval strings to timedelta objects

Resolution Parsing:
    Supports both "p-format" (720p, 1080p) and dimension format (1920x1080).
    Normalizes common dimension formats to standard p-format equivalents.

Timedelta Parsing:
    Legacy function used for config migration. Accepts format: <number><unit>
    Units: s (seconds), m (minutes), h (hours), d (days), w (weeks)
"""

from __future__ import annotations

import re
from datetime import timedelta

from .file import FileResults


def parse_resolutions(results: FileResults) -> list[str]:
    """Parse video resolution from filenames.

    Normalizes (width x height) to p-format ("854x480" -> "480p").

    Args:
        results (FileResults): Files to parse resolution from.

    Returns:
        list[str]: All resolution strings found in filenames, normalized to p-format.
    """
    # \b - Word boundary to avoid partial matches
    # (?:...) - Non-capturing group for the alternation
    # (\d{3,4}[pi]) - Group 1: 3-4 digits followed by 'p' or 'i'
    # | - OR operator
    # (\d{3,4}x\d{3,4}) - Group 2: dimension format (width x height)
    # \b - Word boundary
    regex = re.compile(r"\b(?:(\d{3,4}[pi])|(\d{3,4}x\d{3,4}))\b", re.IGNORECASE)
    dimension_to_p = {
        "416x240": "240p",
        "640x360": "360p",
        "854x480": "480p",
        "1280x720": "720p",
        "1920x1080": "1080p",
        "2560x1440": "1440p",
        "3840x2160": "2160p",
        "7680x4320": "4320p",
    }

    def parse_resolution(filename: str):
        if match := regex.search(filename):
            resolution = match.group(1) or match.group(2)

            if "x" in resolution.lower():
                normalized_key = resolution.lower()
                return dimension_to_p.get(normalized_key, resolution)

            return resolution
        return None

    resolutions = [parse_resolution(file.name) for file in results.get_paths()]
    resolutions = [res for res in resolutions if res is not None]
    return resolutions


def parse_video_codecs(results: FileResults) -> list[str]:
    """Parse video codecs from filenames.

    Args:
        results (FileResults): Files to parse video codecs from.

    Returns:
        list[str]: Parsed video codecs.
    """
    # \b - Word boundary to avoid partial matches (e.g., won't match "box264")
    # (?:...) - Non-capturing group for the main alternation
    #
    # Codec patterns (case-insensitive via re.IGNORECASE):
    #   x264|x265 - Encoder-specific tags (indicate re-encodes)
    #   h\.?264|h\.?265 - Standard notation with optional dot (H.264, H264, h.264, h264)
    #   AVC|HEVC - Alternative names for H.264/H.265
    #   VP9|VP8|AV1 - Modern open codecs
    #   XviD|DivX - Legacy MPEG-4 Part 2 codecs
    #   MPEG-?2 - MPEG-2 with optional hyphen
    #   VC-?1|WMV3? - Microsoft codecs (VC-1, VC1, WMV, WMV3)
    #   Hi10P - 10-bit high-profile encoding indicator
    #   ProRes(?:422|4444)? - Apple ProRes variants (base, 422, 4444)
    #   DNxH[DR] - Avid DNxHD/DNxHR professional codecs
    #   MJPEG|Theora - Older formats
    #   RV[34]0 - RealVideo variants (RV30, RV40)
    #   SVQ[13] - Sorenson Video (SVQ1, SVQ3)
    #   Cinepak|Indeo - Ancient codecs
    #   FFV1|HuffYUV - Lossless archival codecs
    #   UT\s?Video - UT Video codec with optional space
    #   MP4V - MPEG-4 Part 2 Visual
    # \b - Word boundary
    pattern = (
        r"\b(?:"
        r"x264|x265|h\.?264|h\.?265|AVC|HEVC|VP9|VP8|AV1|"
        r"XviD|DivX|MPEG-?2|VC-?1|WMV3?|Hi10P|"
        r"ProRes(?:422|4444)?|DNxH[DR]|"
        r"MJPEG|Theora|RV[34]0|SVQ[13]|Cinepak|Indeo|"
        r"FFV1|HuffYUV|UT\s?Video|MP4V"
        r")\b"
    )
    regex = re.compile(pattern, re.IGNORECASE)
    video_mapping = {
        # H.264 variants (untouched/remux indicators)
        "h264": "H.264",
        "avc": "H.264",
        "x264": "x264",
        # H.265 variants (untouched/remux indicators)
        "h265": "H.265",
        "hevc": "H.265",
        "x265": "x265",
        # VP codecs
        "vp8": "VP8",
        "vp9": "VP9",
        "av1": "AV1",
        # Legacy
        "xvid": "XviD",
        "divx": "DivX",
        "vc1": "VC-1",
        "vc-1": "VC-1",
        "wmv": "WMV",
        "wmv3": "WMV3",
        "mpeg2": "MPEG-2",
        "mpeg-2": "MPEG-2",
        # ProRes
        "prores": "ProRes",
        "prores422": "ProRes422",
        "prores4444": "ProRes4444",
        # DNx
        "dnxhd": "DNxHD",
        "dnxhr": "DNxHR",
        # Older formats
        "mjpeg": "MJPEG",
        "theora": "Theora",
        "rv40": "RealVideo",
        "rv30": "RealVideo",
        "svq1": "Sorenson",
        "svq3": "Sorenson",
        "cinepak": "Cinepak",
        "indeo": "Indeo",
        # Lossless
        "ffv1": "FFV1",
        "huffyuv": "HuffYUV",
        "utvideo": "UT Video",
        "mp4v": "MP4V",
        # Special
        "hi10p": "Hi10P",
    }

    def parse_video_codec(filename: str) -> str | None:
        match = regex.search(filename)

        if not match:
            return None

        video_codec = match.group()
        video_codec_lower = video_codec.lower().replace(".", "").replace(" ", "")

        return video_mapping.get(video_codec_lower, video_codec)

    return [
        video_codec
        for file in results.get_paths()
        if (video_codec := parse_video_codec(file.stem)) is not None
    ]


def parse_audio_codecs(results: FileResults) -> list[str]:
    """Parse audio codecs from filenames.

    Args:
        results (FileResults): Files to parse audio codecs from.

    Returns:
        list[str]: Parsed audio codecs.
    """
    # \b - Word boundary to avoid partial matches
    # (?:...) - Non-capturing group for the main alternation
    #  AAC(?:5\.1|51|2\.0|20)? - AAC with optional channel config (5.1, 51, 2.0, 20)
    #  (?:DD|AC-?3)(?:5\.1|51|2\.0|20)? - Dolby Digital/AC3 with optional hyphen and
    #   channels
    #  (?:E-?AC-?3|DDP)(?:5\.1|51|2\.0|20)? - Dolby Digital Plus (EAC3/DDP) with
    #   channels
    #  TrueHD|Atmos - Dolby premium codecs
    #  DTS(?:-HD)?(?:MA|HR|ES|X)?(?:5\.1|51|7\.1|71|2\.0|20)? - DTS variants:
    #   - DTS (base)
    #   - DTS-HD (high definition, optional hyphen)
    #   - MA (Master Audio - lossless), HR (High Resolution), ES (Extended Surround), X
    #     (object-based)
    #   - Optional channel configs (5.1, 51, 7.1, 71, 2.0, 20)
    #  FLAC(?:2\.0|20)?|ALAC - Lossless codecs with optional stereo indicator
    #  MP3|MP2|Opus|Vorbis - Lossy codecs
    #  PCM|LPCM|WMA - Uncompressed/Windows codecs
    # \b - Word boundary
    pattern = (
        r"\b(?:"
        r"AAC(?:5\.1|51|2\.0|20)?|"
        r"(?:DD|AC-?3)(?:5\.1|51|2\.0|20)?|"
        r"(?:E-?AC-?3|DDP)(?:5\.1|51|2\.0|20)?|"
        r"TrueHD|Atmos|"
        r"DTS(?:-HD)?(?:MA|HR|ES|X)?(?:5\.1|51|7\.1|71|2\.0|20)?|"
        r"FLAC(?:2\.0|20)?|ALAC|"
        r"MP3|MP2|Opus|Vorbis|"
        r"PCM|LPCM|WMA"
        r")\b"
    )
    regex = re.compile(pattern, re.IGNORECASE)
    audio_mapping = {
        # AAC variants
        "aac": "AAC",
        "aac51": "AAC",
        "aac5.1": "AAC",
        "aac20": "AAC",
        "aac2.0": "AAC",
        # DD/AC3 variants
        "ac3": "AC3",
        "ac-3": "AC3",
        "dd": "DD",
        "dd51": "DD",
        "dd5.1": "DD",
        "dd20": "DD",
        "dd2.0": "DD",
        # DD+ variants
        "eac3": "DD+",
        "e-ac3": "DD+",
        "e-ac-3": "DD+",
        "eac-3": "DD+",
        "ddp": "DD+",
        "ddp51": "DD+",
        "ddp5.1": "DD+",
        "ddp20": "DD+",
        "ddp2.0": "DD+",
        "dd+": "DD+",
        "dd+51": "DD+",
        "dd+5.1": "DD+",
        "dd+20": "DD+",
        "dd+2.0": "DD+",
        # Dolby TrueHD and Atmos
        "truehd": "TrueHD",
        "atmos": "Atmos",
        # DTS variants
        "dts": "DTS",
        "dts51": "DTS",
        "dts5.1": "DTS",
        "dts20": "DTS",
        "dts2.0": "DTS",
        "dts-hd": "DTS-HD",
        "dtshd": "DTS-HD",
        "dts-hd51": "DTS-HD",
        "dts-hd5.1": "DTS-HD",
        "dtshd51": "DTS-HD",
        "dtshd5.1": "DTS-HD",
        "dts-hdma": "DTS-HD MA",
        "dtshdma": "DTS-HD MA",
        "dtsma": "DTS-HD MA",
        "dts-hdhr": "DTS-HD HR",
        "dtshdhr": "DTS-HD HR",
        "dtshr": "DTS-HD HR",
        "dts-es": "DTS-ES",
        "dtses": "DTS-ES",
        "dtsx": "DTS:X",
        "dts-x": "DTS:X",
        "dts:x": "DTS:X",
        "dts-hdma5.1": "DTS-HD MA",
        "dts-hdma51": "DTS-HD MA",
        "dtshdma5.1": "DTS-HD MA",
        "dtshdma51": "DTS-HD MA",
        "dts-hdma7.1": "DTS-HD MA",
        "dts-hdma71": "DTS-HD MA",
        "dtshdma7.1": "DTS-HD MA",
        "dtshdma71": "DTS-HD MA",
        "dtsma5.1": "DTS-HD MA",
        "dtsma51": "DTS-HD MA",
        "dtsma7.1": "DTS-HD MA",
        "dtsma71": "DTS-HD MA",
        "dts-hdhr5.1": "DTS-HD HR",
        "dts-hdhr51": "DTS-HD HR",
        "dtshdhr5.1": "DTS-HD HR",
        "dtshdhr51": "DTS-HD HR",
        "dtshr5.1": "DTS-HD HR",
        "dtshr51": "DTS-HD HR",
        # Lossless
        "flac": "FLAC",
        "flac20": "FLAC",
        "flac2.0": "FLAC",
        "alac": "ALAC",
        # Lossy
        "mp3": "MP3",
        "mp2": "MP2",
        "opus": "Opus",
        "vorbis": "Vorbis",
        # Uncompressed
        "pcm": "PCM",
        "lpcm": "LPCM",
        # Windows
        "wma": "WMA",
        "wmv": "WMV",
        "wmv3": "WMV3",
        # VP codecs
        "vp8": "VP8",
        "vp9": "VP9",
        "av1": "AV1",
        # ProRes
        "prores": "ProRes",
        "prores422": "ProRes422",
        "prores4444": "ProRes4444",
        # DNx
        "dnxhd": "DNxHD",
        "dnxhr": "DNxHR",
        # Older formats
        "mjpeg": "MJPEG",
        "theora": "Theora",
        "rv40": "RealVideo",
        "rv30": "RealVideo",
        "svq1": "Sorenson",
        "svq3": "Sorenson",
        "cinepak": "Cinepak",
        "indeo": "Indeo",
        # Lossless video
        "ffv1": "FFV1",
        "huffyuv": "HuffYUV",
        "utvideo": "UT Video",
        "mp4v": "MP4V",
        # Legacy
        "xvid": "XviD",
        "divx": "DivX",
        "vc1": "VC-1",
        "vc-1": "VC-1",
        "mpeg2": "MPEG-2",
        "mpeg-2": "MPEG-2",
        # Special
        "hi10p": "Hi10P",
    }

    def parse_audio_codec(filename: str) -> str | None:
        match = regex.search(filename)

        if not match:
            return None

        audio_codec = match.group()
        audio_codec_lower = audio_codec.lower().replace(".", "").replace(" ", "")

        return audio_mapping.get(audio_codec_lower, audio_codec)

    return [
        audio_codec
        for file in results.get_paths()
        if (audio_codec := parse_audio_codec(file.stem)) is not None
    ]


def parse_dynamic_ranges(results: FileResults) -> list[str]:
    """Parse dynamic range from filenames.

    Args:
        results (FileResults): Files to parse audio codecs from.

    Returns:
        list[str]: Parsed dynamic ranges.
    """
    # HDR and color space pattern matcher
    # \b - Word boundary to avoid partial matches
    # (?:...) - Non-capturing group for the main alternation
    #
    # HDR/Color space patterns (case-insensitive via re.IGNORECASE):
    # IMPORTANT: Order from most specific to least specific to avoid false matches
    #   HDR10P(?:lus)? - HDR10Plus/HDR10P variants (must come before HDR10)
    #   HDR10\+ - HDR10+ with literal plus sign (must come before HDR10)
    #   HDR10 - HDR10 standard (must come before generic HDR)
    #   Do\.?Vi\.?|D\.?V\.? - Dolby Vision with optional dots (DoVi, Do.Vi., DV, D.V.)
    #   HLG - Hybrid Log-Gamma (broadcast HDR standard)
    #   HDR - Generic HDR indicator (MUST be last to avoid catching HDR10 variants)
    # \b - Word boundary
    pattern = r"\b(?:HDR10P(?:lus)?|HDR10\+|HDR10|Do\.?Vi\.?|D\.?V\.?|HLG|HDR)\b"

    regex = re.compile(pattern, re.IGNORECASE)
    hdr_mapping = {
        "dovi": "DV",
        "do.vi.": "DV",
        "do.vi": "DV",
        "dovi.": "DV",
        "dv": "DV",
        "d.v.": "DV",
        "d.v": "DV",
        "dv.": "DV",
        "hdr10+": "HDR10+",
        "hdr10plus": "HDR10+",
        "hdr10p": "HDR10+",
        "hdr10": "HDR10",
        "hdr": "HDR",
        "hlg": "HLG",
    }

    def parse_dynamic_range(filename: str) -> str | None:
        matches = regex.findall(filename)  # Get ALL matches, not just first

        if not matches:
            return None

        # Normalize all matches
        normalized = set()
        for match in matches:
            hdr_lower = match.lower().replace(".", "").replace(" ", "")
            norm = hdr_mapping.get(hdr_lower, match)
            normalized.add(norm)

        # Check for dual-layer Dolby Vision first
        if "DV" in normalized and "HDR10+" in normalized:
            return "DV + HDR10+"
        if "DV" in normalized and "HDR10" in normalized:
            return "DV + HDR10"

        # Return most specific single format
        # Priority: HDR10+ > HDR10 > Dolby Vision > HLG > HDR
        priority = ["HDR10+", "HDR10", "DV", "HLG", "HDR"]
        for fmt in priority:
            if fmt in normalized:
                return fmt

        return None

    return [
        dynamic_range
        for file in results.get_paths()
        if (dynamic_range := parse_dynamic_range(file.stem)) is not None
    ]


def parse_release_years(results: FileResults) -> list[str]:
    """Parse year of release from filenames.

    Args:
        results (FileResults): Files to parse video codecs from.

    Returns:
        list[str]: Parsed release years.
    """
    # Match 4-digit year (1900-2099) but NOT at the start of string
    # (?<!^) - Negative lookbehind: not preceded by start of string
    # (?<!^\.) - Also not preceded by start + dot (handles ".1917...")
    # \b(19|20)\d{2}\b - Year pattern with word boundaries
    pattern = r"(?<!^)(?<!^\.)\b(19|20)\d{2}\b"
    regex = re.compile(pattern)

    return [
        match.group()
        for result in results
        if (match := regex.search(result.file.name)) is not None
    ]


def parse_timedelta_str(interval_str: str) -> timedelta:
    """Parse time interval string like '10s', '30m', '2h', '1d', '5w' into timedelta.

    Args:
        interval_str (str): Interval string.

    Raises:
        ValueError: Invalid input.

    Returns:
        timedelta: Parsed time interval.
    """
    # NOTE: This parser is only used to convert the library_cache_interval setting from
    # the old format "<number><unit>" to the new format in seconds, see
    # config.migrate_config.
    pattern = r"^(\d+)([smhdw])$"
    match = re.match(pattern, interval_str.lower().strip())

    if not match:
        raise ValueError(
            f"Invalid time interval format: {interval_str}. "
            "Use format like '30m', '2h', '1d'"
        )

    value, unit = match.groups()
    value = int(value)

    unit_map = {
        "s": timedelta(seconds=value),
        "m": timedelta(minutes=value),
        "h": timedelta(hours=value),
        "d": timedelta(days=value),
        "w": timedelta(weeks=value),
    }

    return unit_map[unit]
