from mf.utils import normalize_bool_str, normalize_media_extension, normalize_pattern


def test_normalize_pattern_wraps_simple_term():
    assert normalize_pattern("batman") == "*batman*"


def test_normalize_pattern_keeps_glob():
    assert normalize_pattern("*.mp4") == "*.mp4"


def test_normalize_media_extension_lowercases_and_dedots():
    assert normalize_media_extension("MP4") == ".mp4"
    assert normalize_media_extension(".MKV") == ".mkv"


def test_normalize_bool_str_true_values():
    for val in ["true", "Yes", "ON", "1", "enable", "enabled"]:
        assert normalize_bool_str(val) is True


def test_normalize_bool_str_false_values():
    for val in ["false", "No", "off", "0", "disable", "disabled"]:
        assert normalize_bool_str(val) is False
