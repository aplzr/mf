"""Settings registry and configuration action system.

Provides a centralized registry of all configurable settings with their metadata,
validation rules, and transformation functions. Settings are defined once in the
SETTINGS registry and used throughout the application.

Architecture:
    Registry Pattern:
        - SETTINGS: Central registry mapping setting names to specifications
        - SettingSpec: Complete metadata for a single setting
        - apply_action: Unified action handler for all setting modifications

    Setting Lifecycle:
        User Input → normalize() → TOML → from_toml() → Typed Value

        1. User provides raw string value
        2. normalize() converts to TOML-compatible format
        3. Written to TOML configuration file
        4. from_toml() converts to final Python type
        5. validate_all() ensures value is valid
        6. after_update() triggers any side effects

    Action System:
        Scalar settings: Only support 'set' action
        List settings: Support 'set', 'add', 'remove', 'clear' actions
        Each setting declares which actions it supports in its spec

Design Trade-off:
    Configuration class uses dynamic attributes (setattr) to maintain single
    source of truth in SETTINGS registry. This sacrifices static type checking
    for DRY principle - adding a new setting only requires updating the registry,
    not parallel class definitions.

Features:
    - Type conversion pipeline (string → TOML → Python type)
    - Custom validation per setting
    - Reactive updates via after_update hooks
    - Normalized display for user feedback
    - Extensible: new settings require only registry entry

Available Settings: see SETTINGS registry.

Examples:
    >>> # Add a new setting to the registry
    >>> SETTINGS["new_setting"] = SettingSpec(
    ...     key="new_setting",
    ...     kind="scalar",
    ...     value_type=str,
    ...     actions={"set"},
    ...     default="default_value",
    ...     help="Description of the setting"
    ... )

    >>> # Apply an action
    >>> cfg = get_config()
    >>> cfg = apply_action(cfg, "video_player", "set", ["mpv"])
    Set video_player to 'mpv'.

    >>> # Add to list setting
    >>> cfg = apply_action(cfg, "search_paths", "add", ["/media/movies"])
    Added '/media/movies' to search_paths.
"""

from __future__ import annotations

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


def _rebuild_cache_if_enabled():
    # Helper function with lazy imports to avoid circular import
    from .cache import rebuild_library_cache
    from .config import get_config

    if get_config()["cache_library"]:
        rebuild_library_cache()


