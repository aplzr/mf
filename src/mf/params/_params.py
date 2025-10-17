from collections import defaultdict
from pathlib import Path

# Use local directories on the file server, network shares everywhere else
SEARCH_PATHS_BY_HOSTNAME = defaultdict(
    lambda: [
        Path("//doorstep/bitheap-incoming"),
        Path("//doorstep/bitpile-incoming"),
    ],
    {
        "doorstep": [
            Path("/shared/bitheap-incoming"),
            Path("/shared/bitpile-incoming"),
        ],
    },
)

MEDIA_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
}
