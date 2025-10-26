import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fnmatch import translate
from functools import partial
from pathlib import Path

import tomlkit
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from tomlkit import TOMLDocument

# The console instance used for print output throughout the package
console = Console()


def get_cache_file() -> Path:
    """Get the cache file following platform conventions if available, fall back to
    ~/.cache/mf/last_search.json otherwise.

    Returns:
        Path: Path to the cache file.
    """
    cache_dir = Path(
        os.environ.get(
            "LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME",
            Path.home() / ".cache",
        ),
    )

    cache_dir = cache_dir / "mf"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "last_search.json"


def get_config_file() -> Path:
    """Get the config file following platform conventions if available, fall back to
    ~/.config/mf/config.toml otherwise.

    Returns:
        Path: Path to the config file.
    """
    # Use localappdata instead of roaming on windows because the
    # configuration is device-specific
    config_dir = Path(
        os.environ.get(
            "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME",
            Path.home() / ".config",
        )
    )

    config_dir = config_dir / "mf"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.toml"


def save_search_results(pattern: str, results: list[tuple[int, Path]]) -> None:
    """Save search results to cache file.

    Args:
        pattern (str): The search pattern used.
        results (list[tuple[int, Path]]): List of (index, file_path) tuples.
    """
    cache_data = {
        "pattern": pattern,
        "timestamp": datetime.now().isoformat(),
        "results": [
            {"index": idx, "path": str(file_path)} for idx, file_path in results
        ],
    }

    cache_file = get_cache_file()

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)


def load_search_results() -> tuple[str, list[tuple[int, Path]], datetime]:
    """Load the last search results from cache.

    Raises:
        typer.Exit: Cache empty or doesn't exist.

    Returns:
        tuple[str, list[tuple[int, Path]], datetime]: Pattern, results, timestamp, where
            results is a list of (index, file_path) tuples.
    """
    cache_file = get_cache_file()

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

        pattern = cache_data["pattern"]
        results = [
            (item["index"], Path(item["path"])) for item in cache_data["results"]
        ]
        timestamp = datetime.fromisoformat(cache_data["timestamp"])

        return pattern, results, timestamp
    except (json.JSONDecodeError, KeyError, FileNotFoundError):
        console.print(
            (
                "❌ Cache is empty or doesn't exist. "
                "Please run 'mf list <pattern>' or 'mf new' first."
            ),
            style="red",
        )
        raise typer.Exit(1)


def print_search_results(title: str, results: list[tuple[int, Path]]):
    """Print results of a search.

    Args:
        title (str): Panel title.
        results (list[tuple[int, Path]]): A list of (index, Path) tuples.
    """
    # Create rich table
    # Calculate width for index column based on largest index
    max_index_width = len(str(len(results))) if results else 1

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("#", style="cyan", width=max_index_width, justify="right")
    table.add_column("File", style="green", overflow="fold")
    table.add_column("Location", style="blue", overflow="fold")

    for idx, path in results:
        table.add_row(str(idx), path.name, str(path.parent))

    # Wrap in panel with title on the left and vertical padding
    panel = Panel(
        table, title=f"[bold]{title}[/bold]", title_align="left", padding=(1, 1)
    )
    console.print()
    console.print(panel)


def normalize_pattern(pattern: str) -> str:
    """Add wildcards if pattern doesn't contain glob characters.

    Args:
        pattern: The search pattern to normalize.

    Returns:
        The normalized pattern with wildcards added if needed.
    """
    if not any(char in pattern for char in ["*", "?", "[", "]"]):
        return f"*{pattern}*"

    return pattern


