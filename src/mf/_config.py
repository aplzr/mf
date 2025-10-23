import typer

from .utils import get_config_file, start_editor

config_app = typer.Typer(help="Manage mf configuration.")


@config_app.command()
def file():
    "Print the configuration file location."
    print(get_config_file())


@config_app.command()
def edit():
    "Edit the config file."
    start_editor(get_config_file())
