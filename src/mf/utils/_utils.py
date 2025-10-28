import json
import os
import platform
import shutil
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fnmatch import fnmatch
from functools import partial
from importlib.resources import files
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
                "Please run 'mf find <pattern>' or 'mf new' first."
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


def get_validated_search_paths() -> list[Path]:
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


def get_media_extensions() -> set[str]:
    """Get the list of media extensions from the configuration file.

    Returns:
        set[str]: Configured media extensions.
    """
    return {
        normalize_media_extension(extension)
        for extension in read_config()["media_extensions"]
    }


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
        console.print("❌ Extension can't be empty after normalization.", style="red")
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
    normalized_ext = normalize_media_extension(extension)

    if normalized_ext not in cfg["media_extensions"]:
        cfg["media_extensions"].append(normalized_ext)
        console.print(f"✔  Added media extension '{normalized_ext}'.", style="green")
    else:
        console.print(
            f"⚠  Extension '{normalized_ext}' already stored in configuration, skipping.",
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
            f"✔  Extension '{extension}' removed from configuration.", style="green"
        )
        return cfg
    else:
        console.print(
            f"❌ Extension '{extension}' not found in configuration.", style="red"
        )
        raise typer.Exit(1)


def normalize_bool_str(bool_str: str) -> bool:
    """Normalize bool string.

    Args:
        bool_str (str): String representing a boolean value.

    Raises:
        typer.Exit: Invalid value.

    Returns:
        bool: True or False.
    """
    bool_str = bool_str.strip().lower()

    TRUE_VALUES = {"1", "true", "yes", "y", "on", "enable", "enabled"}
    FALSE_VALUES = {"0", "false", "no", "n", "off", "disable", "disabled"}

    if bool_str in TRUE_VALUES:
        return True
    elif bool_str in FALSE_VALUES:
        return False
    else:
        console.print(
            f"❌  Invalid boolean value. Got: '{bool_str}'. Expected one of:",
            ", ".join(repr(item) for item in sorted(TRUE_VALUES | FALSE_VALUES)),
            style="red",
        )
        raise typer.Exit(1)


