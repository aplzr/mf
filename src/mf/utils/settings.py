from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

from tomlkit import TOMLDocument

from ..constants import DEFAULT_MEDIA_EXTENSIONS
from .console import print_and_raise, print_ok, print_warn
from .normalizers import (
    normalize_bool_str,
    normalize_bool_to_toml,
    normalize_media_extension,
    normalize_path,
)

__all__ = [
    "apply_action",
    "REGISTRY",
    "SettingSpec",
]


def _rebuild_cache_if_enabled():
    # Helper function with lazy imports to avoid circular import
    from .cache import rebuild_library_cache
    from .config import read_config

    if read_config()["cache_library"]:
        rebuild_library_cache()


Action = Literal["set", "add", "remove", "clear"]


@dataclass
class SettingSpec:
    """Specification for a configurable setting.

    Attributes:
        key: Name of the setting in the configuration file.
        kind: Kind of setting ('scalar' or 'list').
        value_type: Python type of values loaded from TOML via from_toml.
        actions: Allowed actions for this setting.
        default: Default value(s), used in the default configuration.
        normalize: Function converting a raw string into what is written to TOML.
        from_toml: Function converting value from TOML to the typed value.
        display: Function producing a human readable representation.
        validate_all: Function validating the (possibly list) value(s).
        after_update: Hook to trigger additional action(s) after an update.
        help: Human readable help text shown to the user.
    """

    key: str
    kind: Literal["scalar", "list"]
    value_type: type
    actions: set[Action]
    default: Any
    normalize: Callable[[str], Any] = lambda value: value
    from_toml: Callable[[Any], Any] = lambda value: value
    display: Callable[[Any], str] = lambda value: str(value)
    validate_all: Callable[[Any], None] = lambda value: None
    after_update: Callable[[Any], None] = lambda value: None
    help: str = ""


REGISTRY: dict[str, SettingSpec] = {
    "search_paths": SettingSpec(
        key="search_paths",
        kind="list",
        value_type=str,
        actions={"set", "add", "remove", "clear"},
        normalize=normalize_path,
        from_toml=lambda path: Path(path).resolve(),
        default=[],
        after_update=lambda _: _rebuild_cache_if_enabled(),
        help="Directories scanned for media files.",
    ),
    "media_extensions": SettingSpec(
        key="media_extensions",
        kind="list",
        value_type=str,
        actions={"set", "add", "remove", "clear"},
        normalize=normalize_media_extension,
        default=DEFAULT_MEDIA_EXTENSIONS,
        help="Allowed media file extensions.",
    ),
    "match_extensions": SettingSpec(
        key="match_extensions",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        default=True,
        display=normalize_bool_to_toml,
        help="If true, filter results by media_extensions.",
    ),
    "fullscreen_playback": SettingSpec(
        key="fullscreen_playback",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        default=True,
        display=normalize_bool_to_toml,
        help="If true, files are played in fullscreen mode.",
    ),
    "prefer_fd": SettingSpec(
        key="prefer_fd",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        default=True,
        display=normalize_bool_to_toml,
        help="If true, uses fd for file searches where possible.",
    ),
    "cache_library": SettingSpec(
        key="cache_library",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        default=False,
        display=normalize_bool_to_toml,
        after_update=lambda _: _rebuild_cache_if_enabled(),
        help="If true, caches library metadata locally.",
    ),
    "library_cache_interval": SettingSpec(
        key="library_cache_interval",
        kind="scalar",
        value_type=timedelta,
        actions={"set"},
        default=86400,
        from_toml=lambda interval_s: timedelta(seconds=int(interval_s)),
        help=(
            "Time after which the library cache is automatically rebuilt if "
            "cache_library is set to true, in seconds. Set to 0 to turn off automatic"
            "cache rebuilding. Default value of 86400 s is 1 day."
        ),
    ),
}


def apply_action(
    cfg: TOMLDocument, key: str, action: Action, raw_values: list[str] | None
) -> TOMLDocument:
    """Apply action to setting.

    Args:
        cfg (TOMLDocument): Current configuration.
        key (str): Setting to apply action to.
        action (Action): Action to perform.
        raw_values (list[str] | None): Values to act with.

    Returns:
        TOMLDocument: Updated configuration.
    """
    if key not in REGISTRY:
        print_and_raise(
            f"Unknown configuration key: {key}. Available keys: {list(REGISTRY)}"
        )

    spec = REGISTRY[key]

    if action not in spec.actions:
        print_and_raise(f"Action {action} not supported for {key}.")

    if spec.kind == "scalar" and action == "set":
        if raw_values is None or len(raw_values) > 1:
            print_and_raise(
                f"Scalar setting {key} requires "
                f"a single value for set, got: {raw_values}."
            )

        new_value = spec.normalize(raw_values[0])
        spec.validate_all(new_value)
        cfg[key] = new_value
        spec.after_update(cfg[key])
        print_ok(f"Set {key} to '{spec.display(new_value)}'.")

        return cfg

    # List setting
    if action == "clear":
        cfg[key].clear()
        print_ok(f"Cleared {key}.")
        return cfg

    normalized_values = [spec.normalize(value) for value in raw_values]

    if action == "set":
        cfg[key].clear()
        cfg[key].extend(normalized_values)
        print_ok(f"Set {key} to {normalized_values}.")

    elif action == "add":
        for value in normalized_values:
            if value not in cfg[key]:
                cfg[key].append(value)
                print_ok(f"Added '{value}' to {key}.")
            else:
                print_warn(f"{key} already contains '{value}', skipping.")

    elif action == "remove":
        for value in normalized_values:
            if value in cfg[key]:
                cfg[key].remove(value)
                print_ok(f"Removed '{value}' from {key}.")
            else:
                print_warn(f"'{value}' not found in {key}, skipping.")

    spec.validate_all(cfg[key])
    spec.after_update(cfg[key])

    return cfg
