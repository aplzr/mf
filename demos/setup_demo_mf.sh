#!/bin/bash

if command -v mf &> /dev/null; then
    rm $(mf cache file) 2>/dev/null || true
    rm $(mf config file) 2>/dev/null || true
fi

uv tool uninstall mediafinder 2>/dev/null || true
rm -rf ~/movies
rm -rf ~/shows
python3 ../src/mf/utils/generate_dummy_media.py ~
mv -f ~/shows ~/dummy_shows
mv -f ~/movies ~/dummy_movies
