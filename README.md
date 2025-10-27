# mf - Media File Finder

A cross-platform command-line tool for finding and managing video files in large collections

## Features

- **🔍 Fast file search** - Uses optimized `fd` binary with automatic fallback to Python scanning
- **🎯 Flexible pattern matching** - Glob-based search patterns with automatic wildcard wrapping
- **📁 Multi-path scanning** - Search across multiple configured directories simultaneously
- **🕒 Latest additions** - Find newest files by modification time
- **🎬 Media player integration** - Launch files directly in VLC
- **🌐 IMDB lookup** - Automatically open IMDB pages for media files
- **💾 Smart caching** - Cache search results for quick access by index
- **⚙️ Flexible configuration** - TOML-based config with extension filtering and path management
- **🖥️ Cross-platform** - Works on Windows, Linux, and macOS

## Installation
Currently not packaged on PyPI, install (with [uv](https://docs.astral.sh/uv/)) from Github:

```
uv tool install git+https://github.com/aplzr/mf.git
```

or clone first:

```
git clone https://github.com/aplzr/mf.git
cd mf
uv tool install .
```

## Quick Start

1. **Configure search paths** where your media files are located:

```bash
mf config set search_paths "/path/to/movies" "/path/to/tv-shows"
```
2. **Find media files** matching a pattern:

```bash
mf find "batman" # Finds files containing "batman"
mf find "*.mp4" # Finds all MP4 files
mf find "2023" # Finds files from 2023 (if the year is in the filename)
```

3. **Play a file** from search results:

```bash
mf play 1 # Play first result
mf play # Play random file
```

4. **Find latest additions**:
```bash
mf new # Show 20 newest files
mf new 50 # Show 50 newest files
```

## Commands

### Core Commands

- `mf find <pattern>` - Search for media files matching the glob pattern
- `mf new [n]` - Show latest additions (default: 20 files)
- `mf play [index]` - Play a file by index, or random file if no index given
- `mf imdb <index>` - Open IMDB page for a media file
- `mf filepath <index>` - Print full path of a search result
- `mf version` - Print version information

### Configuration Management

- `mf config set <key> <values>` - Set configuration values
- `mf config add <key> <values>` - Add values to list settings
- `mf config remove <key> <values>` - Remove values from list settings
- `mf config get <key>` - Get configuration value
- `mf config list` - Show all configuration
- `mf config edit` - Edit config file in default editor
- `mf config file` - Print config file location

### Cache Management

- `mf cache` - Show cached search results
- `mf cache file` - Print cache file location
- `mf cache clear` - Clear the cache

## Configuration

The tool uses a TOML configuration file with the following settings:

### Search Paths

```bash
mf config set search_paths "/movies" "/tv-shows" "/documentaries"
```

### Media Extensions
Control which file types are considered media files:

```
mf config set media_extensions ".mp4" ".mkv" ".avi" ".mov" ".wmv"
```

### Extension Matching
Toggle whether to filter results by media extensions:

```bash
mf config set match_extensions true # Only return configured media types
mf config set match_extensions false # Return all files matching pattern
```

## Search Patterns

- Use quotes around patterns with wildcards to prevent shell expansion
- Patterns without wildcards are automatically wrapped: `batman` becomes `*batman*`
- Examples:
  - `mf find "*.mp4"` - All MP4 files
  - `mf find batman` - Files containing "batman" 
  - `mf find "*2023*1080p*"` - 2023 releases in 1080p
  - `mf find "s01e??"` - Season 1 episodes

## Integration Features

- **VLC Integration**: Automatically launches VLC media player
- **IMDB Lookup**: Uses filename parsing to find matching IMDB entries
- **Smart Caching**: Search results are cached for quick index-based access
- **Cross-platform paths**: Handles Windows and Unix path conventions

## Performance

- Uses bundled `fd` binary for fast file scanning when possible
- Automatic fallback to Python scanning if `fd` unavailable
- Parallel scanning across multiple search paths
- Efficient caching of file modification times for "newest" searches

## Requirements

- Python 3.10+
- VLC media player (for `play` command)
- Internet connection (for IMDB lookup)

## License

This project is licensed under the MIT License - see the [LICENSE-MIT](LICENSE-MIT) file for details.

### Third-Party Software

This package includes the [`fd`](https://github.com/sharkdp/fd) file finder binary, which is dual-licensed under **MIT OR Apache-2.0**.
Copyright (c) 2017-present the fd developers.

- MIT License: See `src/mf/bin/LICENSE-fd-MIT`
- Apache License 2.0: See `src/mf/bin/LICENSE-fd-APACHE`