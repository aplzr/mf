from pathlib import Path
from typing import Callable, Literal, get_args, get_type_hints
from warnings import warn

import typer
from rich.syntax import Syntax
from tomlkit import TOMLDocument

from .utils import console, get_config_file, read_config, start_editor, write_config

app_config = typer.Typer(help="Manage mf configuration.")


def supports_action(setter: Callable, action: Literal["add", "remove"]) -> bool:
    """Check if setter function supports action.

    Args:
        setter (Callable): Setter function.
        action (Literal["add", "remove"]): Action to check.

    Returns:
        bool: True if setter supports action, False otherwise.
    """
    type_hints = get_type_hints(setter)

    if "action" in type_hints:
        return action in get_args(type_hints["action"])
    else:
        return False


def set_search_paths(
    cfg: TOMLDocument, search_paths: list[str], action: Literal["set", "add"] = "set"
) -> TOMLDocument:
    """Set search paths.

    Converts relative paths to full paths, escapes backslashes, etc. Warns wenn a path
    doesn't exist, but sets it anyway.

    Args:
        cfg (TOMLDocument): The current configuration.
        search_paths (list[str]): Updated search paths.

    Returns:
        TOMLDocument: Updated configuration.
    """
    search_paths: list[Path] = [Path(path).resolve() for path in search_paths]

    for path in search_paths:
        if not path.exists():
            warn(f"Search path {path} does not exist (storing anyway).", stacklevel=2)

    cfg["search_paths"] = [str(path) for path in search_paths]

    return cfg


setters = {"search_paths": set_search_paths}


@app_config.command()
def file():
    "Print the configuration file location."
    print(get_config_file())


@app_config.command()
def edit():
    "Edit the config file."
    start_editor(get_config_file())


@app_config.command(name="list")
def list_config():
    "List the current configuration."
    config_file = get_config_file()
    console.print(f"Configuration file: {config_file}\n", style="dim")
    console.print(
        Syntax.from_path(
            config_file,
            lexer="toml",
            line_numbers=True,
        )
    )


@app_config.command()
def get(key: str):
    """Get an mf setting."""
    console.print(f"{key} = {read_config().get(key)}")


@app_config.command()
def set(key: str, value: list[str]):
    """Set an mf setting."""
    write_config(setters[key](read_config(), value))


# TODOs
# - [ ] Add "add" command to append elements to list settings
# - [ ] Add "remove" command to remove elements from list settings
# - [ ] Define expected types for settings (list, str) and check against that when
#       doing things where the type matters
# - [ ] Add media extensions
