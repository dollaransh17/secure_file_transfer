#!/bin/sh
# Apply the frontend logout fix and rerun browser tests against the real stack.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
npm --prefix apps/web run test:unit
docker info >/dev/null
docker compose build web
docker compose up --no-build --no-deps -d --wait --wait-timeout 180 web
# Resolve the actual published port, including values loaded from .env.
prooflane_web_binding=$(docker compose port web 80)
export E2E_URL="http://localhost:${prooflane_web_binding##*:}"
cd "$prooflane_root/apps/web"
prooflane_browser_run="logout-$(date -u +%Y%m%dT%H%M%SZ)-$$"
export E2E_OUTPUT_DIR="test-results/$prooflane_browser_run"
export E2E_JSON_REPORT="test-results/$prooflane_browser_run/report.json"
npm run test:e2e
