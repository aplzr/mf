import typer
from rich.console import Console

from ..constants import STATUS_SYMBOLS

__all__ = [
    "console",
    "print_error",
    "print_info",
    "print_ok",
    "print_warn",
]

# Shared console instance for the project
console = Console()


def print_ok(msg: str):
    """Print confirmation message.

    Args:
        msg (str): Confirmation message.
    """
    console.print(f"{STATUS_SYMBOLS['ok']}  {msg}", style="green")


def print_warn(msg: str):
    """Print warning message.

    Args:
        msg (str): Warning message.
    """
    console.print(f"{STATUS_SYMBOLS['warn']}  {msg}", style="yellow")


def print_error(msg: str):
    """Print error message and exit with status 1.

    Args:
        msg (str): Error message (include trailing punctuation yourself).
    """
    console.print(f"{STATUS_SYMBOLS['error']} {msg}", style="red")
    raise typer.Exit(1)


def print_info(msg: str):
    """Print info message.

    Args:
        msg (str): Info message.
    """
    console.print(f"{STATUS_SYMBOLS['info']}  {msg}", style="bright_cyan")
