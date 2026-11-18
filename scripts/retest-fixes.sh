#!/bin/sh
# Apply the citation fix, then rerun only the two failing live suites.
# Reuses trained models/workers; no training or AWS deployment.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
docker info >/dev/null
docker compose build api
docker compose run --rm --no-deps -e ANTHROPIC_API_KEY= -e ANTHROPIC_MODEL= api \
    python -m pytest tests/test_assistant.py tests/test_assistant_evidence_stdlib.py -q
docker compose up --no-build --no-deps -d --wait --wait-timeout 180 api
prooflane_retest_status=0
./scripts/check-assistant.sh || prooflane_retest_status=1
./scripts/retest-browser.sh || prooflane_retest_status=1
exit "$prooflane_retest_status"
