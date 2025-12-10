def test_init_main_and_version_importable():
    # Import package root and ensure attributes are exposed
    import mf

    # `app_mf` should be importable via __init__ re-export
    assert hasattr(mf, "app_mf")

    # main should exist and be callable
    assert hasattr(mf, "main")
    assert callable(mf.main)
