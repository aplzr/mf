import json
from urllib import request

from .utils.console import print_error

__version__ = "0.7.0"


def get_pypi_version() -> str | None:
    """Get number of latest version published on PyPI
    (https://pypi.org/pypi/mediafinder).

    Returns:
        str | None: Version number or None if check fails.
    """
    url = "https://pypi.org/pypi/mediafinder/json"

    try:
        with request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            return data["info"]["version"]
    except Exception as e:
        print_error(f"Version check failed with error: {e}")
