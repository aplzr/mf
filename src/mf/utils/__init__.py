"""mf utility functions."""

from .cache_utils import (
    get_file_by_index,
    get_library_cache_file,
    get_search_cache_file,
    load_search_results,
    print_search_results,
    rebuild_library_cache,
    save_search_results,
)
from .config_utils import (
    get_config_file,
    get_media_extensions,
    get_validated_search_paths,
    parse_timedelta_str,
    read_config,
    write_config,
    write_default_config,
)
from .console import console, print_error, print_ok, print_warn
from .editor_utils import start_editor
from .generate_dummy_media import generate_dummy_media
from .normalizers import (
    normalize_bool_str,
    normalize_bool_to_toml,
    normalize_media_extension,
    normalize_path,
    normalize_pattern,
    normalize_timedelta_str,
)
from .scan_utils import (
    filter_scan_results,
    find_media_files,
    get_fd_binary,
    scan_path_with_fd,
    scan_path_with_python,
)
from .settings_registry import apply_action, default_cfg

__all__ = [
    "apply_action",
    "console",
    "default_cfg",
    "filter_scan_results",
    "find_media_files",
    "generate_dummy_media",
    "get_config_file",
    "get_fd_binary",
    "get_file_by_index",
    "get_library_cache_file",
    "get_media_extensions",
    "get_search_cache_file",
    "get_validated_search_paths",
    "parse_timedelta_str",
    "load_search_results",
    "normalize_bool_str",
    "normalize_bool_to_toml",
    "normalize_media_extension",
    "normalize_path",
    "normalize_pattern",
    "normalize_timedelta_str",
    "print_error",
    "print_ok",
    "print_search_results",
    "print_warn",
    "read_config",
    "rebuild_library_cache",
    "save_search_results",
    "scan_path_with_fd",
    "scan_path_with_python",
    "start_editor",
    "write_config",
    "write_default_config",
]
