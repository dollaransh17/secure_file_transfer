#!/bin/sh
# Execute current suites without retraining models or provisioning infrastructure.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
exec python3 scripts/test_all.py
