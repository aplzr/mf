import typer

from .utils import console, get_cache_file, load_search_results, print_search_results

app_cache = typer.Typer(
    help=(
        "Show cache contents, print cache location or clear the cache. "
        "If no argument is given, runs the default 'show' command."
    )
)


@app_cache.command()
def show():
    """Print cache contents."""
    pattern, results, timestamp = load_search_results()
    console.print(f"[yellow]Cache file:[/yellow] {get_cache_file()}")
    console.print(f"[yellow]Timestamp:[/yellow] [grey70]{str(timestamp)}[/grey70]")
    console.print("[yellow]Cached results:[/yellow]")

    if "latest additions" not in pattern:
        pattern = f"Search pattern: {pattern}"

    print_search_results(pattern, results)


@app_cache.command()
def file():
    """Print the cache file location."""
    console.print(get_cache_file())


@app_cache.command()
def clear():
    """Clear the cache."""
    get_cache_file().unlink(missing_ok=True)
    console.print("✔  Cache cleared.", style="green")


@app_cache.callback(invoke_without_command=True)
def cache_callback(ctx: typer.Context):
    """Runs the default subcommand 'show' when no argument to 'cache' is provided."""
    if ctx.invoked_subcommand is None:
        show()
