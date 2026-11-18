#!/bin/sh
# Apply reviewed security targets through npm, verify, then deploy only local web.
set -eu
prooflane_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$prooflane_root"
prooflane_zod_version=$(node -p "require('./apps/web/security-dependencies.json').zod")
prooflane_resolver_version=$(node -p "require('./apps/web/security-dependencies.json')['@hookform/resolvers']")
prooflane_security_run="zod-$(date -u +%Y%m%dT%H%M%SZ)-$$"
prooflane_security_output="$prooflane_root/artifacts/security/$prooflane_security_run"
mkdir -p "$prooflane_security_output"
cd "$prooflane_root/apps/web"
# npm generates authentic resolutions/integrity values; don't hand-edit the lock.
# No force flag, peer-dependency bypass, audit suppression or broad update.
npm install --save-exact "zod@$prooflane_zod_version" "@hookform/resolvers@$prooflane_resolver_version" --no-fund
node scripts/check-dependencies.mjs
npm audit --json > "$prooflane_security_output/npm-audit.json" || {
    cat "$prooflane_security_output/npm-audit.json"
    printf '\nAudit did not pass. Report: %s\n' "$prooflane_security_output/npm-audit.json" >&2
    exit 1
}
npm run test:unit
cp test-results/unit-report.json "$prooflane_security_output/frontend-unit-report.json"
npm run build
cp package.json "$prooflane_security_output/package.json"
cp package-lock.json "$prooflane_security_output/package-lock.json"
cd "$prooflane_root"
docker info >/dev/null
docker compose build web
docker compose up --no-build --no-deps -d --wait --wait-timeout 180 web
cd "$prooflane_root/apps/web"
export E2E_OUTPUT_DIR="$prooflane_security_output/browser"
export E2E_JSON_REPORT="$prooflane_security_output/browser-report.json"
npm run test:e2e
printf '\nSecurity migration and browser checks passed. Reports: %s\n' "$prooflane_security_output"
