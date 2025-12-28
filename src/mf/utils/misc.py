from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import typer

from ..constants import FALLBACK_EDITORS_POSIX
from .console import console, print_and_raise
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
    if editor := os.environ.get("VISUAL") or os.environ.get("EDITOR"):
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
    # Heavy imports, import here lazily so they don't slow down every mf invocation
    from guessit import guessit
    from imdbinfo import search_title

    parsed = guessit(result.file.stem)

    if "title" not in parsed:
        print_and_raise(f"Could not parse a title from filename '{result.file.name}'.")

    title = parsed["title"]
    results = search_title(title)

    if results.titles:
        imdb_url = results.titles[0].url
        console.print(f"IMDB entry for [green]{title}[/green]: {imdb_url}")
        typer.launch(imdb_url)
    else:
        print_and_raise(f"No IMDB results found for parsed title {title}.")


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
