from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from mf.constants import FALLBACK_EDITORS_POSIX

from .console import console

__all__ = ["start_editor"]


def start_editor(file: Path):
    """Open file in user-preferred editor or fall back to common editors."""
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
