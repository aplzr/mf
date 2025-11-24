from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from tomlkit import TOMLDocument

from ..constants import DEFAULT_MEDIA_EXTENSIONS
from .console import print_error, print_ok, print_warn
from .normalizers import (
    normalize_bool_str,
    normalize_bool_to_toml,
    normalize_media_extension,
    normalize_path,
    normalize_timedelta_str,
)

__all__ = [
    "apply_action",
    "REGISTRY",
    "SettingSpec",
]

Action = Literal["set", "add", "remove", "clear"]


def _rebuild_cache_if_enabled():
    from .config import read_config
    from .file import rebuild_library_cache

    if read_config()["cache_library"]:
        rebuild_library_cache()


@dataclass
class SettingSpec:
    """Specification for a configurable setting.

    Attributes:
        key: Name of the setting in the configuration file.
        kind: Kind of setting ('scalar' or 'list').
        value_type: Python type of the normalized value(s).
        actions: Allowed actions for this setting.
        normalize: Function converting a raw string into the typed value.
        default: Default value(s), used in the default configuration.
        display: Function producing a human readable representation.
        validate_all: Function validating the (possibly list) value(s).
        help: Human readable help text shown to the user.
        before_write: Hook to transform value(s) before persisting.
        after_update: Hook to trigger additional action(s) after an update.
    """

    key: str
    kind: Literal["scalar", "list"]
    value_type: type
    actions: set[Action]
    normalize: Callable[[str], Any]
    default: Any
    display: Callable[[Any], str] = lambda value: str(value)
    validate_all: Callable[[Any], None] = lambda value: None
    help: str = ""
    before_write: Callable[[Any], any] = lambda value: value
    after_update: Callable[[Any], None] = lambda value: None


REGISTRY: dict[str, SettingSpec] = {
    "search_paths": SettingSpec(
        key="search_paths",
        kind="list",
        value_type=str,
        actions={"set", "add", "remove", "clear"},
        normalize=normalize_path,
        default=[],
        help="Directories scanned for media files.",
        after_update=lambda _: _rebuild_cache_if_enabled(),
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
        help="If true, caches library metadata locally.",
        after_update=lambda _: _rebuild_cache_if_enabled(),
    ),
    "library_cache_interval": SettingSpec(
        key="library_cache_interval",
        kind="scalar",
        value_type=str,
        actions={"set"},
        normalize=normalize_timedelta_str,
        default="1d",
        help=(
            "Time after which the library cache is automatically rebuilt if "
            "cache_library is set to true. Format: '<number><unit>', with unit one of "
            "s, m, h, d, w. Set to '0' (without unit) to turn off automatic cache "
            "rebuilding."
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
        print_error(
            f"Unknown configuration key: {key}. Available keys: {list(REGISTRY)}"
        )

    spec = REGISTRY[key]

    if action not in spec.actions:
        print_error(f"Action {action} not supported for {key}.")

    if spec.kind == "scalar" and action == "set":
        if raw_values is None or len(raw_values) > 1:
            print_error(
                f"Scalar setting {key} requires "
                f"a single value for set, got: {raw_values}."
            )

        new_value = spec.normalize(raw_values[0])
        spec.validate_all(new_value)
        cfg[key] = spec.before_write(new_value)
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
