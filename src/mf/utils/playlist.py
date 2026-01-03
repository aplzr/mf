"""Playlist navigation and playback state management.

Tracks which file was last played in the current search results and provides
navigation functions to move through the playlist. Playback state is persisted
in the search results cache file.

State Management:
    The last played index is stored in the search cache JSON file under the
    key "last_played_index". This index is 0-based and refers to a position
    in the cached results list.

Navigation:
    - get_next(): Advance to next file in playlist
    - get_last_played_index(): Get current position for display
    - save_last_played(): Update position after playing a file

Limitations:
    - No wraparound: get_next() fails at end of playlist
    - No backward navigation: No get_previous() function
    - No shuffle support
    - Tightly coupled to search cache format

Dependencies:
    Requires search results to be cached (via 'mf find' or 'mf new').
    Functions will fail if cache doesn't exist or is corrupted.

Error Handling:
    All functions should catch exceptions and use print_and_raise() to convert
    them to user-friendly messages. Currently missing comprehensive error handling.

Examples:
    >>> # After running 'mf find *.mkv'
    >>> next_file = get_next()  # Get first file
    >>> save_last_played(next_file)  # Mark as played
    >>> next_file = get_next()  # Get second file

    >>> # Check current position
    >>> index = get_last_played_index()
    >>> if index is not None:
    ...     print(f"Currently at position {index + 1}")

Note:
    This module assumes a single-threaded CLI environment with no concurrent
    access to the cache file. Race conditions are possible but unlikely in
    normal CLI usage.
"""

from __future__ import annotations

import json

from .console import print_and_raise
from .file import FileResult, get_search_cache_file, open_utf8


def save_last_played(result: FileResult):
    """Save which file was played last to the cached search results file.

    Args:
        result (FileResult): File last played.
    """
    with open_utf8(get_search_cache_file()) as f:
        cached = json.load(f)

    last_search_results: list[str] = cached["results"]
    last_played_index = last_search_results.index(str(result))
    cached["last_played_index"] = last_played_index

    with open_utf8(get_search_cache_file(), "w") as f:
        json.dump(cached, f, indent=2)


def get_last_played_index() -> int | None:
    """Get the search result index of the last played file.

    Returns:
        int | None: Index or None if no file was played.
    """
    with open_utf8(get_search_cache_file()) as f:
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
    with open_utf8(get_search_cache_file()) as f:
        cached = json.load(f)

    results: list[str] = cached["results"]

    try:
        index_last_played = int(cached["last_played_index"])
    except KeyError:
        # Nothing played yet, start at the beginning
        index_last_played = -1

    try:
        return FileResult.from_string(results[index_last_played + 1])
    except IndexError as e:
        print_and_raise("Last available file already played.", raise_from=e)
