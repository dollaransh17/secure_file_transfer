#!/bin/sh
# One Claude explanation, with at most one format repair, using isolated events.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
docker info >/dev/null
docker compose run --rm --no-deps -v "$prooflane_root/scripts:/app/scripts:ro" api python scripts/live_assistant_smoke.py
