#!/bin/sh
# Apply the UI/Claude update, validate optional research/cloud tooling, and train.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
if ! docker info >/dev/null 2>&1; then
    echo 'Docker is unavailable from this terminal. Start Docker Desktop first.' >&2
    exit 1
fi
# Build each shared image once. Running tests precedes recreating accepted services.
docker compose build api web
docker compose run --rm --no-deps api python -m pytest -q
docker compose up --no-build -d --wait --wait-timeout 600
# Reads the model endpoint only; no application evidence or generation prompt.
if ! docker compose run --rm --no-deps api python scripts/check_claude.py; then
    echo 'Claude configuration could not be verified; core security and research checks continue independently.' >&2
fi
# No AWS APIs or resource creation in this workflow.
python3 infrastructure/aws/build_template.py
docker compose --profile cloud-check build cloud-check
docker compose --profile cloud-check run --rm --no-deps cloud-check
# Genuine CPU model tests, then causal training and paired held-out comparison.
docker compose --profile research build research
docker compose --profile research run --rm --no-deps research
if [ "${PROOFLANE_TRAIN_MODELS:-1}" = '1' ]; then
    docker compose --profile research run --rm --no-deps research python -m ml.pipeline --epochs "${PROOFLANE_TRAIN_EPOCHS:-10}"
    ./scripts/check-models.sh
fi
printf '\nUpdated Prooflane: http://localhost:5173\n'
printf 'Model manifests: artifacts/models; held-out comparison: artifacts/results-v2/results.json\n'