def _validate_search_paths_overlap(search_paths: list[str]):
    from .validation import validate_search_paths_overlap

    validate_search_paths_overlap(search_paths)


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
        allowed_values: Allowed values to choose from.
        normalize: Function converting a raw string into what is written to TOML.
        from_toml: Function converting value from TOML to the typed value.
        display: Function producing a human readable representation.
        validate_all: Function validating the final state before changes are applied.
            Called with the complete value (scalar or list) that will be set. Should
            raise an exception if validation fails, preventing the change.
        after_update: Hook to trigger additional action(s) after an update.
        help: Human readable help text shown to the user.
    """

    key: str
    kind: Literal["scalar", "list"]
    value_type: type
    actions: set[Action]
    default: Any
    allowed_values: list[Any] | None = None
    normalize: Callable[[str], Any] = lambda value: value
    from_toml: Callable[[Any], Any] = lambda value: value
    display: Callable[[Any], str] = lambda value: str(value)
    validate_all: Callable[[Any], None] = lambda value: None
    after_update: Callable[[Any], None] = lambda value: None
    help: str = ""


SETTINGS: dict[str, SettingSpec] = {
    "search_paths": SettingSpec(
        key="search_paths",
        kind="list",
        value_type=str,
        actions={"set", "add", "remove", "clear"},
        normalize=normalize_path,
        from_toml=lambda path: Path(path).resolve(),
        default=[],
        validate_all=_validate_search_paths_overlap,
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
        help="Filter results by media_extensions.",
    ),
    "fullscreen_playback": SettingSpec(
        key="fullscreen_playback",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        default=True,
        display=normalize_bool_to_toml,
        help="Play files in fullscreen mode.",
    ),
    "prefer_fd": SettingSpec(
        key="prefer_fd",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        default=True,
        display=normalize_bool_to_toml,
        help="Use fd for file searches where possible.",
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
        help="Cache library metadata locally.",
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
            "cache_library is set to true, in seconds. Set to 0 to turn off automatic "
            "cache rebuilding. Default value of 86400 s is 1 day."
        ),
    ),
    "auto_wildcards": SettingSpec(
        key="auto_wildcards",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        default=True,
        display=normalize_bool_to_toml,
        help=(
            "Automatically wrap search patterns with '*' if they don't contain "
            "any wildcards (* ? [ ]). 'batman' becomes '*batman*'."
        ),
    ),
    "parallel_search": SettingSpec(
        key="parallel_search",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        default=True,
        display=normalize_bool_to_toml,
        help=(
            "Parallelize file searches over search paths. Turn off if search paths are "
            "located on the same mechanical drive (but leave on for SSD/NVME)."
        ),
    ),
    "display_paths": SettingSpec(
        key="display_paths",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        default=True,
        display=normalize_bool_to_toml,
        help="Display file paths in search results.",
    ),
    "video_player": SettingSpec(
        key="video_player",
        kind="scalar",
        value_type=str,
        actions={"set"},
        normalize=lambda s: s.lower().strip(),
        default="auto",
        allowed_values=["auto", "vlc", "mpv"],
        help=(
            "Video player to use. 'vlc', 'mpv', or 'auto'. If 'auto', uses VLC with "
            "fallback to mpv. Note that video player(s) must be installed separately."
        ),
    ),
}


def validate_allowed_value(value: Any, spec: SettingSpec) -> None:
    """Validate a single value against allowed_values list.

    Raises:
        typer.Exit: If value is not in allowed_values.
    """
    if spec.allowed_values is None:
        return

    if value not in spec.allowed_values:
        allowed_str = ", ".join(
            repr(allowed_value) for allowed_value in spec.allowed_values
        )
        print_and_raise(
            f"Invalid value {value!r} for {spec.key}. Allowed values: {allowed_str}."
        )


def _apply_action(
    cfg: TOMLDocument, key: str, action: Action, values: list[str] | None
) -> None:
    """Apply action to setting.

    Modifies the configuration in-place.

    Args:
        cfg (TOMLDocument): Current configuration to modify.
        key (str): Setting to apply action to.
        action (Action): Action to perform.
        values (list[str] | None): Values to act with.
    """
    if key not in SETTINGS:
        print_and_raise(
            f"Unknown configuration key: {key}. Available keys: {list(SETTINGS)}"
        )

    spec = SETTINGS[key]

    if action not in spec.actions:
        print_and_raise(f"Action {action} not supported for {key}.")

    if spec.kind == "scalar" and action == "set":
        if values is None or len(values) > 1:
            print_and_raise(
                f"Scalar setting {key} requires a single value for set, got: {values}."
            )

        new_value = spec.normalize(values[0])
        validate_allowed_value(new_value, spec)
        spec.validate_all(new_value)
        cfg[key] = new_value
        spec.after_update(cfg[key])
        print_ok(f"Set {key} to '{spec.display(new_value)}'.")
        return

    # List setting
    if action == "clear":
        cfg[key].clear()  # type: ignore [union-attr]
        print_ok(f"Cleared {key}.")
        return

    if values is None:
        print_and_raise(f"Action '{action}' requires values for '{key}'.")

    normalized_values = [spec.normalize(value) for value in values]

    if action in ["set", "add"]:
        for value in normalized_values:
            validate_allowed_value(value, spec)

    if action == "set":
        # Validate final state before making changes
        spec.validate_all(normalized_values)
        cfg[key].clear()  # type: ignore [union-attr]
        cfg[key].extend(normalized_values)  # type: ignore [union-attr]
        print_ok(f"Set {key} to {normalized_values}.")
        spec.after_update(cfg[key])

    elif action == "add":
        # Build hypothetical final state and validate before making changes
        final_state = list(cfg[key])  # type: ignore [arg-type]
        for value in normalized_values:
            if value not in final_state:
                final_state.append(value)
        spec.validate_all(final_state)

        # Now actually add the values
        for value in normalized_values:
            if value not in cfg[key]:  # type: ignore [operator]
                cfg[key].append(value)  # type: ignore [operator, union-attr, call-arg]
                print_ok(f"Added '{value}' to {key}.")
            else:
                print_warn(f"{key} already contains '{value}', skipping.")
        spec.after_update(cfg[key])

    elif action == "remove":
        # Build hypothetical final state and validate before making changes
        final_state = [v for v in cfg[key] if v not in normalized_values]  # type: ignore [union-attr]
        spec.validate_all(final_state)

        # Now actually remove the values
        for value in normalized_values:
            if value in cfg[key]:  # type: ignore [operator]
                cfg[key].remove(value)  # type: ignore [union-attr]
                print_ok(f"Removed '{value}' from {key}.")
            else:
                print_warn(f"'{value}' not found in {key}, skipping.")
        spec.after_update(cfg[key])


def apply_action(key: str, action: Action, values: list[str] | None):
    """Apply action to setting and write the updated configuration to disk.

    Args:
        key (str): Setting to apply action to.
        action (Action): Action to perform.
        values (list[str] | None): Values to act with. None if action is "clear".
    """
    from .config import get_config, write_config

    cfg = get_config()
    _apply_action(cfg, key, action, values)
    write_config(cfg)