def scan_path(search_path: Path, pattern_regex: re.Pattern) -> list[Path]:
    """Scan a single path for media files.

    Args:
        search_path (Path): The directory path to scan for media files.
        pattern_regex (re.Pattern): Compiled regex pattern for matching filenames.

    Returns:
        list[Path]: All media files found in the directory tree.
    """
    results = []
    match_extensions = read_config()["match_extensions"]
    media_extensions = read_config()["media_extensions"]

    if not search_path.exists():
        console.print(
            f"⚠  Search path '{search_path}' does not exist, skipping.", style="yellow"
        )
        return results

    # Use os.scandir for better performance with cached stat info
    def scan_dir(path):
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file(follow_symlinks=False):
                        if match_extensions:
                            # Check extension first (cheapest check)
                            if Path(entry.name).suffix.lower() in media_extensions:
                                # Then check pattern match
                                if pattern_regex.match(entry.name.lower()):
                                    results.append(Path(entry.path))
                        else:
                            # Only check pattern match
                            if pattern_regex.match(entry.name.lower()):
                                results.append(Path(entry.path))
                    elif entry.is_dir(follow_symlinks=False):
                        scan_dir(entry.path)
        except PermissionError:
            console.print(
                f"❌ Missing access rights for search path '{path}.'", style="red"
            )
            raise typer.Exit(1)

    scan_dir(str(search_path))
    return results


def find_media_files(pattern: str) -> list[tuple[int, Path]]:
    """Search for media files matching the pattern.

    Scans all configured search paths in parallel and filters results
    by the given glob pattern.

    Args:
        pattern (str): Glob-based search pattern to match filenames against.

    Returns:
        list[tuple[int, Path]]: (index, path) tuples for each matching file, where index
            is a 1-based sequential number.
    """
    match_extensions = read_config()["match_extensions"]
    media_extensions = read_config()["media_extensions"]

    if match_extensions and not media_extensions:
        console.print(
            (
                "❌  match_extensions is set to true, but media_extensions is "
                "empty. Set list of allowed media extensions with 'mf config set "
                "media_extensions'."
            ),
            style="red",
        )
        raise typer.Exit(1)

    search_paths = get_search_paths()

    # Pre-compile pattern to regex for faster matching
    pattern_regex = re.compile(translate(pattern), re.IGNORECASE)

    # Scan all paths in parallel
    with ThreadPoolExecutor(max_workers=len(search_paths)) as executor:
        scan_with_pattern = partial(scan_path, pattern_regex=pattern_regex)
        path_results = executor.map(scan_with_pattern, search_paths)

    # Flatten results, sort by filename (case-insensitive), add index
    all_files = []

    for files in path_results:
        all_files.extend(files)

    all_files.sort(key=lambda path: path.name.lower())
    results = [(idx, path) for idx, path in enumerate(all_files, start=1)]

    return results


def get_file_by_index(index: int) -> Path:
    """Get a file path from the cache.

    Args:
        index (int): Index of the requested file.

    Raises:
        typer.Exit: Invalid index.
        typer.Exit: File doesn't exist anymore.

    Returns:
        Path: Path of the requested file.
    """

    pattern, results, _ = load_search_results()
    file = None

    for idx, path in results:
        if idx == index:
            file = path
            break

    if file is None:
        console.print(
            f"Index {index} not found in last search results (pattern: '{pattern}')",
            style="red",
        )
        console.print(f"Valid indices: 1-{len(results)}", style="yellow")
        raise typer.Exit(1)

    if not file.exists():
        console.print(f"[red]File no longer exists:[/red] {file}")
        raise typer.Exit(1)

    return file


def start_editor(file: Path):
    """Edit file in editor.

    Tries to edit file in default editor if there is one, otherwise tries
    platform-specific editors that are usually available.

    Args:
        file (Path): File to edit.
    """
    # Try defaults first
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")

    if editor:
        subprocess.run([editor, str(file)])
    # Windows: try np++, fall back to np
    elif os.name == "nt":
        if shutil.which("notepad++"):
            subprocess.run(["notepad++", str(file)])
        else:
            subprocess.run(["notepad", str(file)])
    # Linux/macOS
    else:
        for ed in ["nano", "vim", "vi"]:
            if shutil.which(ed):
                subprocess.run([ed, str(file)])
                break
        else:
            console.print(f"No editor found. Edit manually: {file}")


