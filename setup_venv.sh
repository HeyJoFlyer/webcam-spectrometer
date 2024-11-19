#! /bin/bash

# Creates a virtual environment and installs dependencies

if ! [$(python3 -m pip freeze) | grep "venv "]; then
    python3 -m pip install venv
fi

python3 -m venv $(pwd)/.venv/

source $(pwd)/.venv/bin/activate

pip install -r $(pwd)/software/requirements.txt