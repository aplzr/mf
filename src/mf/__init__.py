from . import params, utils
from ._app_mf import app_mf
from ._version import __version__

__all__ = [
    "__version__",
    "app_mf",
    "main",
    "params",
    "utils",
]


def main():
    app_mf()
