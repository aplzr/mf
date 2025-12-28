from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
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


def _get_player_from_registry(
    registry_keys: list[tuple[int, str]], executable_name: str
) -> Path | None:
    """Try to get a player path from Windows' registry.

    Args:
        registry_keys: List of (hkey, subkey) tuples to check.
        executable_name: Name of the executable to look for (e.g., "vlc.exe").

    Returns:
        Path | None: Path to the executable if found in registry, None otherwise.
    """
    if os.name != "nt":
        return None

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
                player_path = Path(install_dir) / executable_name
                if player_path.exists():
                    return player_path

        except (OSError, FileNotFoundError):
            # Registry key doesn't exist or access denied
            continue

    return None  # Not found in registry


def get_vlc_from_registry() -> Path | None:
    """Try to get the VLC path from Windows' registry.

    Returns:
        Path | None: Path to vlc.exe if it exists in the registry, None if not.
    """
    registry_keys = [
        # Native installations (VLC bitness matches Windows bitness)
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC"),
        # 32 bit VLC on 64 bit system
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\VideoLAN\VLC"),
    ]
    return _get_player_from_registry(registry_keys, "vlc.exe")


def get_mpv_from_registry() -> Path | None:
    """Try to get the MPV path from Windows' registry.

    Note: MPV doesn't always register itself, especially portable versions.

    Returns:
        Path | None: Path to mpv.exe if it exists in the registry, None if not.
    """
    registry_keys = [
        # System-wide installation
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\mpv"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\mpv"),
        # User-specific installation
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\mpv"),
    ]
    return _get_player_from_registry(registry_keys, "mpv.exe")


def _get_player_command(
    registry_getter: Callable[[], Path | None],
    common_paths: list[Path],
    command_name: str,
) -> str:
    """Get the platform-specific player command.

    Args:
        registry_getter: Function that returns player path from registry.
        common_paths: List of common installation paths to check (Windows only).
        command_name: Command name to use as fallback (e.g., "vlc", "mpv").

    Returns:
        str: Existing path to the player binary or command name for path lookup.
    """
    if os.name == "nt":
        # Try registry first
        if registry_path := registry_getter():
            return str(registry_path)

        # Try common installation paths
        for path in common_paths:
            if path.exists():
                return str(path)

        # Try to find in PATH
        return shutil.which(command_name) or command_name
    else:
        # Unix-like (Linux, macOS)
        return shutil.which(command_name) or command_name


def get_vlc_command() -> str:
    """Get the platform-specific VLC command.

    Returns:
        str: Existing path to the vlc binary or command name for path lookup.
    """
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
    return _get_player_command(get_vlc_from_registry, vlc_paths, "vlc")


def get_mpv_command() -> str:
    """Get the platform-specific MPV command.

    Returns:
        str: Existing path to the mpv binary or command name for path lookup.
    """
    mpv_paths = [
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "mpv" / "mpv.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"))
        / "mpv"
        / "mpv.exe",
        Path("C:\\mpv\\mpv.exe"),  # Common portable location
        Path.home() / "AppData" / "Local" / "mpv" / "mpv.exe",  # User-local install
    ]
    return _get_player_command(get_mpv_from_registry, mpv_paths, "mpv")


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


@dataclass
class PlayerSpec:
    """Specification for a supported video player.

    Attributes:
        commmand_getter: Function that returns the command to run the player.
        args_builder: Function that returns the arguments to pass to the player.
        display_name: Display name of the player.
    """

    command_getter: Callable[[], str]
    args_builder: Callable[[Path | str, list[Path], str], list[str]]  # TODO: check
    display_name: str


PLAYERS: dict[str, PlayerSpec] = {
    "vlc": PlayerSpec(
        command_getter=get_vlc_command,
        args_builder=...,  # type: ignore
        display_name="vlc",
    ),
    "mpv": PlayerSpec(
        command_getter=get_mpv_command,
        args_builder=...,  # type: ignore
        display_name="mpv",
    ),
}
