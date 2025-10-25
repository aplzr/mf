from pathlib import Path
from warnings import warn

import typer
from rich.syntax import Syntax
from tomlkit import TOMLDocument

from .utils import console, get_config_file, read_config, start_editor, write_config

app_config = typer.Typer(help="Manage mf configuration.")


def set_search_paths(cfg: TOMLDocument, search_paths: list[str]) -> TOMLDocument:
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
    setters = {"search_paths": set_search_paths}
    write_config(setters[key](read_config(), value))


# TODOs
# - [ ] Add "add" command to append elements to list settings
# - [ ] Add "remove" command to remove elements from list settings
# - [ ] Define expected types for settings (list, str) and check against that when
#       doing things where the type matters
# - [ ] Add media extensions
