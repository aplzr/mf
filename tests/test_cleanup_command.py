"""Tests for the cleanup command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mf.cli_main import app_mf
from mf.utils.config import get_config_file
from mf.utils.file import get_library_cache_file, get_search_cache_file


@pytest.fixture
def runner():
    """Provide a CliRunner instance."""
    return CliRunner()


def test_cleanup_no_files_exist(runner):
    """Test cleanup when no config or cache files exist."""
    # Ensure files don't exist
    config_file = get_config_file()
    library_cache = get_library_cache_file()
    search_cache = get_search_cache_file()

    if config_file.exists():
        config_file.unlink()
    if library_cache.exists():
        library_cache.unlink()
    if search_cache.exists():
        search_cache.unlink()

    result = runner.invoke(app_mf, ["cleanup"])

    assert result.exit_code == 0
    assert "No configuration or cache files exist" in result.stdout
    assert "nothing to clean up" in result.stdout


def test_cleanup_user_confirms_deletion(runner):
    """Test cleanup when user confirms deletion."""
    # Ensure files exist
    config_file = get_config_file()
    library_cache = get_library_cache_file()
    search_cache = get_search_cache_file()

    # Create files if they don't exist
    config_file.parent.mkdir(parents=True, exist_ok=True)
    library_cache.parent.mkdir(parents=True, exist_ok=True)
    search_cache.parent.mkdir(parents=True, exist_ok=True)

    config_file.touch()
    library_cache.touch()
    search_cache.touch()

    # Simulate user typing "y" to confirm
    result = runner.invoke(app_mf, ["cleanup"], input="y\n")

    assert result.exit_code == 0
    assert "This will reset mediafinder" in result.stdout
    assert "Delete files?" in result.stdout
    assert "Configuration and cache files deleted" in result.stdout
    assert not config_file.exists()
    assert not library_cache.exists()
    assert not search_cache.exists()


def test_cleanup_user_aborts(runner):
    """Test cleanup when user aborts deletion."""
    # Ensure files exist
    config_file = get_config_file()
    library_cache = get_library_cache_file()
    search_cache = get_search_cache_file()

    config_file.parent.mkdir(parents=True, exist_ok=True)
    library_cache.parent.mkdir(parents=True, exist_ok=True)
    search_cache.parent.mkdir(parents=True, exist_ok=True)

    config_file.touch()
    library_cache.touch()
    search_cache.touch()

    # Simulate user typing "n" to abort
    result = runner.invoke(app_mf, ["cleanup"], input="n\n")

    assert result.exit_code == 0
    assert "This will reset mediafinder" in result.stdout
    assert "Delete files?" in result.stdout
    assert "Cleanup aborted" in result.stdout
    # Files should still exist
    assert config_file.exists()
    assert library_cache.exists()
    assert search_cache.exists()


def test_cleanup_shows_files_to_delete(runner):
    """Test that cleanup shows the list of files that will be deleted."""
    # Ensure files exist
    config_file = get_config_file()
    library_cache = get_library_cache_file()
    search_cache = get_search_cache_file()

    config_file.parent.mkdir(parents=True, exist_ok=True)
    library_cache.parent.mkdir(parents=True, exist_ok=True)
    search_cache.parent.mkdir(parents=True, exist_ok=True)

    config_file.touch()
    library_cache.touch()
    search_cache.touch()

    result = runner.invoke(app_mf, ["cleanup"], input="n\n")

    # Check that all files are listed
    assert str(config_file) in result.stdout
    assert str(library_cache) in result.stdout
    assert str(search_cache) in result.stdout


def test_cleanup_only_deletes_existing_files(runner):
    """Test that cleanup only attempts to delete files that exist."""
    # Create only one file
    config_file = get_config_file()
    library_cache = get_library_cache_file()
    search_cache = get_search_cache_file()

    config_file.parent.mkdir(parents=True, exist_ok=True)
    library_cache.parent.mkdir(parents=True, exist_ok=True)

    # Only create config file
    config_file.touch()

    # Ensure cache files don't exist
    if library_cache.exists():
        library_cache.unlink()
    if search_cache.exists():
        search_cache.unlink()

    result = runner.invoke(app_mf, ["cleanup"], input="y\n")

    assert result.exit_code == 0
    # Should only show config file in the list
    assert str(config_file) in result.stdout
    assert str(library_cache) not in result.stdout
    assert str(search_cache) not in result.stdout
    assert not config_file.exists()
