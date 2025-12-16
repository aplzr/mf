from __future__ import annotations

import tomlkit
import typer
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Column, Table

from .utils.config import get_config, get_config_file, write_config
from .utils.console import console, print_and_raise
from .utils.misc import start_editor
from .utils.settings import REGISTRY, apply_action

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
            code=tomlkit.dumps(get_config()),
            lexer="toml",
            line_numbers=True,
        )
    )


@app_config.command()
def get(key: str):
    """Get a setting."""
    try:
        setting = get_config()[key]
    except tomlkit.exceptions.NonExistentKey as e:
        print_and_raise(
            f"Invalid key: '{key}'. Available keys: "
            f"{', '.join(repr(key) for key in REGISTRY)}",
            raise_from=e,
        )

    console.print(f"{key} = {REGISTRY[key].display(setting)}")


@app_config.command()
def set(key: str, values: list[str]):
    """Set a setting."""
    cfg = get_config()
    cfg = apply_action(cfg, key, "set", values)
    write_config(cfg)


@app_config.command()
def add(key: str, values: list[str]):
    """Add value(s) to a list setting."""
    cfg = get_config()
    cfg = apply_action(cfg, key, "add", values)
    write_config(cfg)


@app_config.command()
def remove(key: str, values: list[str]):
    """Remove value(s) from a list setting."""
    cfg = get_config()
    cfg = apply_action(cfg, key, "remove", values)
    write_config(cfg)


@app_config.command()
def clear(key: str):
    """Clear a setting."""
    cfg = get_config()
    cfg = apply_action(cfg, key, "clear", None)
    write_config(cfg)


@app_config.command()
def settings():
    "List all available settings."
    table = Table(
        Column("Setting", style="cyan", no_wrap=True),
        Column("Type", style="magenta", no_wrap=True),
        Column("Actions", style="green"),
        Column("Description", style="white"),
        show_header=True,
        box=None,
        padding=(0, 1),
    )

    for key, spec in REGISTRY.items():
        actions = ", ".join(spec.actions)
        table.add_row(
            key, f"{spec.kind}, {spec.value_type.__name__}", actions, spec.help
        )

    panel = Panel(
        table,
        title="[bold]Available settings[/bold]",
        title_align="left",
        padding=(1, 1),
    )

    console.print()
    console.print(panel)
