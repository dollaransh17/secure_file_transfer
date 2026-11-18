# Current update: Claude, workload models, AWS, and UI

## Current verified result

The final host rename/CSP retest passed **desktop and mobile, 2/2**, in 29.904 seconds total. Twenty-six frontend unit tests passed. Both browser diagnostics show zero page errors/CSP violations and successful rename/logout requests. The rebuilt web image is healthy. The recorded dependency audit has zero vulnerabilities with Zod 4.6.7 and resolvers 7.0.6.

Preserved reports and their original run references: `benchmarks/results/browser-final-20261114`. Earlier migration/failure/retest commands below remain reusable history; the current tested web corrections are complete. Broader security race testing, research experiments and AWS deployment remain outstanding. See `docs/STATUS.md` for the current evidence rather than interpreting historical pending entries as current failures.

## Latest: clean dependency audit; mobile rename retest

The host security migration completed installation, real lockfile generation, an actual **zero-vulnerability npm audit**, 18 unit tests and the rebuilt web image. The post-upgrade desktop scenario passed; mobile failed waiting for rename within five seconds. The original diagnostic captured no page error but did not capture PATCH status.

The current frontend updates names only after server-confirmed rename, cancels stale detail/list reads and exposes pending/error state. Tests now await the intended PATCH request/response before asserting the heading. A dropdown SVG blocked by the existing CSP was moved to a same-origin static asset without relaxing CSP. Twenty-six frontend unit tests, dependency consistency, production build and browser discovery passed locally. Run only:

```sh
./scripts/retest-browser.sh
```

This rebuilds web and reruns desktop/mobile using existing API/models. No dependency reinstall or Claude request is necessary. Preserve `artifacts/security/zod-20261114T112316Z-7635` and copied reports under `benchmarks/results/zod-upgrade-20261114`; these include the actual clean audit and the prior one-pass/one-failure browser result. The current mobile correction is not yet live-verified.

## Current security dependency migration

The audit identifies [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5), affecting Zod below 4.6.6. The reviewed targets are Zod 4.6.7 and `@hookform/resolvers` 7.0.6, whose published metadata supports Zod 4 and React Hook Form `^7.55.0`; the existing installed form package is 7.92.0. Run:

```sh
./scripts/fix-web-audit.sh
```

The script installs only the reviewed dependency targets with npm, producing authentic lockfile resolutions/integrity values; verifies manifest/lock/installed versions; saves the actual audit JSON; runs form/resolver/session tests and production build; rebuilds/recreates only web; then runs desktop/mobile against the existing API/models. It does not force peer resolution or suppress advisories. Reports go under `artifacts/security/zod-<timestamp>-<pid>`.

