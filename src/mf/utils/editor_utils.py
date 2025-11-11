from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ..constants import FALLBACK_EDITORS_POSIX
from .console import console

__all__ = ["start_editor"]


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
