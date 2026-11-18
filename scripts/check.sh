#!/bin/sh
set -eu
python -m compileall -q apps/api ml benchmarks scripts tests
PYTHONPATH=apps/api:. python -m unittest discover -s tests -p '*stdlib.py' -v
python -m pytest -q
npm --prefix apps/web run build
