from . import params, utils
from ._mf import app
from ._version import __version__

__all__ = [
    "app",
    "params",
    "main",
    "utils",
]


def main():
    app()
