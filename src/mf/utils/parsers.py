import re
from collections import Counter

from .file import FileResults


# TODO: only parse, count/sort in the histogram function
def parse_resolution(results: FileResults) -> list[tuple[str, int]]:
    """Parse video resolution from filenames for statistical purposes.

    Args:
        results (FileResults): Files to parse resolution from.

    Returns:
        list[tuple[str, int]]: (resolution, count) pairs, sorted by resolution.
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

    resolution_counts = Counter(
        [_parse_resolution(file.name) for file in results.get_paths()]
    ).items()
    resolution_counts = [
        (name, count) for name, count in resolution_counts if name is not None
    ]
    resolution_counts = sorted(
        resolution_counts,
        key=lambda x: int("".join(filter(str.isdigit, x[0]))) if x[0] else 0,
    )
    return resolution_counts
