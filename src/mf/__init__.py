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
    """Main entry point for the mf CLI application.

    This function is called when the package is executed as a script
    or via the installed console script 'mf' or 'mediafinder'.
    """
    app_mf()
