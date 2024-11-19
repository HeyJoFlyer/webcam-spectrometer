#! /bin/bash

# Creates a virtual environment and installs dependencies

python3 -m venv $(pwd)/.venv/ 2> /dev/null || printf "venv module not installed, please install python venv \ne.g. for Debian: sudo apt install python3-venv\n" && exit 1

source $(pwd)/.venv/bin/activate

pip install -r $(pwd)/software/requirements.txt