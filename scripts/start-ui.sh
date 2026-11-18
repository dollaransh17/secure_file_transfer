#!/bin/sh
# Apply the frontend design and start the existing local stack, without training
# models, rebuilding the backend, or creating any AWS resources.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
if ! docker info >/dev/null 2>&1; then
    echo 'Cannot access Docker. Start Docker Desktop and run this script in your terminal.' >&2
    exit 1
fi
if [ ! -f .env ]; then
    echo 'The existing .env is required. For a first-time setup use ./scripts/start-local.sh.' >&2
    exit 1
fi
export PROOFLANE_WEB_PORT=${PROOFLANE_WEB_PORT:-5174}
export PROOFLANE_API_PORT=${PROOFLANE_API_PORT:-8001}
set -- -f docker-compose.yml
if docker image inspect prooflane-research:local >/dev/null 2>&1; then
    set -- "$@" -f docker-compose.ml.yml
fi
docker compose "$@" config --quiet
docker compose "$@" build web
docker compose "$@" up --no-build -d --wait --wait-timeout 600
docker compose "$@" exec -T web wget -q -O /dev/null http://127.0.0.1/api/health
prooflane_web_binding=$(docker compose "$@" port web 80)
prooflane_api_binding=$(docker compose "$@" port api 8000)
printf '\nProoflane is ready: http://localhost:%s\n' "${prooflane_web_binding##*:}"
printf 'API documentation: http://localhost:%s/docs\n' "${prooflane_api_binding##*:}"
