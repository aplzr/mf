from typing import Any

import typer
from rich.syntax import Syntax
from tomlkit import TOMLDocument

from .utils import console, get_config_file, read_config, start_editor, write_config

config_app = typer.Typer(help="Manage mf configuration.")


def set_search_paths(cfg: TOMLDocument, search_paths: list[str]):
    if len(search_paths) == 1:
        search_paths = search_paths[0]

    cfg["search_paths"] = search_paths
    return cfg


@config_app.command()
def file():
    "Print the configuration file location."
    print(get_config_file())


@config_app.command()
def edit():
    "Edit the config file."
    start_editor(get_config_file())


@config_app.command(name="list")
def list_config():
    "List the current configuration."
    config_file = get_config_file()
    console.print(f"Configuration file: {config_file}\n", style="dim")
    console.print(
        Syntax.from_path(
            config_file,
            lexer="toml",
            background_color="default",
            line_numbers=False,
        )
    )


@config_app.command()
def get(key: str):
    """Get an mf option."""
    console.print(f"{key} = {read_config().get(key)}")


@config_app.command()
def set(key: str, value: list[str]):
    """Set an mf option."""
    setters = {"search_paths": set_search_paths}

    cfg = read_config()
    cfg = setters[key](cfg, value)

    # TODO: remove
    print(value)
    print(cfg)

    write_config(cfg)
