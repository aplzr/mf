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

if os.name == "nt":
    import winreg


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
        str: Existing path to the vlc binary or command name for path lookup.
    """
    if os.name == "nt":
        if registry_vlc := get_vlc_from_registry():
            return str(registry_vlc)

        # Try common VLC installation paths
        vlc_paths = [
            Path(os.environ.get("PROGRAMFILES", "C:\\Program Files"))
            / "VideoLAN"
            / "VLC"
            / "vlc.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"))
            / "VideoLAN"
            / "VLC"
            / "vlc.exe",
            Path.home()
            / "AppData"
            / "Local"
            / "Microsoft"
            / "WindowsApps"
            / "vlc.exe",  # App store
        ]
        vlc_cmd: str | None = None

        for path in vlc_paths:
            if path.exists():
                vlc_cmd = str(path)
                break

        if vlc_cmd is None:
            # Try to find in PATH
            vlc_cmd = "vlc"
    else:  # Unix-like (Linux, macOS)
        vlc_cmd = "vlc"

    return vlc_cmd


def get_vlc_from_registry() -> Path | None:
    """Try to get the VLC path from Window's registry.

    Returns:
        Path | None: Path to vlc.exe if it exists in the registry, None if not.
    """
    if os.name != "nt":
        return None

    registry_keys = [
        # Native installations (VLC bitness matches Windows bitness)
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC"),
        # 32 bit VLC on 64 bit system
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\VideoLAN\VLC"),
    ]

    for hkey, subkey in registry_keys:
        try:
            key = winreg.OpenKey(hkey, subkey)

            # Try to read the InstallDir value, fall back to default value
            try:
                install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
            except FileNotFoundError:
                install_dir, _ = winreg.QueryValueEx(key, "")

            winreg.CloseKey(key)

            if install_dir:
                vlc_path = Path(install_dir) / "vlc.exe"
                if vlc_path.exists():
                    return vlc_path

        except (OSError, FileNotFoundError):
            # Registry key doesn't exist or access denied
            continue

    return None  # Not found in registry


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
