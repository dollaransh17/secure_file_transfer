#!/bin/sh
# Host-based Playwright uses the real localhost origin and running API.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root/apps/web"
npm install
npx playwright install chromium
# Preserve previous host evidence when another run fails before browser startup.
prooflane_browser_run="run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
export E2E_OUTPUT_DIR="test-results/$prooflane_browser_run"
export E2E_JSON_REPORT="test-results/$prooflane_browser_run/report.json"
npm run test:e2e
