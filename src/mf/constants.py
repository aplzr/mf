from __future__ import annotations

# Default media file extensions included in a fresh config.
DEFAULT_MEDIA_EXTENSIONS: list[str] = [
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
]

# Boolean normalization sets (lowercase tokens)
BOOLEAN_TRUE_VALUES: set[str] = {"1", "true", "yes", "y", "on", "enable", "enabled"}
BOOLEAN_FALSE_VALUES: set[str] = {"0", "false", "no", "n", "off", "disable", "disabled"}

# POSIX fallback editors in order of preference.
FALLBACK_EDITORS_POSIX: list[str] = ["nano", "vim", "vi"]

# Mapping of (system, machine) -> fd binary filename.
FD_BINARIES: dict[tuple[str, str], str] = {
    ("linux", "x86_64"): "fd-v10_3_0-x86_64-unknown-linux-gnu",
    ("darwin", "arm64"): "fd-v10_3_0-aarch64-apple-darwin",
    ("darwin", "x86_64"): "fd-v10_3_0-x86_64-apple-darwin",
    ("windows", "x86_64"): "fd-v10_3_0-x86_64-pc-windows-msvc.exe",
}

# Status symbols for consistent console messages.
STATUS_SYMBOLS = {
    "ok": "✔",
    "warn": "⚠",
    "error": "❌",
}

__all__ = [
    "DEFAULT_MEDIA_EXTENSIONS",
    "BOOLEAN_TRUE_VALUES",
    "BOOLEAN_FALSE_VALUES",
    "FALLBACK_EDITORS_POSIX",
    "FD_BINARIES",
    "STATUS_SYMBOLS",
]
