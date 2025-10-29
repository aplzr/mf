import tomlkit
import typer
from rich.syntax import Syntax

from .utils import (
    apply_action,
    console,
    get_config_file,
    read_config,
    start_editor,
    write_config,
)

app_config = typer.Typer(help="Manage mf configuration.")


@app_config.command()
def file():
    "Print the configuration file location."
    print(get_config_file())


@app_config.command()
def edit():
    "Edit the configuration file."
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
    """Get a setting."""
    setting = read_config().get(key)

    if setting in [True, False]:
        # Print as TOML
        setting = str(setting).lower()

    console.print(f"{key} = {setting}")


@app_config.command()
def set(key: str, values: list[str]):
    """Set a setting."""
    cfg = read_config()
    cfg = apply_action(cfg, key, "set", values)
    write_config(cfg)


@app_config.command()
def add(key: str, values: list[str]):
    """Add value(s) to a list setting."""
    cfg = read_config()
    cfg = apply_action(cfg, key, "add", values)
    write_config(cfg)


@app_config.command()
def remove(key: str, values: list[str]):
    """Remove value(s) from a list setting."""
    cfg = read_config()
    cfg = apply_action(cfg, key, "remove", values)
    write_config(cfg)


@app_config.command()
def clear(key: str):
    """Clear a setting."""
    cfg = read_config()
    cfg = apply_action(cfg, key, "clear", None)
    write_config(cfg)
