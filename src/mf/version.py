import json
from urllib import request

from packaging.version import Version

from .utils.console import print_error, print_info

__version__ = "0.7.0"


def get_pypi_version() -> Version:
    """Get number of latest version published on PyPI
    (https://pypi.org/pypi/mediafinder).

    Returns:
        Version: Version number.
    """
    url = "https://pypi.org/pypi/mediafinder/json"

    try:
        with request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            return Version(data["info"]["version"])
    except Exception as e:
        print_error(f"Version check failed with error: {e}")


def check_version():
    """Check installed version against latest available version of mediafinder."""
    pypi_version = get_pypi_version()
    local_version = Version(__version__)

    if pypi_version > local_version:
        print_info(
            "There's a newer version of mediafinder available "
            f"({local_version} → {pypi_version}). "
            "Use 'uv tool upgrade mediafinder' to upgrade."
        )
    else:
        print_info(f"You're on the latest version of mediafinder ({local_version}).")
