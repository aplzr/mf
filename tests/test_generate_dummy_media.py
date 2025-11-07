from pathlib import Path

from mf.utils.generate_dummy_media import (
    MOVIES,
    SHOW_EPISODES,
    SPECIALS,
    generate_dummy_media,
)


def test_generate_dummy_media_structure(tmp_path: Path):
    """Full generation creates expected directories and files and is idempotent."""
    generate_dummy_media(tmp_path)

    movies_dir = tmp_path / "movies"
    shows_dir = tmp_path / "shows"

    assert movies_dir.is_dir()
    assert shows_dir.is_dir()

    # All movie + specials files exist
    for name in MOVIES + SPECIALS:
        assert (movies_dir / name).is_file(), f"Missing dummy movie: {name}"

    # Show episodes under show/Season XX/
    for show, episodes in SHOW_EPISODES.items():
        for ep in episodes:
            # Extract season token like S01E02
            season_token = next(
                (part for part in ep.split() if part.startswith("S") and "E" in part),
                None,
            )
            assert season_token, f"No season token found in {ep}"
            season_num = season_token.split("E")[0][1:]
            season_folder = f"Season {season_num}"
            path = shows_dir / show / season_folder / ep
            assert path.is_file(), f"Missing episode file: {path}"

    # Capture mtimes for idempotency check
    before = {p: p.stat().st_mtime for p in movies_dir.rglob('*') if p.is_file()}
    before.update({p: p.stat().st_mtime for p in shows_dir.rglob('*') if p.is_file()})

    # Second run should not overwrite existing files (mtime stable)
    generate_dummy_media(tmp_path)

    after = {p: p.stat().st_mtime for p in movies_dir.rglob('*') if p.is_file()}
    after.update({p: p.stat().st_mtime for p in shows_dir.rglob('*') if p.is_file()})

    assert (
        before == after
    ), "File mtimes changed on second generation run (not idempotent)"

    # Ensure printed summary lines (rough smoke test)
    # We don't capture stdout here, but absence of exceptions is our success condition.
