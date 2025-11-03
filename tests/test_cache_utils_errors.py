import pytest
import typer

from mf.utils import get_file_by_index, save_search_results


def test_get_file_by_index_invalid_index(tmp_path):
    f = tmp_path / "m.mp4"
    f.write_text("x")
    save_search_results("*", [(1, f)])
    with pytest.raises(typer.Exit):
        get_file_by_index(2)


def test_get_file_by_index_deleted_file(tmp_path):
    f = tmp_path / "gone.mp4"
    f.write_text("x")
    save_search_results("*", [(1, f)])
    f.unlink()  # remove file
    with pytest.raises(typer.Exit):
        get_file_by_index(1)
