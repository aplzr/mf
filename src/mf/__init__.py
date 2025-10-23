from . import params, utils
from ._mf import app
from ._version import __version__

__all__ = [
    "__version__",
    "app",
    "main",
    "params",
    "utils",
]


def main():
    app()
