from typing import Callable, Literal, get_args, get_type_hints

import tomlkit
import typer
from rich.syntax import Syntax
from tomlkit import TOMLDocument

from .constants import STATUS_SYMBOLS
from .utils import (
    add_media_extension,
    add_search_path,
    console,
    get_config_file,
    normalize_bool_str,
    read_config,
    remove_media_extension,
    remove_search_path,
    start_editor,
    write_config,
)

app_config = typer.Typer(help="Manage mf configuration.")


def supports_action(
    setter: Callable, action: Literal["add", "remove", "clear"]
) -> bool:
    """Check if setter function supports action.

    Args:
        setter (Callable): Setter function.
        action (Literal["add", "remove", "clear"]): Action to check.

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
    action: Literal["set", "add", "remove", "clear"],
) -> TOMLDocument:
    """Set / add / remove / clear search paths.

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
        console.print(f"{STATUS_SYMBOLS['ok']}  Cleared search paths.", style="green")

    else:
        raise ValueError(f"Unknown action: {action}")

    return cfg


def set_media_extensions(
    cfg: TOMLDocument,
    media_extensions: list[str] | None,
    action: Literal["set", "add", "remove", "clear"],
) -> TOMLDocument:
    """Set / add / remove / clear media extensions.

    Args:
        cfg (TOMLDocument): Current configuration.
        media_extensions (list[str] | None): List of media extensions.
        action (Literal["set", "add", "remove", "clear"]): Action to perform.

    Raises:
        ValueError: Unknown action.

    Returns:
        TOMLDocument: Updated configuration.
    """
    if action == "set":
        cfg["media_extensions"].clear()

        for media_extension in media_extensions:
            cfg = add_media_extension(cfg, media_extension)

    elif action == "add":
        for media_extension in media_extensions:
            cfg = add_media_extension(cfg, media_extension)

    elif action == "remove":
        for media_extension in media_extensions:
            cfg = remove_media_extension(cfg, media_extension)

    elif action == "clear":
        cfg["media_extensions"].clear()
        console.print(
            f"{STATUS_SYMBOLS['ok']}  Cleared media extensions.", style="green"
        )

    else:
        raise ValueError(f"Unknown action: {action}.")

    return cfg


def set_match_extensions(
    cfg: TOMLDocument,
    match_extensions: list[str],
    action: Literal["set"],
) -> TOMLDocument:
    """Set match_extensions. If 'true', search results will be matched against the list
    of allowed media file extensions. If 'false', all search results matching the search
    pattern will be returned.

    Args:
        cfg (TOMLDocument): Current configuration.
        match_extensions (list[str]): ['true'] or ['false'].
        action (Literal["set"]): Action to perform.

    Raises:
        typer.Exit: More than one value provided.
        ValueError: Wrong value provided.

    Returns:
        TOMLDocument: Updated configuration.
    """
    if len(match_extensions) > 1:
        console.print(
            (
                f"{STATUS_SYMBOLS['error']} A single value is expected "
                "when setting match_extensions, "
                f"got: {match_extensions}."
            ),
            style="red",
        )
        raise typer.Exit(1)

    bool_ = normalize_bool_str(match_extensions[0])

    if action == "set":
        cfg["match_extensions"] = bool_
        console.print(
            f"{STATUS_SYMBOLS['ok']}  Set match_extensions to '{str(bool_).lower()}'.",
            style="green",
        )
        return cfg
    else:
        raise ValueError(f"Unknown action: {action}")


# {name of setting in the configuration file: setter function}
setters = {
    "search_paths": set_search_paths,
    "media_extensions": set_media_extensions,
    "match_extensions": set_match_extensions,
}


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
    setting = read_config().get(key)

    if setting in [True, False]:
        # Print as TOML
        setting = str(setting).lower()

    console.print(f"{key} = {setting}")


@app_config.command()
def set(key: str, value: list[str]):
    """Set an mf setting."""
    write_config(setters[key](read_config(), value, action="set"))


@app_config.command()
def add(key: str, value: list[str]):
    """Add an element to a list setting."""
    if supports_action(setters[key], "add"):
        write_config(setters[key](read_config(), value, action="add"))
    else:
        console.print(
            f"{STATUS_SYMBOLS['error']} 'add' action not supported for {key} setting.",
            style="red",
        )
        raise typer.Exit(1)


@app_config.command()
def remove(key: str, value: list[str]):
    """Remove an element from a list setting."""
    if supports_action(setters[key], "remove"):
        write_config(setters[key](read_config(), value, action="remove"))
    else:
        console.print(
            f"{STATUS_SYMBOLS['error']} 'remove' action "
            f"not supported for {key} setting.",
            style="red",
        )
        raise typer.Exit(1)


@app_config.command()
def clear(key: str):
    """Clear a setting."""
    if supports_action(setters[key], "clear"):
        write_config(setters[key](read_config(), None, action="clear"))
    else:
        console.print(
            f"{STATUS_SYMBOLS['error']} 'clear' action "
            f"not supported for {key} setting.",
            style="red",
        )
        raise typer.Exit(1)
