from __future__ import annotations

import re
from datetime import timedelta

from .file import FileResults


def parse_resolutions(results: FileResults) -> list[str]:
    """Parse video resolution from filenames for statistical purposes.

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
    pattern = re.compile(r"\b(?:(\d{3,4}[pi])|(\d{3,4}x\d{3,4}))\b", re.IGNORECASE)
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

    def _parse_resolution(filename: str):
        match = pattern.search(filename)

        if match:
            resolution = match.group(1) or match.group(2)

            if "x" in resolution.lower():
                normalized_key = resolution.lower()
                return dimension_to_p.get(normalized_key, resolution)

            return resolution
        return None

    resolutions = [_parse_resolution(file.name) for file in results.get_paths()]
    resolutions = [res for res in resolutions if res is not None]
    return resolutions


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
