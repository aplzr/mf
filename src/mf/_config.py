import typer
from rich.syntax import Syntax

from .utils import console, get_config_file, start_editor

config_app = typer.Typer(help="Manage mf configuration.")


@config_app.command()
def file():
    "Print the configuration file location."
    print(get_config_file())


@config_app.command()
def edit():
    "Edit the config file."
    start_editor(get_config_file())


@config_app.command()
def list():
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
