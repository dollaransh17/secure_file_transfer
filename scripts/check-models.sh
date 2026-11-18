#!/bin/sh
# Check existing trained models without retraining or changing other workspaces.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
docker info >/dev/null
docker compose -f docker-compose.yml -f docker-compose.ml.yml up --no-build --no-deps -d --wait --wait-timeout 180 worker worker-2
docker compose run --rm --no-deps -v "$prooflane_root/scripts:/app/scripts:ro" api python scripts/live_ml_smoke.py
