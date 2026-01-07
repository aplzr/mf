"""Video player integration with automatic platform detection and fallback.

Provides cross-platform support for launching VLC and mpv media players with automatic
player detection and fallback logic. Handles player discovery via Windows registry,
common paths, and PATH, with command-line argument building based on user configuration.

Features:
    - Automatic player detection (VLC preferred, mpv fallback)
    - Platform-specific discovery (Windows registry, common installation paths, PATH)
    - Configurable playback options (fullscreen, etc.)
    - Single file and playlist support
    - Command-line argument generation from config

Architecture:
    Uses Strategy pattern via PlayerSpec to encapsulate player-specific details.
    Each supported player has a get_command function and options mapping.

Supported Players:
    - VLC and mpv (separate installs)

Platform Support:
    - Windows: Registry lookup → common paths → PATH
    - Unix-like: PATH lookup

Example:
    >>> # Launch a single file
    >>> file = FileResult(Path("movie.mkv"))
    >>> launch_video_player(file)

    >>> # Launch playlist
    >>> files = FileResults([...])
    >>> launch_video_player(files)
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from random import choice
from typing import Literal, NamedTuple, TypedDict, cast

from ..constants import STATUS_SYMBOLS
from .config import Configuration
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
        all_files = FindQuery.from_config("*").execute()

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
) -> Path | None:
    """Get the platform-specific player command.

    Args:
        registry_getter: Function that returns player path from registry (Windows only).
        common_paths: List of common installation paths to check (Windows only).
        command_name: Command name to search in PATH (all platforms).

    Returns:
        Path | None: Path to video player executable or None if it can't be found.
    """
    if os.name == "nt":
        # Try registry first
        if registry_path := registry_getter():
            return registry_path

        # Try common installation paths
        for common_path in common_paths:
            if common_path.exists():
                return common_path

    # Path lookup for unix-like and nt
    if env_path := shutil.which(command_name):
        return Path(env_path)

    return None


def get_vlc_command() -> ResolvedPlayer | None:
    """Get the platform-specific VLC command.

    Returns:
        ResolvedPlayer | None: Path to the vlc executable or None if it can't be found.
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
    vlc_label = "vlc"

    return (
        ResolvedPlayer(vlc_label, player)
        if (player := _get_player_command(get_vlc_from_registry, vlc_paths, vlc_label))
        else None
    )


def get_mpv_command() -> ResolvedPlayer | None:
    """Get the platform-specific MPV command.

    Returns:
        ResolvedPlayer | None: Path to the mpv executable or None if it can't be found.
    """
    mpv_paths = [
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "mpv" / "mpv.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"))
        / "mpv"
        / "mpv.exe",
        Path("C:\\mpv\\mpv.exe"),  # Common portable location
        Path.home() / "AppData" / "Local" / "mpv" / "mpv.exe",  # User-local install
    ]
    mpv_label = "mpv"

    return (
        ResolvedPlayer(mpv_label, player)
        if (player := _get_player_command(get_mpv_from_registry, mpv_paths, mpv_label))
        else None
    )


def launch_video_player(media: FileResult | FileResults):
    """Launch video player with selected file(s).

    Args:
        media (FileResult | FileResults): File or files to play.
    """
    cfg = Configuration.from_config()
    resolved_player = resolve_configured_player(cfg)

    if not resolved_player:
        print_and_raise("No video player could be found. Please install VLC or mpv.")

    player_args: list[str] = [str(resolved_player.path)]

    if isinstance(media, FileResult):
        # Single file
        if not media.file.exists():
            print_and_raise(f"File no longer exists: {media.file}.")

        console.print(f"[green]Playing:[/green] [white]{media.file.name}[/white]")
        console.print(f"[blue]Location:[/blue] [white]{media.file.parent}[/white]")
        player_args.append(str(media.file))
    elif isinstance(media, FileResults):
        # Last search results as playlist
        if missing_files := media.get_missing():
            print_warn(
                "The following files don't exist anymore and will be skipped:\n"
                + "\n".join(str(missing_file.file) for missing_file in missing_files)
            )
            media.filter_by_existence()

        if not media:
            print_and_raise("All files in playlist don't exist anymore, aborting.")

        console.print(
            "[green]Playing:[/green] [white]Last search results as playlist[/white]"
        )
        player_args.extend(str(result.file) for result in media)

    if extra_args := build_player_args(PLAYERS[resolved_player.label], cfg):
        player_args.extend(extra_args)

    try:
        # Launch player in background
        subprocess.Popen(
            player_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        console.print(
            f"[green]{STATUS_SYMBOLS['ok']}[/green]  "
            f"{resolved_player.label} launched successfully"
        )

    except FileNotFoundError as e:
        print_and_raise(
            f"{resolved_player.label} not found. "
            f"Please install {resolved_player.label} media player.",
            raise_from=e,
        )

    except Exception as e:
        print_and_raise(f"Error launching {resolved_player.label}: {e}", raise_from=e)


class PlayerOptions(TypedDict):
    """Mapping from generic player settings in the settings registry to player-specific
    command-line arguments.
    """

    fullscreen_playback: list[str]


@dataclass
class PlayerSpec:
    """Specification for a supported video player.

    Attributes:
        get_command: Function that returns the command to run the player.
        label: Display name of the player.
        options: Player options.
    """

    get_command: Callable[[], ResolvedPlayer | None]
    label: str
    options: PlayerOptions


PLAYERS: dict[str, PlayerSpec] = {
    "vlc": PlayerSpec(
        get_command=get_vlc_command,
        label="vlc",
        options=PlayerOptions(
            fullscreen_playback=["--fullscreen", "--no-video-title-show"]
        ),
    ),
    "mpv": PlayerSpec(
        get_command=get_mpv_command,
        label="mpv",
        options=PlayerOptions(fullscreen_playback=["--fullscreen"]),
    ),
}


class ResolvedPlayer(NamedTuple):
    """Result of player resolution.

    Attributes:
        label: Player label.
        path: Path to player executable.
    """

    label: str
    path: Path


def resolve_configured_player(cfg: Configuration) -> ResolvedPlayer | None:
    """Resolve the configured video player.

    If the 'video_player' setting is set to 'auto' (the default), will try to use VLC
    with automatic fallback to mpv, otherwise use the configured player.

    Args:
        cfg (Configuration): mediafinder configuration.

    Returns:
        ResolvedPlayer | None: Resolved video player if present or None if no player can
            be found.
    """
    if cfg.video_player == "auto":
        return get_vlc_command() or get_mpv_command()

    if cfg.video_player not in PLAYERS:
        print_and_raise(
            f"Invalid video player selected: {cfg.video_player}. "
            "Use 'vlc', 'mpv', or 'auto'."
        )

    return PLAYERS[cfg.video_player].get_command()


def build_player_args(player_spec: PlayerSpec, cfg: Configuration) -> list[str]:
    """Build the argument list for a selected video player for the options that are
    configured in mediafinder's configuration.

    Args:
        player_spec (PlayerSpec): Selected video player.
        cfg (Configuration): mediafinder configuration.

    Returns:
        list[str]: Command line arguments for the player call.
    """
    args_list: list[str] = []

    for option, args in player_spec.options.items():
        if cfg[option]:
            args_list.extend(cast(list[str], args))

    return args_list
