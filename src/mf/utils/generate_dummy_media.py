"""Utility script to generate dummy media files for demos.

Creates a set of fictitious movie and TV show files using common naming
conventions without referencing real copyrighted titles. Intended for
term-to-SVG / asciinema style showcase recordings of the *mf* CLI.

Usage (module):
    python -m mf.utils.generate_dummy_media [BASE_DIR]

Usage (script):
    python src/mf/utils/generate_dummy_media.py [BASE_DIR]

If BASE_DIR is omitted the current working directory is used.

The following structure will be created (if not already present):

    BASE_DIR/
        movies/
            <movie files>
        shows/
            CircuitWorld/
                Season 01/
                    CircuitWorld S01E01 Pilot.mkv
                    ...
            EchoNetwork/
                Season 01/
                    ...
            Tiny Travelers/
                Season 01/
                    ...

All files are tiny text files containing the word "dummy". They are only
meant to exist so *mf* can index and display them. Safe to delete at any
time.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# Movie and show names sourced from a synthetic list crafted to avoid
# real media collisions.
MOVIES: list[str] = [
    "Aurora Dawn 2023 1080p.mp4",
    "Broken Horizon 2019 720p.mkv",
    "Circuit Dreams 2024 4K HDR.mkv",
    "Crimson Alloy 2022 1080p.mov",
    "Dawn of Tomorrow 2021 1080p Extended Cut.mkv",
    "Echoes of Mist 2020 480p.mp4",
    "Emerald Skies 2024 2160p WEBRip.mkv",
    "Final Orbit 2023 1080p Director's Cut.mkv",
    "Glass Forest 2018 1080p.mp4",
    "Grey Rain 2022 720p WEB-DL.mp4",
    "Hollow Signal 2025 1080p.mkv",
    "Ivory Engine 2023 1080p HEVC.mkv",
    "Jade Sector 2024 4K.mkv",
    "Last Beacon 2021 1080p.mkv",
    "Lunar Silence 2020 1080p.mp4",
    "Midnight Lattice 2022 1080p AAC.mp4",
    "Nebula Trace 2023 1080p.mkv",
    "Obsidian Field 2019 720p.mp4",
    "Parallax Drift 2024 1080p.mkv",
    "Quantum Stone 2025 1080p DV.mkv",
    "Silent Array 2022 1080p.mp4",
    "Solar Fragments 2023 1080p HDR.mkv",
    "Star of Glass 2021 720p.mp4",
    "Static Valley 2020 1080p.mp4",
    "Synthetic Memory 2024 1080p.mkv",
    "Velvet Cascade 2025 1080p.mp4",
    "Winter Node 2023 1080p.mkv",
    # Multi-part / split examples
    "Crimson Alloy 2022 1080p Part1.mkv",
    "Crimson Alloy 2022 1080p Part2.mkv",
    "Final Orbit 2023 1080p CD1.mkv",
    "Final Orbit 2023 1080p CD2.mkv",
    # Different extensions coverage
    "Echoes of Mist 2020 1080p.webm",
    "Winter Node 2023 1080p.avi",
    "Grey Rain 2022 720p.wmv",
    "Obsidian Field 2019 720p.flv",
    # Generic samples
    "Sample Media File A 2024.mp4",
    "Sample Media File B 2024.mkv",
]

# Episode definitions per show
SHOW_EPISODES: dict[str, list[str]] = {
    "CircuitWorld": [
        "CircuitWorld S01E01 Pilot.mkv",
        "CircuitWorld S01E02 Diagnostics.mkv",
        "CircuitWorld S01E03 Failover.mkv",
        "CircuitWorld S01E04 Interrupt.mkv",
        "CircuitWorld S01E05 Overclock.mkv",
        "CircuitWorld S02E01 Restart.mkv",
        "CircuitWorld S02E02 Patch.mkv",
        "CircuitWorld S02E03 Kernel Panic.mkv",
        "CircuitWorld S02E04 Recovery.mkv",
        "CircuitWorld S02E05 Shutdown.mkv",
    ],
    "EchoNetwork": [
        "EchoNetwork S01E01 Signal Found.mp4",
        "EchoNetwork S01E02 Crosslink.mp4",
        "EchoNetwork S01E03 Latency.mp4",
        "EchoNetwork S01E04 Packet Loss.mp4",
        "EchoNetwork S01E05 Silent Channel.mp4",
    ],
    "Tiny Travelers": [
        "Tiny Travelers S01E01 Packing Day.mp4",
        "Tiny Travelers S01E02 Lost Compass.mp4",
        "Tiny Travelers S01E03 Floating Map.mp4",
    ],
}

SPECIALS: list[str] = [
    "Aurora Dawn Behind the Scenes 2023 1080p.mp4",
    "Aurora Dawn Teaser Trailer 2023 1080p.mp4",
    "Nebula Trace Production Diary 2023 720p.mkv",
    "Solar Fragments Promo Clip 2023 1080p.mp4",
    "Quantum Stone Featurette 2025 1080p.mkv",
    "Building a Distributed Garden 2024 1080p.mkv",
    "Intro to Synthetic Biology 2023 720p.mp4",
    "Mapping the Quiet Ocean 2022 1080p.mov",
    "Renewable Systems Overview 2024 1080p.mkv",
    "Understanding Modular Robotics 2025 1080p.mkv",
    "Horizon 2 2023 1080p.mp4",
    "Drift_Archive_2024.mkv",
    "Node-Log-2025.mov",
    "Beacon2021.mkv",
    "Mist.v2.2020.mp4",
]


@dataclass
class Created:  # noqa: D101
    path: Path
    existed: bool


def _touch_file(path: Path) -> Created:
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    if not existed:
        # Tiny placeholder content (still a text file with a video extension).
        path.write_text("dummy", encoding="utf-8")
    return Created(path, existed)


def create_movies(base: Path) -> list[Created]:
    movies_dir = base / "movies"
    created: list[Created] = []
    for name in MOVIES + SPECIALS:
        created.append(_touch_file(movies_dir / name))
    return created


def create_shows(base: Path) -> list[Created]:
    shows_dir = base / "shows"
    created: list[Created] = []
    for show, episodes in SHOW_EPISODES.items():
        for ep in episodes:
            # Derive season folder from SxxExx token
            season_token = next(
                (part for part in ep.split() if part.startswith("S") and "E" in part),
                "S01E01",
            )
            season_num = season_token.split("E")[0][1:]  # after leading 'S'
            season_folder = f"Season {season_num}"
            created.append(_touch_file(shows_dir / show / season_folder / ep))
    return created


def summarize(results: Iterable[Created]) -> str:
    new_count = sum(1 for r in results if not r.existed)
    skipped = sum(1 for r in results if r.existed)
    return f"Created {new_count} new files, skipped {skipped} existing."


def generate_dummy_media(base_dir: Path | None = None) -> None:
    if base_dir is None:
        base_dir = Path.cwd()
    movies = create_movies(base_dir)
    shows = create_shows(base_dir)
    summary = summarize(movies + shows)
    print(summary)
    print(f"Base directory: {base_dir}")
    print(f"Movies directory: {base_dir / 'movies'}")
    print(f"Shows directory: {base_dir / 'shows'}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    base = Path(argv[0]).expanduser().resolve() if argv else Path.cwd()
    generate_dummy_media(base)
    return 0


if __name__ == "__main__":  # pragma: no cover - convenience script entry
    raise SystemExit(main())
