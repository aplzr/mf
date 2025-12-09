
from mf.utils.file import get_cache_dir, get_library_cache_file
from mf.utils.misc import format_size


def test_format_size_thresholds():
    assert format_size(123) == "123 B"
    assert format_size(1536) == "1.50 kB"
    assert format_size(10 * 1024 * 1024) == "10.0 MB"
    assert format_size(150 * 1024 * 1024 * 1024) == "150 GB"


def test_library_cache_file_isolated_env(isolated_config):
    cache_dir = get_cache_dir()
    path = get_library_cache_file()
    assert path.name == "library.json"
    assert path.parent == cache_dir
    assert cache_dir.exists()
