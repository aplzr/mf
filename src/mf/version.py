"""Version information and update checking.

Provides the current package version and utilities to check for newer releases
on PyPI. Used by the 'mf version --check' command.

Functions:
    get_pypi_version: Query PyPI API for latest published version
    check_version: Compare local version against PyPI and notify user

Version Comparison:
    Uses packaging.version.Version for semantic versioning comparison.
    Suggests 'uv tool upgrade' command when updates are available.

Error Handling:
    Network errors, JSON parsing errors, and API format changes are caught
    and converted to user-friendly error messages.
"""

from __future__ import annotations

import json
import os
from json import JSONDecodeError
from urllib import request
from urllib.error import URLError

from packaging.version import Version

from .utils.console import print_and_raise, print_info, print_ok

__version__ = "0.11.0"


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
    except URLError as e:
        print_and_raise(f"Network error checking version: {e}", raise_from=e)
    except JSONDecodeError as e:
        print_and_raise(f"Invalid response from PyPI: {e}", raise_from=e)
    except KeyError as e:
        print_and_raise(f"Unexpected PyPI API response format: {e}", raise_from=e)


def check_version():
    """Check installed version against latest available version of mediafinder."""
    pypi_version = get_pypi_version()
    local_version = Version(__version__)

    if pypi_version > local_version:
        upgrade_command = {
            "posix": ("'uv cache clean mediafinder && uv tool upgrade mediafinder'"),
            "nt": ("'uv cache clean mediafinder; uv tool upgrade mediafinder'"),
        }

        print_info(
            "There's a newer version of mediafinder available "
            f"({local_version} → {pypi_version}). "
            f"Run {upgrade_command[os.name]} to upgrade."
        )
    else:
        print_ok(f"You're on the latest version of mediafinder ({local_version}).")
