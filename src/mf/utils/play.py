from __future__ import annotations

import os
import subprocess
from pathlib import Path
from random import choice
from typing import Literal

from .config import get_config
from .console import console, print_and_raise, print_warn
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


def get_vlc_command() -> str:
    """Get the platform-specific VLC command.

    Returns:
        str: VLC command.
    """
    if os.name == "nt":
        # Try common VLC installation paths
        vlc_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ]
        vlc_cmd = None
        for path in vlc_paths:
            if Path(path).exists():
                vlc_cmd = path
                break

        if vlc_cmd is None:
            # Try to find in PATH
            vlc_cmd = "vlc"
    else:  # Unix-like (Linux, macOS)
        vlc_cmd = "vlc"

    return vlc_cmd


def launch_video_player(file_to_play: FileResult | FileResults):
    """Launch video player with selected file(s).

    Args:
        file_to_play (FileResult | FileResults): File or files to play.
    """
    vlc_cmd = get_vlc_command()
    vlc_args = [vlc_cmd]

    if isinstance(file_to_play, FileResult):
        # Single file
        if not file_to_play.file.exists():
            print_and_raise(f"File no longer exists: {file_to_play.file}.")

        console.print(
            f"[green]Playing:[/green] [white]{file_to_play.file.name}[/white]"
        )
        console.print(
            f"[blue]Location:[/blue] [white]{file_to_play.file.parent}[/white]"
        )
        vlc_args.append(str(file_to_play.file))
    elif isinstance(file_to_play, FileResults):
        # Last search results as playlist
        if missing_files := file_to_play.get_missing():
            print_warn(
                "The following files don't exist anymore and will be skipped:\n"
                + "\n".join(str(missing_file.file) for missing_file in missing_files)
            )
            file_to_play.filter_by_existence()

        if not file_to_play:
            print_and_raise("All files in playlist don't exist anymore, aborting.")

        console.print(
            "[green]Playing:[/green] [white]Last search results as playlist[/white]"
        )
        vlc_args.extend(str(result.file) for result in file_to_play)

    fullscreen_playback = get_config()["fullscreen_playback"]

    if fullscreen_playback:
        vlc_args.extend(["--fullscreen", "--no-video-title-show"])

    try:
        # Launch VLC in background
        subprocess.Popen(
            vlc_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        console.print("[green]✓[/green] VLC launched successfully")

    except FileNotFoundError as e:
        print_and_raise("VLC not found. Please install VLC media player.", raise_from=e)

    except Exception as e:
        print_and_raise(f"Error launching VLC: {e}", raise_from=e)
