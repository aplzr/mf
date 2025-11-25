import json

from .console import print_error
from .file import FileResult, get_search_cache_file


def save_last_played(result: FileResult):
    """Save which file was played last to the cached search results file.

    Args:
        result (FileResult): File last played.
    """
    with open(get_search_cache_file(), encoding="utf-8") as f:
        cached = json.load(f)

    last_search_results: list[str] = cached["results"]
    last_played_index = last_search_results.index(str(result))
    cached["last_played_index"] = last_played_index

    with open(get_search_cache_file(), "w", encoding="utf-8") as f:
        json.dump(cached, f, indent=2)


def get_last_played_index() -> int | None:
    """Get the search result index of the last played file.

    Returns:
        int | None: Index or None if no file was played.
    """
    with open(get_search_cache_file(), encoding="utf-8") as f:
        cached = json.load(f)

    try:
        return int(cached["last_played_index"])
    except KeyError:
        return None


def get_next() -> FileResult:
    """Get the next file to play.

    Returns:
        FileResult: Next file to play.
    """
    with open(get_search_cache_file(), encoding="utf-8") as f:
        cached = json.load(f)

    results: list[str] = cached["results"]

    try:
        index_last_played = int(cached["last_played_index"])
    except KeyError:
        # Nothing played yet, start at the beginning
        index_last_played = -1

    try:
        next = FileResult.from_string(results[index_last_played + 1])
        return next
    except IndexError:
        print_error("Last available file already played.")