def write_default_config() -> TOMLDocument:
    """Write configuration with default settings.

    Returns:
        TOMLDocument: The default configuration as written to disk.
    """
    # fmt: off
    default_cfg = tomlkit.document()

    # Media file search paths
    default_cfg.add(tomlkit.comment("Media file search paths"))
    default_cfg.add("search_paths", [])
    default_cfg.add(tomlkit.nl())

    # Media file extensions
    default_cfg.add(tomlkit.comment("Media file extensions matched by 'mf find' and 'mf new'."))
    default_cfg.add("media_extensions", ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'])
    default_cfg.add(tomlkit.nl())

    # Match extensions setting
    default_cfg.add(tomlkit.comment("If true, 'mf find' and 'mf new' will only return results that match one of the file extensions"))
    default_cfg.add(tomlkit.comment("defined by media_extensions. Otherwise all files found in the search paths will be returned."))
    default_cfg.add(tomlkit.comment("Set to false if your search paths only contain media files and you don't want to manage media"))
    default_cfg.add(tomlkit.comment("extensions."))
    default_cfg.add("match_extensions", True)
    default_cfg.add(tomlkit.nl())

    # Player setting
    default_cfg.add(tomlkit.comment("This is the player that is used by mf play"))
    default_cfg.add("player", "vlc")
    # fmt: on

    write_config(default_cfg)
    console.print(
        f"✔  Written default configuration to '{get_config_file()}'.", style="green"
    )

    return default_cfg


def read_config() -> TOMLDocument:
    """Load the configuration file from disk.

    If the configuration file doesn't exist, write the default configuration, then
    return that.

    Returns:
        TOMLDocument: Loaded configuration.
    """
    try:
        with open(get_config_file()) as f:
            cfg = tomlkit.load(f)
    except FileNotFoundError:
        console.print(
            "⚠  Configuration file doesn't exist, creating it with default settings.",
            style="yellow",
        )
        cfg = write_default_config()

    return cfg


def write_config(cfg: TOMLDocument):
    """Write (updated) configuration back to disk.

    Args:
        cfg (dict): Configuration to write.
    """
    with open(get_config_file(), "w") as f:
        tomlkit.dump(cfg, f)


def get_search_paths() -> list[Path]:
    """Get search paths from the configuration file.

    Validates paths by checking if they exist. Paths that don't are removed from the
    returned list.

    Raises:
        typer.Exit: List empty or entries don't exist.

    Returns:
        list[Path]: Validated search paths.
    """
    search_paths = read_config()["search_paths"]
    validated_paths: list[Path] = []

    for search_path in search_paths:
        path = Path(search_path)

        if not path.exists():
            console.print(
                f"⚠  Configured search path {search_path} does not exist.",
                style="yellow",
            )
        else:
            validated_paths.append(path)

    if not validated_paths:
        console.print(
            "❌ List of search paths is empty or paths don't exist. "
            "Set search paths with 'mf config set search_paths'.",
            style="red",
        )
        raise typer.Exit(1)
    else:
        return validated_paths


def normalize_path(path_str: str) -> str:
    """Make paths consistent by resolving to full paths and returning a posix-style
    string representation (forward slashes).

    Args:
        path_str (str): Path to normalize.

    Returns:
        str: Normalized path.
    """
    return Path(path_str).resolve().as_posix()


def add_search_path(cfg: TOMLDocument, path_str: str) -> TOMLDocument:
    """Add search path to configuration.

    Skips if path is already in the configuration, warns if path does not exist but
    stores anyway.

    Args:
        cfg (TOMLDocument): Current configuration.
        path_str (str): Search path to add.

    Returns:
        TOMLDocument: Updated configuration.
    """
    path_str = normalize_path(path_str)

    if path_str not in cfg["search_paths"]:
        if not Path(path_str).exists():
            console.print(
                f"⚠  Path '{path_str}' does not exist (storing anyway).", style="yellow"
            )
        cfg["search_paths"].append(path_str)
        console.print(f"✔  Added search path: '{path_str}'", style="green")
    else:
        console.print(
            (
                f"⚠  Search path '{path_str}' already stored "
                "in configuration file, skipping."
            ),
            style="yellow",
        )

    return cfg


def remove_search_path(cfg: TOMLDocument, path_str: str) -> TOMLDocument:
    """Remove search path from configuration.

    Args:
        cfg (TOMLDocument): Current configuration.
        path_str (str): Search path to remove.

    Returns:
        TOMLDocument: Updated configuration.
    """
    path_str = normalize_path(path_str)

    try:
        cfg["search_paths"].remove(path_str)
        console.print(f"✔  Removed search path: '{path_str}'", style="green")
        return cfg
    except ValueError:
        console.print(
            f"❌ Path '{path_str}' not found in configuration file.", style="red"
        )
        raise typer.Exit(1)


def get_media_extensions() -> list[str]:
    """The media extensions from the configuration file."""
    # TODOs
    # - [ ] Validate extensions
    # - [ ] Handle empty list
    return list(read_config()["media_extensions"])


def normalize_media_extension(extension: str) -> str:
    """Normalize media extensions.

    Args:
        extension (str): Extension to normalize.

    Raises:
        typer.Exit: Extension empty after normalization.

    Returns:
        str: Normalized extension (lowercase with a single leading dot, no whitespace).
    """
    if not extension:
        raise ValueError("Extension can't be empty.")

    extension = extension.lower().strip().lstrip(".")

    if not extension:
        console.print("❌ Extension can't be empty after normalization.")
        raise typer.Exit(1)

    return "." + extension


def add_media_extension(cfg: TOMLDocument, extension: str) -> TOMLDocument:
    """Add media extension to the configuration.

    Args:
        cfg (TOMLDocument): Current configuration.
        extension (str): Extension to add.

    Returns:
        TOMLDocument: Updated configuration.
    """
    if extension not in cfg["media_extensions"]:
        extension = normalize_media_extension(extension)
        cfg["media_extensions"].append(extension)
        console.print(f"✔  Added media extension '{extension}'.", style="green")
    else:
        console.print(
            f"⚠  Extension '{extension}' already stored in configuration, skipping.",
            style="yellow",
        )

    return cfg


def remove_media_extension(cfg: TOMLDocument, extension: str) -> TOMLDocument:
    """Remove media extension from configuration.

    Args:
        cfg (TOMLDocument): Current configuration.
        extension (str): Extension to remove.

    Raises:
        typer.Exit: Extension not found in configuration.

    Returns:
        TOMLDocument: Updated configuration.
    """
    extension = normalize_media_extension(extension)

    if extension in cfg["media_extensions"]:
        cfg["media_extensions"].remove(extension)
        console.print(
            f"✔  Extension '{extension}' removed from configuration.", style="yellow"
        )
        return cfg
    else:
        console.print(
            f"❌ Extension '{extension}' not found in configuration.", style="red"
        )
        raise typer.Exit(1)


def normalize_bool_str(bool_str: str) -> str:
    bool_str = bool_str.strip().lower()

    TRUE_VALUES = {"1", "true", "yes", "y", "on", "enable", "enabled"}
    FALSE_VALUES = {"0", "false", "no", "n", "off", "disable", "disabled"}

    if bool_str in TRUE_VALUES:
        return "true"
    elif bool_str in FALSE_VALUES:
        return "false"
    else:
        console.print(
            f"❌  Invalid boolean value. Got: '{bool_str}'. Expected one of:",
            ", ".join(repr(item) for item in sorted(TRUE_VALUES | FALSE_VALUES)),
            style="red",
        )
        raise typer.Exit(1)
