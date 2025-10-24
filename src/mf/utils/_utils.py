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
from socket import gethostname

import tomlkit
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..params import MEDIA_EXTENSIONS, SEARCH_PATHS_BY_HOSTNAME

# The console instance used for print output throughout the package
console = Console()

search_paths = SEARCH_PATHS_BY_HOSTNAME[gethostname()]


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
            "Cache is empty or doesn't exist. Please run 'mf list <pattern>' first.",
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

    if not search_path.exists():
        return results

    # Use os.scandir for better performance with cached stat info
    def scan_dir(path):
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file(follow_symlinks=False):
                        # Check extension first (cheapest check)
                        if Path(entry.name).suffix.lower() in MEDIA_EXTENSIONS:
                            # Then check pattern match
                            if pattern_regex.match(entry.name.lower()):
                                results.append(Path(entry.path))
                    elif entry.is_dir(follow_symlinks=False):
                        scan_dir(entry.path)
        except PermissionError:
            pass  # Skip directories we can't access

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


def read_config() -> dict:
    """Load the configuration file from disk.

    Returns:
        dict: Loaded connfiguration.
    """
    with open(get_config_file()) as f:
        return tomlkit.load(f)


def write_config(cfg: dict):
    """Write (updated) configuration back to disk.

    Args:
        cfg (dict): Configuration to write.
    """
    with open(get_config_file(), "w") as f:
        tomlkit.dump(cfg, f)
