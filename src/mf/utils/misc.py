from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import typer
from guessit import guessit
from imdbinfo import search_title

from ..constants import FALLBACK_EDITORS_POSIX
from .console import console, print_error
from .file import FileResult

__all__ = [
    "open_imdb_entry",
    "start_editor",
]


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
        print_error(f"Could not parse a title from filename '{filestem}'.")

    title = parsed["title"]
    results = search_title(title)

    if results.titles:
        imdb_url = results.titles[0].url
        console.print(f"IMDB entry for [green]{title}[/green]: {imdb_url}")
        typer.launch(imdb_url)
    else:
        print_error("No IMDB results found for parsed title {title}.")
