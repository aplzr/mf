import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fnmatch import translate
from functools import partial
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Media file finder and player")
console = Console()

# Configure your search paths here
SEARCH_PATHS = [
    Path("//doorstep/bitheap-incoming"),
    Path("//doorstep/bitpile-incoming"),
]

# Configure supported media extensions
MEDIA_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
}


# Cross-platform cache file location
def get_cache_file() -> Path:
    """Get the cache file path following platform best practices.

    Returns:
        Path to the cache file in the appropriate user directory.
    """
    if os.name == "nt":  # Windows
        cache_dir = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:  # Unix-like (Linux, macOS)
        cache_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

    cache_dir = cache_dir / "mf"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "last_search.json"


def save_search_results(pattern: str, results: list[tuple[int, Path]]) -> None:
    """Save search results to cache file.

    Args:
        pattern: The search pattern used.
        results: List of (index, file_path) tuples.
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


def load_search_results() -> tuple[str, list[tuple[int, Path]]] | None:
    """Load the last search results from cache.

    Returns:
        A tuple of (pattern, results) if cache exists, None otherwise.
    """
    cache_file = get_cache_file()

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

        pattern = cache_data["pattern"]
        results = [
            (item["index"], Path(item["path"])) for item in cache_data["results"]
        ]

        return pattern, results
    except (json.JSONDecodeError, KeyError, FileNotFoundError):
        return None


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
        search_path: The directory path to scan for media files.
        pattern_regex: Compiled regex pattern for matching filenames.

    Returns:
        A list of Path objects for all media files found in the directory tree.
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
        pattern: Glob-based search pattern to match filenames against.

    Returns:
        A list of tuples containing (index, file_path) for each matching file,
        where index is a 1-based sequential number.
    """
    normalized_pattern = normalize_pattern(pattern)

    # Pre-compile pattern to regex for faster matching
    pattern_regex = re.compile(translate(normalized_pattern), re.IGNORECASE)

    # Scan all paths in parallel
    with ThreadPoolExecutor(max_workers=len(SEARCH_PATHS)) as executor:
        # Create partial function with pattern
        scan_with_pattern = partial(scan_path, pattern_regex=pattern_regex)
        path_results = executor.map(scan_with_pattern, SEARCH_PATHS)

    # Flatten results
    all_files = []
    for files in path_results:
        all_files.extend(files)

    # Sort alphabetically by filename (case-insensitive)
    all_files.sort(key=lambda p: p.name.lower())

    # Add index after sorting
    results = [(idx, file_path) for idx, file_path in enumerate(all_files, 1)]

    return results


@app.command()
def find(pattern: str = typer.Argument("*", help="Search pattern (glob-based)")):
    """List media files matching the search pattern.

    Args:
        pattern: Glob-based search pattern. If no wildcards are present,
                 the pattern will be wrapped with wildcards automatically.
    """
    results = find_media_files(pattern)

    if not results:
        console.print(f"[yellow]No media files found matching '{pattern}'[/yellow]")
        raise typer.Exit()

    # Save results to cache
    save_search_results(pattern, results)

    # Create rich table
    # Calculate width for index column based on largest index
    max_index_width = len(str(len(results))) if results else 1

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("#", style="cyan", width=max_index_width, justify="right")
    table.add_column("File", style="green")
    table.add_column("Location", style="blue")

    for idx, file_path in results:
        table.add_row(str(idx), file_path.name, str(file_path.parent))

    # Wrap in panel with title on the left and vertical padding
    panel = Panel(
        table, title=f"[bold]{pattern}[/bold]", title_align="left", padding=(1, 1)
    )
    console.print()  # Blank line before panel
    console.print(panel)


@app.command()
def play(index: int = typer.Argument(..., help="Index of the file to play")):
    """Play a media file by its index.

    Args:
        index: The 1-based index number of the file to play, as shown
               in the list command output.
    """
    # Load cached search results
    cached = load_search_results()

    if cached is None:
        console.print(
            "[red]No previous search found. Please run 'mf list <pattern>' first.[/red]"
        )
        raise typer.Exit(1)

    pattern, results = cached

    # Find the file with the requested index
    file_to_play = None
    for idx, file_path in results:
        if idx == index:
            file_to_play = file_path
            break

    if file_to_play is None:
        console.print(
            f"[red]Index {index} not found in last search results (pattern: '{pattern}')[/red]"
        )
        console.print(f"[yellow]Valid indices: 1-{len(results)}[/yellow]")
        raise typer.Exit(1)

    # Check if file still exists
    if not file_to_play.exists():
        console.print(f"[red]File no longer exists:[/red] {file_to_play}")
        raise typer.Exit(1)

    console.print(f"[green]Playing:[/green] {file_to_play.name}")
    console.print(f"[blue]Location:[/blue] {file_to_play.parent}")

    # Launch VLC with the file
    try:
        if os.name == "nt":  # Windows
            # Try common VLC installation paths
            vlc_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ]
            vlc_cmd = None
            for path in vlc_paths:
                if Path(path).exists():
                    vlc_cmd = path
                    break

            if vlc_cmd is None:
                # Try to find in PATH
                vlc_cmd = "vlc"
        else:  # Unix-like (Linux, macOS)
            vlc_cmd = "vlc"

        # Launch VLC in background
        subprocess.Popen(
            [vlc_cmd, str(file_to_play)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        console.print("[green]✓[/green] VLC launched successfully")

    except FileNotFoundError:
        console.print(
            "[red]Error: VLC not found. Please install VLC media player.[/red]"
        )
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error launching VLC:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
