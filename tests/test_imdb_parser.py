from imdbinfo import search_title


def test_search_title():
    test_title = "metropolis"
    test_imdb_id = "0017136"
    result = search_title(test_title).titles[0]
    assert result.title.lower() == test_title
    assert result.id == test_imdb_id