The manifest and validation code are prepared. Registry DNS blocked installation in the coding sandbox, so the current lockfile/modules remain old and the fix is **not yet applied or verified**. The guard intentionally prevents ordinary builds/unit commands from silently using those versions. Eighteen direct contract tests passed on the old dependency installation; that proves only baseline input/error behavior and guard fixtures, not the patched integration. The prior successful browser report remains a pre-migration baseline. See [Zod's migration guide](https://zod.dev/v4/changelog) and [resolver release/source metadata](https://github.com/react-hook-form/resolvers/releases).

## Latest result

The corrected browser retest passed: **desktop and mobile, 2/2**, 23.058 seconds total. Seven frontend unit tests passed, and web rebuilt/restarted healthy. Both diagnostics confirm server logout, session denial, invalid-password rejection and subsequent valid login, with zero page JavaScript errors. Reports are preserved in `benchmarks/results/browser-logout-20261114-passed`. Claude's corrected integration already passed its 14 focused tests and all three live checks.

The earlier pending steps below are retained as reusable commands; logout validation is now complete for these tested cases. The host npm install reported one high-severity vulnerability. Its exact advisory remains unresolved because the agent's audit request failed registry DNS; this and broader security/research validation remain outstanding. See `docs/STATUS.md` for current evidence and limitations.

## Current next check: browser logout

The citation correction passed its 14 focused tests and all three live Claude checks. Browser tests passed the file, version, exact download, scheduler and page-navigation assertions before failing at logout. Apply the frontend correction and rerun only the browser suite:

```sh
./scripts/retest-browser.sh
```

This runs seven browser-free frontend unit tests, rebuilds/recreates only web, then runs desktop/mobile against the existing API and workers. Logout awaits actual server revocation before loading a fresh document. Failed logout requests show an error and remain retryable. The browser test additionally verifies the logout HTTP response and denial of `/api/auth/me`, and preserves screenshots plus sanitized browser-error/auth-status diagnostics. It makes no Claude requests or model-training runs. Logs/screenshots remain in a distinct `apps/web/test-results/logout-<timestamp>-<pid>` folder. Full live correction remains unverified until this host retest passes.

## Repeat the API and browser corrections

The earlier full suite passed ten groups and failed citation/status checks; those corrections have since passed focused host checks. The current remaining browser issue is logout. To repeat API/citation checks as well as applying the latest frontend correction:

```sh
./scripts/retest-fixes.sh
```

This rebuilds API, runs focused citation regression tests, recreates API, runs Claude checks, then rebuilds web and runs frontend unit plus desktop/mobile checks. It reuses existing trained models and leaves workers running. Both live suites are attempted even if one fails. The Claude output schema offers only authorized event IDs; the server validates each claim, appends citations and rejects unknown IDs. At most one extra billable format-repair request is made, with actual token counts accumulated across responses. The post-network permission check remains mandatory. See the [official tool-use format](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) used for the SDK request; this tool only formats a response and executes no security action.

## Run all existing test suites

With the local services running, existing images built, web dependencies installed and Playwright Chromium available:

```sh
./scripts/test-all.sh
```

This aggregates syntax/Compose checks, backend pytest, model tests, AWS template lint, real security/model/Claude smoke runs, frontend build and the desktop/mobile browser flow. It writes `artifacts/test-runs/<id>/report.json` and separate logs. Failed and blocked checks both cause a nonzero exit; previous host successes are not substituted for fresh runs. No models are retrained and no AWS resources are created. The Claude smoke requests one explanation using synthetic event metadata, with at most one extra billable format-repair request.

The agent's latest attempt passed five groups (including 65 tests and the frontend build); seven groups were blocked by Docker/Chromium permissions. The browser-control access host was also unavailable. Full report: `artifacts/test-runs/20261114T102523Z-c9043274/report.json`. The expanded desktop/mobile assertions were discovered but not executed past browser startup. Existing host live reports remain separately documented.

## What can run locally now

From the project root with Docker Desktop running:

```sh
./scripts/update-local.sh
```

This builds the revised API/frontend, executes the backend suite, applies migrations, recreates services with the current `.env`, checks the configured Claude model against the account, lints AWS templates in an isolated container, runs genuine model smoke tests, trains LightGBM and TGN on the causal synthetic workload, writes a paired five-scheduler held-out comparison, and replaces only the worker images with their ML-enabled image. It then runs a live model-decision/antivirus check in a new isolated workspace. It never creates AWS resources or uploads a key to AWS.

The model check uses `models.retrieve` through the official Anthropic SDK; it does not send file data or a generation prompt. Without a supported/configured Claude model the rest of the workflow continues independently. `scripts/check_claude.py --probe` is an optional short generation probe with token accounting, not part of the default update.

Training defaults to ten epochs with validation-based early stopping for TGN. Use `PROOFLANE_TRAIN_EPOCHS=2 ./scripts/update-local.sh` for a shorter initial pipeline check, or `PROOFLANE_TRAIN_MODELS=0 ./scripts/update-local.sh` to defer model training explicitly. A short check is not a research-quality performance study. The first research image build downloads CPU PyTorch/PyG/LightGBM dependencies. Epoch logs are actual measured losses, not placeholder progress.

After successful training, model manifests and their real held-out metrics appear in Research Lab. Select **Import latest run** to save the actual `artifacts/results-v2/results.json` report in the current workspace; imports are idempotent and tenant-scoped. Choose one available algorithm in Verification Queue to activate its workload ordering. The gateway remains deterministic.

The seed-17 training and comparison have now completed. To activate/check these existing weights **without retraining**, run:

```sh
./scripts/check-models.sh
```

This restarts only workers using the already-built research image, waits for the containers to start, and exercises each model in a new development workspace. It checks finite predictions, the actual checkpoint ID, absence of fallback, real clean scans/exact downloads and real EICAR quarantine/denial. It saves a credential-free `artifacts/live/ml-smoke-<id>.json` report. The saved host run `ml-smoke-ddd6c2577d9f4006a4c9e7dc0f2d3509.json` passed both methods/eight actual decisions in 49.150 seconds. This establishes functional integration, not ranking quality. Its agent rerun remains blocked by Docker socket permissions.

For one real, billable Claude explanation through the application (not just model availability), run:

```sh
./scripts/check-assistant.sh
```

This uses the running API's configured key, creates isolated accounts, scans a harmless EICAR fixture with real ClamAV, and asks about its recorded quarantine. It verifies actual token usage, authorized citation identifiers, cross-tenant exclusion and removal of evidence after permission revocation. Uploaded bytes, credentials and arbitrary file metadata are not sent to Claude. The host run passed all three checks in 12.701 seconds with Haiku, using 527 input and 315 output tokens. Its report is preserved at `benchmarks/results/assistant-smoke-2ccbab75846548adacc5caf4d4649368.json`. The earlier agent attempt was blocked by Docker permissions; the passing host result supersedes the pending live validation. If a future run reports unconfigured, recreate the API after changing `.env`.

For browser checks and desktop/mobile screenshots against the real localhost application:

```sh
./scripts/check-browser.sh
```

Screenshots and JSON results are written under `apps/web/test-results/run-<timestamp>-<pid>`.

On 14 November, existing host dependencies allowed a fresh attempt. Chromium failed before page navigation because sandboxed macOS Mach-port registration was denied. The previous saved summary reported passed. Future `check-browser.sh` runs use separate timestamped output directories and JSON reports so a failed attempt preserves earlier output. The frontend build now passes locally after scoping TypeScript ambient types to the browser project.

## Model and workload integrity

The earlier synthetic v1 generator made previous target labels available too soon. It must not be used for model training. Existing v1 deterministic scheduling reports remain historical simulation artifacts; no ML superiority was established by them.

Synthetic v2 generates authorized request timestamps and a fixed historical FIFO service trace. Features read only requests, starts and completions observed strictly before the scheduling timestamp. Future counts and completed service times are labels, purged at split boundaries until mature. Cooldown intervals between workload families allow queue drain and target maturity. The full workload has 3,600 samples; the validated default temporal split contains 1,800 training, 240 validation and 720 test rows after purging. The last family introduces new logical files/users. Context snapshots use stable typed identities, timestamps and bounded history; uploaded file contents are never model features.

Training publishes a model identity derived from checkpoint hashes. Availability requires matching hashes, feature names, horizon and graph input schema. Incomplete, incompatible or changed files are unavailable and workers fall back. If retraining replaces weights before the new atomic manifest is published, hash mismatch causes temporary deterministic fallback. No untrained scores are presented as TGN predictions.

The new comparison uses held-out rows only, identical resources/deadline/fairness rules, and cached arrival-time predictions for both learned methods. It measures prediction overhead separately and does not add it to simulated delay. Queue wait is not an observed end-user download delay. Single-seed synthetic comparisons do not establish real-world generalization, policy-invalid release rates under faults, or statistically significant superiority. Use `--ablations` with `python -m ml.pipeline` for the memory/attention ablations. Repeated seeds and full integrity-monitoring comparisons remain necessary.

## AWS

See `infrastructure/aws/README.md` and generated `template.json`/`repositories.json`. The package includes private RDS/Redis, ECS services, versioned SSE-KMS S3, SQS event/dead-letter handling, CloudWatch and TLS ingress. Database/Redis URLs are constructed from injected secrets; the RDS certificate is verified against the AWS CA bundle. No key is hardcoded into frontend code or a deployment template.

The agent could not refresh the configured AWS identity because the sign-in endpoint is unreachable from the coding sandbox. No authenticated account validation or deployment was performed. Region, domain, ACM certificate, image digests, secret ARN and explicit cost approval remain prerequisites to provisioning. Do not execute a deployment with example parameter values.

## What was actually verified for this update

- Host core pytest: 85 passed, 4 skipped, 28 passing subtests; frontend TypeScript/Vite build passed.
- Host Anthropic account check: configured model retrieved successfully without printing the key or generating an answer.
- Host cloud template lint passed; no AWS API calls or provisioning performed by that check.
- Host CPU model suite: all three tests passed; genuine LightGBM and TGN trained and produced a five-method held-out comparison.
- 65 dependency-free tests passed, including graph causality, checkpoint integrity, S3 notification parsing, AWS structural/dependency checks and live-model/Claude-response validators.
- Python compilation, shell syntax and Compose configurations passed.
- Default v2 workload split sizes and causal snapshots checked locally.

Saved report: `benchmarks/results/synthetic-v2-seed-17`. LightGBM had lowest mean simulated wait, EDF fewest misses, and TGN performed slightly worse than FIFO. Both models underpredicted held-out demand; TGN inference overhead was substantial. See `docs/STATUS.md` for measured numbers and their limits. The saved host live-model and Claude checks passed. Browser visual review, broader research/security validation and AWS deployment remain incomplete. The coding sandbox still cannot access Docker or host application ports; the host logs and generated artifacts establish the reported runs.
