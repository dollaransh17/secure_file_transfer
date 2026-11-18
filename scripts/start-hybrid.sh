#!/bin/sh
# Run on the Mac host. Does not create or modify AWS resources.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
if [ ! -x .venv/bin/python ]; then
    echo 'Create a Python 3.12/3.13 .venv and install the project dependencies first.' >&2
    exit 1
fi
exec .venv/bin/python scripts/start_hybrid.py "$@"
