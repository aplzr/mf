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

# Clean build artifacts
[windows]
clean:
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }; if (Test-Path build) { Remove-Item -Recurse -Force build }; Get-ChildItem -Filter "*.egg-info" -Recurse | Remove-Item -Recurse -Force

[unix]
clean:
    rm -rf dist/ build/ *.egg-info

# Clean tool caches (Windows)
[windows]
clean-cache:
    uv clean
    if (Test-Path .pytest_cache) { Remove-Item -Recurse -Force .pytest_cache }; if (Test-Path .ruff_cache) { Remove-Item -Recurse -Force .ruff_cache }

# Clean tool caches (Unix)
[unix]
clean-cache:
    uv clean
    rm -rf .pytest_cache .ruff_cache

# NOTE: all recipes that take a VERSION parameter will stash all uncommitted changes,
# check out the corresponding version tag, do what they're supposed to do with that
# version (build, publish, etc.), then check out the previous revision and re-apply the
# stashed changes (if there where any).

# Build distribution (Unix)
[unix]
build VERSION:
    #!/usr/bin/env bash
    just clean
    set -e
    HAS_CHANGES=0
    git diff-index --quiet HEAD || HAS_CHANGES=1
    if [ $HAS_CHANGES -eq 1 ]; then git stash push -u -m "build"; fi
    git checkout "v{{VERSION}}"
    uv build
    git checkout -
    if [ $HAS_CHANGES -eq 1 ]; then git stash pop; fi

# Build distribution (Windows)
[windows]
build VERSION:
    just clean
    $hasChanges = (git status --porcelain).Length -gt 0
    if ($hasChanges) { git stash push -u -m "build" }
    git checkout "v{{VERSION}}"
    uv build
    git checkout -
    if ($hasChanges) { git stash pop }

# Publish to TestPyPI (Unix)
[unix]
pypi-test VERSION TOKEN:
    #!/usr/bin/env bash
    set -e
    HAS_CHANGES=0
    git diff-index --quiet HEAD || HAS_CHANGES=1
    if [ $HAS_CHANGES -eq 1 ]; then git stash push -u -m "pypi-test"; fi
    git checkout "v{{VERSION}}"
    just clean
    just build
    uv publish --publish-url https://test.pypi.org/legacy/ --token {{TOKEN}}
    git checkout -
    if [ $HAS_CHANGES -eq 1 ]; then git stash pop; fi

# Publish to TestPyPI (Windows)
[windows]
pypi-test VERSION TOKEN:
    $hasChanges = (git status --porcelain).Length -gt 0
    if ($hasChanges) { git stash push -u -m "pypi-test" }
    git checkout "v{{VERSION}}"
    just clean
    just build
    uv publish --publish-url https://test.pypi.org/legacy/ --token {{TOKEN}}
    git checkout -
    if ($hasChanges) { git stash pop }

# NOTE: In the verify recipes, the pinning of `jmespath<99.99.99` is necessary
# because one of mediafinder's direct dependencies depends on it and it has a
# bogus version `99.99.99` on test.pypi.org which can't be installed.

# Verify TestPyPI package (Unix)
[unix]
pypi-verify VERSION:
    #!/usr/bin/env bash
    set -e
    HAS_CHANGES=0
    git diff-index --quiet HEAD || HAS_CHANGES=1
    if [ $HAS_CHANGES -eq 1 ]; then git stash push -u -m "pypi-verify"; fi
    git checkout "v{{VERSION}}"
    uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ --index-strategy unsafe-best-match --with "jmespath<99.99.99, mediafinder=={{VERSION}}, pytest, pytest-cov" pytest --no-cov tests
    git checkout -
    if [ $HAS_CHANGES -eq 1 ]; then git stash pop; fi

# Verify TestPyPI package (Windows)
[windows]
pypi-verify VERSION:
    $hasChanges = (git status --porcelain).Length -gt 0
    if ($hasChanges) { git stash push -u -m "pypi-verify" }
    git checkout "v{{VERSION}}"
    uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ --index-strategy unsafe-best-match --with "jmespath<99.99.99, mediafinder=={{VERSION}}, pytest, pytest-cov" pytest --no-cov tests
    git checkout -
    if ($hasChanges) { git stash pop }

# Publish to PyPI (Unix)
[unix]
pypi-production VERSION TOKEN:
    #!/usr/bin/env bash
    set -e
    HAS_CHANGES=0
    git diff-index --quiet HEAD || HAS_CHANGES=1
    if [ $HAS_CHANGES -eq 1 ]; then git stash push -u -m "pypi-production"; fi
    git checkout "v{{VERSION}}"
    just clean
    just build
    uv publish --token {{TOKEN}}
    git checkout -
    if [ $HAS_CHANGES -eq 1 ]; then git stash pop; fi

# Publish to PyPI (Windows)
[windows]
pypi-production VERSION TOKEN:
    $hasChanges = (git status --porcelain).Length -gt 0
    if ($hasChanges) { git stash push -u -m "pypi-production" }
    git checkout "v{{VERSION}}"
    just clean
    just build
    uv publish --token {{TOKEN}}
    git checkout -
    if ($hasChanges) { git stash pop }
