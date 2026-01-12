"""Application-wide constants and default values.

Defines all constant values used across the mediafinder application including
default configuration values, platform-specific settings, and UI symbols.

Constants:
    DEFAULT_MEDIA_EXTENSIONS: Default video file extensions for new configs
    BOOLEAN_TRUE_VALUES: Accepted strings for boolean true normalization
    BOOLEAN_FALSE_VALUES: Accepted strings for boolean false normalization
    FALLBACK_EDITORS_POSIX: Editor search order on Unix-like systems
    FD_BINARIES: Platform-to-binary mapping for vendored fd tool
    STATUS_SYMBOLS: Unicode symbols for console status messages

Platform Support:
    FD_BINARIES maps (system, machine) tuples to fd binary filenames for
    Linux x86_64, macOS arm64/x86_64, and Windows x86_64.
"""

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
    ".rar",
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
    "info": "ℹ",
}

# Directory name prefix for temporary directories created / used by mediafinder
TEMP_DIR_PREFIX = "mediafinder_video_"
