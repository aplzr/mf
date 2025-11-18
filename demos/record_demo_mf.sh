#!/bin/bash

# Run cleanup/setup
./setup_demo_mf.sh

# Record
cd ~
termtosvg development/mf/static/demo_mf.svg \
    -g 100x24 \
    -c 'doitlive play development/mf/demos/demo_mf.session'

