from typing import Callable, Literal, get_args, get_type_hints

import tomlkit
import typer
from rich.syntax import Syntax
from tomlkit import TOMLDocument

from .utils import (
    add_search_path,
    console,
    get_config_file,
    read_config,
    remove_search_path,
    start_editor,
    write_config,
)

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
    cfg: TOMLDocument,
    search_paths: list[str] | None,
    action: Literal["set", "add", "remove", "clear"] = "set",
) -> TOMLDocument:
    """Set / add / remove / clear search paths.

    Converts relative paths to full paths, escapes backslashes, etc. Warns wenn a path
    doesn't exist, but sets it anyway.

    Args:
        cfg (TOMLDocument): The current configuration.
        search_paths (list[str] | None): Paths to set / add / remove or None when
            search paths are cleared.
        action: (Literal["set", "add", "remove", "clear"]): Action to perform.

    Returns:
        TOMLDocument: Updated configuration.
    """
    if action == "set":
        cfg["search_paths"].clear()

        for search_path in search_paths:
            cfg = add_search_path(cfg, search_path)

    elif action == "add":
        for search_path in search_paths:
            cfg = add_search_path(cfg, search_path)

    elif action == "remove":
        for search_path in search_paths:
            remove_search_path(cfg, search_path)

    elif action == "clear":
        cfg["search_paths"].clear()
        console.print("✔  Cleared search paths.", style="green")

    else:
        raise ValueError(f"Unknown action: {action}")

    return cfg


# {name of setting in the configuration file: setter function}
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
    console.print(f"Configuration file: {get_config_file()}\n", style="dim")
    console.print(
        Syntax(
            code=tomlkit.dumps(read_config()),
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


@app_config.command()
def add(key: str, value: list[str]):
    """Add an element to a list setting."""
    if supports_action(setters[key], "add"):
        write_config(setters[key](read_config(), value, action="add"))
    else:
        console.print(
            f"⚠  'add' action not supported for {key} setting.", style="yellow"
        )
        raise typer.Exit(1)


@app_config.command()
def remove(key: str, value: list[str]):
    """Remove an element from a list setting."""
    if supports_action(setters[key], "remove"):
        write_config(setters[key](read_config(), value, action="remove"))
    else:
        console.print(
            f"⚠  'remove' action not supported for {key} setting.", style="yellow"
        )
        raise typer.Exit(1)


@app_config.command()
def clear(key: str):
    """Clear a setting."""
    write_config(setters[key](read_config(), None, action="clear"))


# TODOs
# - [x] Add "add" command to append elements to list settings
# - [x] Add "remove" command to remove elements from list settings
# - [x, sort of (check if action is supported by setter instead)] Define expected types
#   for settings (list, str) and check against that when doing things where the type
#   matters
# - [ ] Add media extensions
# - [ ] Remove params module
# - [x] Fix:
# # mf config get search_paths
# search_paths = ['\\\\doorstep\\bitheap-incoming\\', '\\\\doorstep\\bitpile-incoming\\']

#  ap on  ~/development/mf
#  mf 3.12.0 add-config ≢  ~1  3
# # mf config remove search_paths \\\\doorstep\\bitpile-incoming\\
# \\\\doorstep\bitpile-incoming not found in configuration
