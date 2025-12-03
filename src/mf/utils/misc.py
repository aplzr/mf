from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import typer
from guessit import guessit
from imdbinfo import search_title

from mf.utils.config import read_config

from ..constants import FALLBACK_EDITORS_POSIX
from .console import console, print_and_raise, print_warn
from .file import FileResult


def start_editor(file: Path):
    """Open a file in an editor.

    Resolution order:
        1. VISUAL or EDITOR environment variables.
        2. Windows: Notepad++ if present else notepad.
        3. POSIX: First available editor from FALLBACK_EDITORS_POSIX.

    Args:
        file (Path): File to open.
    """
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        subprocess.run([editor, str(file)])
        return
    if os.name == "nt":  # Windows
        if shutil.which("notepad++"):
            subprocess.run(["notepad++", str(file)])
        else:
            subprocess.run(["notepad", str(file)])
        return
    for ed in FALLBACK_EDITORS_POSIX:
        if shutil.which(ed):
            subprocess.run([ed, str(file)])
            break
    else:
        console.print(f"No editor found. Edit manually: {file}")


def open_imdb_entry(result: FileResult):
    """Print IMDB URL and open it in the default browser if one is available.

    Args:
        result (FileResult): File for which to open the IMDB entry.
    """
    filestem = result.file.stem
    parsed = guessit(filestem)

    if "title" not in parsed:
        print_and_raise(f"Could not parse a title from filename '{filestem}'.")

    title = parsed["title"]
    results = search_title(title)

    if results.titles:
        imdb_url = results.titles[0].url
        console.print(f"IMDB entry for [green]{title}[/green]: {imdb_url}")
        typer.launch(imdb_url)
    else:
        print_and_raise("No IMDB results found for parsed title {title}.")


def validate_search_paths() -> list[Path]:
    """Return existing configured search paths.

    Raises:
        typer.Exit: If no valid search paths are configured.

    Returns:
        list[Path]: List of validated existing search paths.
    """
    search_paths = read_config()["search_paths"]
    validated: list[Path] = []

    for search_path in search_paths:
        p = Path(search_path)

        if not p.exists():
            print_warn(f"Configured search path {search_path} does not exist.")
        else:
            validated.append(p)

    if not validated:
        print_and_raise(
            "List of search paths is empty or paths don't exist. "
            "Set search paths with 'mf config set search_paths'."
        )

    return validated


def format_size(size_bytes: int) -> str:
    """Format a size in bytes to human-readable string with appropriate prefix.

    Args:
        size_bytes (int): Size in bytes.

    Returns:
        str: Formatted string like "1.5 GB" or "250 MB".
    """
    units = [(1024**3, "GB"), (1024**2, "MB"), (1024**1, "kB"), (1, "B")]

    for threshold, unit in units:
        if size_bytes >= threshold:
            value = size_bytes / threshold
            # Use appropriate decimal places based on magnitude
            if value >= 100:
                return f"{value:.0f} {unit}"
            elif value >= 10:
                return f"{value:.1f} {unit}"
            else:
                return f"{value:.2f} {unit}"

    return f"{size_bytes} B"


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
