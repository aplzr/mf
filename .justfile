# Platform-specific shell configuration
set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

# Default recipe to display help
default:
    @just --list

# Prune remote tracking branches and delete local branches whose remote is gone
prune:
    git remote prune origin
    just _prune-local

[windows]
_prune-local:
    git for-each-ref --format '%(refname:short) %(upstream:track)' refs/heads | Select-String '\[gone\]' | ForEach-Object { $_.ToString().Split()[0] } | ForEach-Object { Write-Host "Deleting branch: $_"; git branch -D $_ }

[unix]
_prune-local:
    @git for-each-ref --format '%(refname:short) %(upstream:track)' refs/heads | grep '\[gone\]' | cut -d ' ' -f1 | while read branch; do [ -n "$branch" ] && echo "Deleting branch: $branch" && git branch -D "$branch"; done || true

# Run tests with coverage
test:
    pytest

# Run tests without coverage (fast)
test-quick:
    pytest -q --no-cov

# Run specific test file
test-file FILE:
    pytest {{FILE}}

# Run linting checks
lint:
    ruff check .

# Run linting with auto-fix
lint-fix:
    ruff check . --fix

# Format code
format:
    ruff format .

# Install dev dependencies
install:
    uv pip install -e .[dev]

# Build distribution
build:
    uv build

# Clean build artifacts
[windows]
clean:
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }; if (Test-Path build) { Remove-Item -Recurse -Force build }; Get-ChildItem -Filter "*.egg-info" -Recurse | Remove-Item -Recurse -Force; if (Test-Path .pytest_cache) { Remove-Item -Recurse -Force .pytest_cache }; if (Test-Path .ruff_cache) { Remove-Item -Recurse -Force .ruff_cache }

[unix]
clean:
    rm -rf dist/ build/ *.egg-info .pytest_cache .ruff_cache
