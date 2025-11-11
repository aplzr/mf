"""media file finder and player."""

from . import utils
from .cli_main import app_mf
from .version import __version__

__all__ = [
    "__version__",
    "app_mf",
    "main",
    "utils",
]


def main():
    app_mf()
