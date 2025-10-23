import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import typer
from guessit import guessit
from imdb import IMDb

from ._version import __version__
from .utils import (
    console,
    find_media_files,
    get_cache_file,
    get_file_by_index,
    load_search_results,
    normalize_pattern,
    print_search_results,
    save_search_results,
)

app = typer.Typer(help="Media file finder and player")
cache_app = typer.Typer(
    help=(
        "Show cache contents, print cache location or clear the cache. "
        "If no argument is given, runs the default 'show' command."
    )
)
app.add_typer(cache_app, name="cache")


@app.command()
def find(pattern: str = typer.Argument("*", help="Search pattern (glob-based)")):
    """Find media files matching the search pattern.

    Finds matching files and prints an indexed list.

    Args:
        pattern (str): Glob-based search pattern. If no wildcards are present, the
            pattern will be wrapped with wildcards automatically.

    Raises:
        typer.Exit: No matching files found.
    """
    # Find, cache, and print media file paths
    pattern = normalize_pattern(pattern)
    results = find_media_files(pattern)

    if not results:
        console.print(f"No media files found matching '{pattern}'", style="yellow")
        raise typer.Exit()

    save_search_results(pattern, results)
    print_search_results(f"Search pattern: {pattern}", results)


@app.command()
def new(
    n: int = typer.Argument(20, help="Number of latest additions to show"),
):
    """Find the latest additions to the media database.

    Args:
        n (int, optional): Number of latest additions to show. Defaults to 20.
    """
    # Run parallelized IO lookups for fast create date retrieval of all files
    all_files = [path for _, path in find_media_files("*")]
    with ThreadPoolExecutor(max_workers=50) as executor:
        times = list(executor.map(lambda path: path.stat().st_mtime, all_files))

    # Sort, filter, add index
    latest_files = [path for _, path in sorted(zip(times, all_files), reverse=True)][:n]
    latest_files = [(idx, path) for idx, path in enumerate(latest_files, start=1)]

    # Cache and print results
    pattern = f"{n} latest additions"
    save_search_results(pattern, latest_files)
    print_search_results(pattern, latest_files)


@app.command()
def play(index: int = typer.Argument(..., help="Index of the file to play")):
    """Play a media file by its index.

    Args:
        index (int): The 1-based index number of the file to play, as shown in the list
            command output.

    Raises:
        typer.Exit: VLC not found.
        typer.Exit: Error launching VLC.
    """
    file_to_play = get_file_by_index(index)

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
            "Error: VLC not found. Please install VLC media player.", style="red"
        )
        raise typer.Exit(1)

    except Exception as e:
        console.print(f"Error launching VLC: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def imdb(
    index: int = typer.Argument(
        ..., help="Index of the file for which to retrieve the IMDB URL"
    ),
):
    """Open IMDB entry of a search result.

    Args:
        index (int): Index of the file for which to retrieve the IMDB URL.
    """
    filestem = get_file_by_index(index).stem
    title = guessit(filestem)["title"]
    imdb_entry = IMDb().search_movie(title)[0]
    imdb_url = f"https://www.imdb.com/title/tt{imdb_entry.movieID}/"
    console.print(f"IMDB entry for [green]{imdb_entry['title']}[/green]: {imdb_url}")
    typer.launch(imdb_url)


@app.command()
def filepath(
    index: int = typer.Argument(
        ..., help="Index of the file for which to print the filepath."
    ),
):
    """Print filepath of a search result."""
    print(get_file_by_index(index))


@app.command()
def version():
    "Print version."
    console.print(__version__)


@cache_app.command()
def show():
    """Print cache contents."""
    pattern, results, timestamp = load_search_results()
    console.print(f"[yellow]Cache file:[/yellow] {get_cache_file()}")
    console.print(f"[yellow]Timestamp:[/yellow] [grey70]{str(timestamp)}[/grey70]")
    console.print("[yellow]Cached results:[/yellow]")

    if "latest additions" not in pattern:
        pattern = f"Search pattern: {pattern}"

    print_search_results(pattern, results)


@cache_app.command()
def file():
    """Print the cache file location."""
    console.print(get_cache_file())


@cache_app.command()
def clear():
    """Clear the cache."""
    get_cache_file().unlink(missing_ok=True)
    console.print("Cache cleared.")


@cache_app.callback(invoke_without_command=True)
def cache_callback(ctx: typer.Context):
    """Runs the default subcommand 'show' when no argument to 'cache' is provided."""
    if ctx.invoked_subcommand is None:
        show()


# TODOs
# - [x] Add a "new" command that lists the last n newest additions
# - [x] Add a "cache" command that lists the current cache
# - [x] Return timestamp in load_search_results and print it in cache
# - [x] Add "imdb" command
# - [ ] Add "trailer" command
# - [ ] Add -r option for additional ratings
# - [x] Add "filepath" command
