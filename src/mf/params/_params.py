from collections import defaultdict
from pathlib import Path

# Define local mount points for the search paths per client here, try to use default SMB
# shares for undefined clients (only works on Windows clients).
SEARCH_PATHS_BY_HOSTNAME = defaultdict(
    # Default network search paths
    lambda: [
        Path("//doorstep/bitheap-incoming"),
        Path("//doorstep/bitpile-incoming"),
    ],
    # Mount points of the network search paths on specific clients
    {
        "doorstep": [
            Path("/shared/bitheap-incoming"),
            Path("/shared/bitpile-incoming"),
        ],
    },
    {
        "mediabox": [
            Path("/mnt/media/bitheap-incoming"),
            Path("/mnt/media/bitpile-incoming"),
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
