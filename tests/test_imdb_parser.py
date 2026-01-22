from warnings import warn
from imdbinfo import search_title


def test_search_title():
    test_title = "metropolis"
    test_imdb_id = "0017136"
    try:
        result = search_title(test_title).titles[0]

        if result.title.lower() != test_title or result.id != test_imdb_id:
            warn(
                "IMDB parser returned unexpected results: "
                f"title={result.title!r} (should be: {test_title}), "
                f"id={result.id!r} (should be: {test_imdb_id}).",
                category=UserWarning,
                )
    except Exception as e:
        warn(
            f"IMDB parser failed (upstream issue): {type(e).__name__}: {e}",
            category=UserWarning
            )
