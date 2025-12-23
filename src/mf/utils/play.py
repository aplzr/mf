from __future__ import annotations

from random import choice
from typing import Literal

from .console import print_and_raise
from .file import FileResult, FileResults
from .playlist import get_next, save_last_played
from .scan import FindQuery
from .search import get_result_by_index, load_search_results


def resolve_play_target(
    target: Literal["next", "list"] | str | None,
) -> FileResult | FileResults:
    """Resolve the target parameter of the play command.

    Args:
        target (Literal["next", "list"] | str | None): What should be played. Either
            next search result, the full search results, or the search result with
            index int(target). If None, returns a random file to play.

    Returns:
        FileResult | FileResults: Single file or files to play.
    """
    if target is None:
        # Play random file
        all_files = FindQuery("*").execute()

        if not all_files:
            print_and_raise("No media files found (empty collection).")

        return choice(all_files)

    elif target.lower() == "next":
        # Play next file from search results
        file_to_play = get_next()
        save_last_played(file_to_play)
        return file_to_play

    elif target.lower() == "list":
        # Send full search results to video player as playlist
        files_to_play, *_ = load_search_results()
        return files_to_play

    else:
        # Play file by search result index
        try:
            index = int(target)
            file_to_play = get_result_by_index(index)
            save_last_played(file_to_play)
            return file_to_play

        except ValueError as e:
            print_and_raise(
                f"Invalid target: {target}. Use an index number, 'next', or 'list'.",
                raise_from=e,
            )
