#!/bin/sh
# Start the real stack and confirm readiness before printing its browser URL.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
if ! command -v docker >/dev/null 2>&1; then
    echo 'Docker with Compose is required. Install it and start the Docker daemon.' >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo 'Cannot access the Docker daemon. Start Docker Desktop and check terminal/workspace Docker permissions.' >&2
    echo 'No Prooflane service has been started. Run: python3 scripts/doctor.py' >&2
    exit 1
fi
if [ ! -f .env ]; then
    python3 scripts/init_local_config.py
    echo 'Created .env with loopback-only local development settings.'
fi
docker compose config --quiet
# The API is the sole builder for the image reused by migrations/init/workers.
# Complete pulls/builds before starting services; do not export the same tag
# concurrently through multiple Compose build targets.
if ! docker compose pull postgres redis clamav; then
    echo 'An infrastructure image could not be pulled. No application build was attempted.' >&2
    exit 1
fi
if ! docker compose build api minio web; then
    echo 'A Prooflane image build failed. Check the build error above; existing images and volumes have been retained.' >&2
    exit 1
fi
if ! docker compose up --no-build -d --wait --wait-timeout 600; then
    echo 'Prooflane did not become healthy. Recent startup logs follow:' >&2
    docker compose logs --tail 60 storage-init minio migrate api web worker worker-2 clamav >&2
    exit 1
fi
# Check both the public proxy path and database-backed health, not just containers.
if ! docker compose exec -T web wget -q -O /dev/null http://127.0.0.1/api/health; then
    echo 'The frontend proxy cannot reach the healthy API. Inspect: docker compose logs web api' >&2
    exit 1
fi
prooflane_web_binding=$(docker compose port web 80)
printf '\nProoflane is ready: http://localhost:%s\n' "${prooflane_web_binding##*:}"
printf 'Stop services with: docker compose stop\n'
