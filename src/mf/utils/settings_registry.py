from dataclasses import dataclass
from typing import Any, Callable, Literal

from tomlkit import TOMLDocument

from .config_utils import (
    normalize_bool_str,
    normalize_media_extension,
    normalize_path,
)
from .console import print_error, print_ok, print_warn

Action = Literal["set", "add", "remove", "clear"]


@dataclass
class SettingSpec:
    key: str
    kind: Literal["scalar", "list"]
    value_type: type
    actions: set[Action]
    normalize: Callable[[str], Any]
    display: Callable[[Any], str] = lambda value: str(value)
    validate_all: Callable[[Any], None] = lambda value: None
    help: str = ""
    before_write: Callable[[Any], any] = lambda value: value


REGISTRY: dict[str, SettingSpec] = {
    "search_paths": SettingSpec(
        key="search_paths",
        kind="list",
        value_type=str,
        actions={"set", "add", "remove", "clear"},
        normalize=normalize_path,
        help="Directories scanned for media files.",
    ),
    "media_extensions": SettingSpec(
        key="media_extensions",
        kind="list",
        value_type=str,
        actions={"set", "add", "remove", "clear"},
        normalize=normalize_media_extension,
        help="Allowed media file extensions.",
    ),
    "match_extensions": SettingSpec(
        key="match_extensions",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        help="If true, filter results by media_extensions.",
    ),
    "fullscreen_playback": SettingSpec(
        key="fullscreen_playback",
        kind="scalar",
        value_type=bool,
        actions={"set"},
        normalize=normalize_bool_str,
        help="If true, files are played in fullscreen mode.",
    ),
}


def apply_action(
    cfg: TOMLDocument, key: str, action: Action, raw_values: list[str] | None
):
    spec = REGISTRY[key]

    if action not in spec.actions:
        print_error(f"Action {action} not supported for {key}.")

    if spec.kind == "scalar":
        if action == "set":
            if raw_values is None or len(raw_values) > 1:
                print_error(
                    f"Scalar setting {key} requires "
                    f"a single value for set, got: {raw_values}."
                )

        new_value = spec.normalize(raw_values[0])
        spec.validate_all(new_value)
        cfg[key] = spec.before_write(new_value)

        print_ok(
            f"{key}: set to {str(new_value).lower() if new_value in [True, False] else new_value}."
        )

        return cfg

    # List setting
    if action == "clear":
        cfg[key].clear()
        print_ok(f"Cleared '{key}'.")
        return cfg

    normalized_values = [spec.normalize(value) for value in raw_values]

    if action == "set":
        cfg[key].clear()
        cfg[key].extend(normalized_values)
        print_ok(f"{key}: set {normalized_values}.")

    elif action == "add":
        for value in normalized_values:
            if value not in cfg[key]:
                cfg[key].append(value)
                print_ok(f"{key}: added '{value}'.")
            else:
                print_warn(f"{key}: already contains '{value}', skipping.")

    elif action == "remove":
        for value in normalized_values:
            if value in cfg[key]:
                cfg[key].remove(value)
                print_ok(f"{key}: removed '{value}'.")
            else:
                print_warn(f"{key}: '{value}' not found, skipping.")

    spec.validate_all(cfg[key])

    return cfg