def get_fd_binary() -> Path:
    """Get the path to the appropriate fd binary for the current platform.

    Raises:
        RuntimeError: Unsupported platform.

    Returns:
        Path: fd binary.
    """
    # NOTE: Exceptions caused by this are handled by the calling find_media_files, which
    # will fall back to the python scanner
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        binary_name = "fd-v10_3_0-x86_64-unknown-linux-gnu"
    elif system == "darwin":
        if machine == "arm64":
            binary_name = "fd-v10_3_0-aarch64-apple-darwin"
        else:
            binary_name = "fd-v10_3_0-x86_64-apple-darwin"
    elif system == "windows":
        binary_name = "fd-v10_3_0-x86_64-pc-windows-msvc.exe"
    else:
        raise RuntimeError(f"Unsupported platform: {system}-{machine}")

    # Get binary resource path and convert to actual Path (needed for subprocess)
    bin_path = files("mf").joinpath("bin", binary_name)
    bin_path = Path(str(bin_path))

    # Make executable on Unix systems
    if system in ("linux", "darwin"):
        current_perms = bin_path.stat().st_mode
        if not (current_perms & stat.S_IXUSR):
            bin_path.chmod(current_perms | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return bin_path


def scan_path_with_python(
    search_path: Path,
    pattern: str,
    media_extensions: set[str],
    match_extensions: bool,
    include_mtime: bool = False,
) -> list[Path] | list[tuple[Path, float]]:
    """Scan a single path for media files.

    Slower compared to the fd scanner for regular file searches, but can optionally
    provide mtime information (and can do it faster than fd scanner + mtime lookup).

    Args:
        search_path (Path): The directory path to scan for media files.
        pattern (str): Glob pattern for matching filenames.
        media_extensions (set[str]): The set of allowed media file extensions.
        match_extensions (bool): Whether search results should be matched against
            media_extensions or not.
        include_mtime (bool, optional): Additionally look up and return mtime for each
            entry. Defaults to False.

    Returns:
        list[Path] | list[tuple[Path, float]]: All (media) files found in the directory
            tree. If include_mtime, additionally the last modified time of each entry.
    """
    results = []

    # Use os.scandir for better performance with cached stat info
    def scan_dir(path):
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file(follow_symlinks=False):
                        if match_extensions and media_extensions:
                            # Check extension first (cheapest check)
                            if Path(entry.name).suffix.lower() in media_extensions:
                                # Then check pattern match
                                if fnmatch(entry.name.lower(), pattern.lower()):
                                    if include_mtime:
                                        # Cached on Windows (if it's not a symlink),
                                        # additional syscall on Linux
                                        mtime = entry.stat().st_mtime
                                        results.append((Path(entry.path), mtime))
                                    else:
                                        results.append(Path(entry.path))
                        else:
                            # Only check pattern match
                            if fnmatch(entry.name.lower(), pattern.lower()):
                                if include_mtime:
                                    mtime = entry.stat().st_mtime
                                    results.append((Path(entry), mtime))
                                else:
                                    results.append(Path(entry.path))
                    elif entry.is_dir(follow_symlinks=False):
                        scan_dir(entry.path)
        except PermissionError:
            console.print(
                f"⚠  Missing access permissions for directory {path}, skipping.",
                style="yellow",
            )

    scan_dir(str(search_path))
    return results


def scan_path_with_fd(
    search_path: Path,
    pattern: str,
    media_extensions: set[str],
    match_extensions: bool,
) -> list[Path]:
    """Scan a single path using fd for better performance.

    Args:
        search_path (Path): The directory path to scan for media files.
        pattern (str): Glob pattern for matching filenames.
        media_extensions (set[str]): The set of allowed media file extensions.
        match_extensions (bool): Whether to filter by media extensions.

    Returns:
        list[Path]: All matching files found in the directory tree.
    """
    # Build fd command
    cmd = [
        str(get_fd_binary()),
        "--glob",
        "--type",
        "f",  # files only
        "--absolute-path",
        "--hidden",
        pattern,
        str(search_path),
    ]

    # Add extension filters if needed
    if match_extensions and media_extensions:
        for ext in media_extensions:
            # Remove leading dot if present and add extension filter
            cmd.extend(["-e", ext.lstrip(".")])

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    # Parse output into Path objects
    files = []

    for line in result.stdout.strip().split("\n"):
        if line:  # Skip empty lines
            files.append(Path(line))

    return files


def find_media_files(
    pattern: str, *, sort_by_mtime: bool = False, prefer_fd: bool = True
) -> list[tuple[int, Path]]:
    """Unified media file search with configurable sorting and scanner preference.

    Args:
        pattern (str): Glob pattern to match filenames against.
        sort_by_mtime (bool, optional): If True, sorts results by last modified time.
            Forces use of the python scanner. Defaults to False.
        prefer_fd (bool, optional): Prefer external fd binary for faster file scanning
            if possible, else use the python scanner. Defaults to True.

    Returns:
        list[tuple[int, Path]]: List of indexed search results.
    """

    # Get and validate config
    search_paths = get_validated_search_paths()
    match_extensions = read_config()["match_extensions"]
    media_extensions = get_media_extensions()

    # Determine which scanner to use
    use_fd = prefer_fd and not sort_by_mtime  # fd can't provide mtime

    # Parallel scanning over search paths
    with ThreadPoolExecutor(max_workers=len(search_paths)) as executor:
        if use_fd:
            try:
                scanner = partial(
                    scan_path_with_fd,
                    pattern=pattern,
                    media_extensions=media_extensions,
                    match_extensions=match_extensions,
                )
                path_results = executor.map(scanner, search_paths)
            except (
                FileNotFoundError,
                subprocess.CalledProcessError,
                OSError,
                PermissionError,
            ):
                # Fallback to python scanner
                scanner = partial(
                    scan_path_with_python,
                    pattern=pattern,
                    media_extensions=media_extensions,
                    match_extensions=match_extensions,
                    include_mtime=False,
                )
                path_results = executor.map(scanner, search_paths)
        else:
            # Use python scanner for mtime
            scanner = partial(
                scan_path_with_python,
                pattern=pattern,
                media_extensions=media_extensions,
                match_extensions=match_extensions,
                include_mtime=sort_by_mtime,
            )
            path_results = executor.map(scanner, search_paths)

    # Flatten results
    all_results = []
    for results in path_results:
        all_results.extend(results)

    # Sort and index based on what we got back
    if sort_by_mtime:
        # all_results contains [(Path, mtime), ...] tuples
        # Sort by mtime (newest first), add index, remove mtime
        all_results.sort(key=lambda item: item[1], reverse=True)
        indexed_results = [
            (idx, path) for idx, (path, mtime) in enumerate(all_results, start=1)
        ]
    else:
        # all_results contains [Path, Path, ...] objects
        # Sort alphabetically, add index
        all_results.sort(key=lambda path: path.name.lower())
        indexed_results = [(idx, path) for idx, path in enumerate(all_results, start=1)]

    return indexed_results
