"""media file finder and player."""

from . import utils
from ._version import __version__
from .cli_main import app_mf

__all__ = [
    "__version__",
    "app_mf",
    "main",
    "utils",
]


def main():
    app_mf()
