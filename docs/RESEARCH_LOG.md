# Research log

## Explicit mock CNN display — 18 November 2026

User requested a mock CNN and explicitly required it not alter ClamAV decisions. Added opt-in CNN_MODE=mock (default disabled), enabled only in the ignored prepared hybrid environment. No trained network or actual inference is claimed: stable arbitrary demo_class_a/b scores are derived from the stored digest and labeled synthetic, not malware probabilities. Worker successful scan completions record exact-version/digest/generation-bound MOCK_CNN_ANALYSIS events; an owner-only CSRF-protected endpoint can generate an example for existing current versions. Neither path changes status, scan/integrity evidence, ACLs or release checks. Mock events are excluded from Claude evidence retrieval. The file inspector displays a CNN demo tab, disclaimer and existing-file generation button. No extra AWS services or ML dependencies are added.

Validation: 37 API/cloud configuration tests passed and TypeScript/Vite build passed. New tests confirm clean approval remains downloadable, infected content remains quarantined after mock analysis/regeneration, pending versions stay held, replacement versions do not reuse previous mock evidence, cross-tenant generation is denied, disabled mode rejects generation and Claude retrieval excludes mock events. Unit tests use explicit scanner/storage doubles. Host restart/live UI verification remains pending; previous live security/browser passes predate this feature.

## Docker engine check timeout — 18 November 2026

Host reports Ctrl+C after readiness followed by a 20-second Docker-info timeout on restart. AWS preflight still passed. Changed engine preflight to the narrower server-version query, retaining the bounded timeout, and added specific Docker Desktop recovery guidance. No Docker restart, container/data deletion or AWS changes were performed. Agent Docker/ps access is denied, so host engine health remains unverified. Launcher safeguard suite: 14 tests and 23 subtests passed. User must verify Docker Desktop responds and restart the foreground app before the new Storage tab is live.

## Owner-visible filename-to-S3 mapping — 18 November 2026

Added a Storage tab to the owned-file inspector showing the unchanged Prooflane filename, current logical version, exact storage key/object-version ID, and S3 bucket/region/URI when applicable. A console link selects the key and S3 version for real AWS endpoints; it is not a signed download link and requires separate AWS console authorization. Existing mappings work without reupload. Backend location metadata is returned only after normal file authorization and only to its owner; shared readers receive no new bucket metadata, and local filesystem paths/credentials are never exposed. No object renaming or storage mutation is performed.

Validation: 29 API tests passed (explicit local storage/scanner doubles), including owner mapping, cross-tenant denial and shared-reader metadata exclusion; TypeScript/Vite production build passed. The real workspace E2E now asserts the Storage tab and recorded key but has not been rerun after this change. Host launcher restart and live UI verification remain pending. Prior revision reports now confirm seven real security checks and six desktop/mobile browser tests passed; those do not validate this new tab.

## Hybrid browser loading and AV timeout diagnosis — 18 November 2026

Inspected host live smoke: six checks passed, including exact-version ClamAV CLEAN evidence and downloads, sharing/revocation, cross-tenant denial and V2 replacement. The EICAR phase failed with httpx ReadTimeout after 77 seconds total; it does not establish quarantine success or a scanner defect. API logs have no completed third-upload line. Browser results: four failures/two passes; both void-scroll cases timed out in initial page.goto (before chat), desktop workspace registered successfully but remained Connecting at its five-second assertion, mobile workspace had blank document/HTTP 400 and never reached registration. No page exceptions/CSP violations were reported. Root cause of these transport/loading stalls remains unproven.

Launcher now builds the frontend with the sanitized frontend environment and serves built assets via loopback Vite preview with the API proxy; no cold module transforms/HMR during browser acceptance. Browser setup checks navigation HTTP 200, explicit auth readiness, registration HTTP status and bounded workspace rendering. No assertions skipped or retries added. Live smoke now isolates EICAR upload/poll/evidence/download phases, reports sanitized method/path/error/elapsed time, records returned AV IDs, and allows a separate bounded 90-second upload read budget (regular requests remain 30 seconds). Upload timeouts are explicitly unconfirmed and are not automatically retried. No release/ClamAV decision logic or IAM grants were relaxed.

Validation: 58 focused Python tests and 23 subtests passed, 36 frontend unit tests passed, TypeScript/Vite build passed. These include explicit transport/scanner doubles, not new live AWS or browser passes. Agent loopback/browser access remains unavailable. Host must stop/restart the launcher and rerun live smoke plus serial desktop/mobile tests; quarantine and full current browser acceptance remain pending. Original available failure artifacts preserved under artifacts/hybrid-review-20261118.

## Host hybrid application ready — 18 November 2026

The user reports Docker Desktop available, isolated hybrid PostgreSQL/Redis/ClamAV healthy, migration completed, and the launcher ready at http://localhost:5174 with API and two separately authenticated workers. The AWS identity/versioning/source-queue configuration preflight passed. Agent browser creation failed because the browser access host is unavailable; completion was recorded. Direct loopback health checks with proxies disabled were denied (PermissionError errno 1) by the tool environment. These are agent access limitations, not evidence of application failure. Actual AWS-backed upload/scan/share/revoke/EICAR and desktop/mobile browser acceptance remain pending host execution of live_smoke.py and direct Playwright tests. Avoid legacy Docker rebuild helpers, which target the old MinIO stack.

## Host AWS preflight passed; local startup diagnosis — 18 November 2026

The user reports successful expected API/worker identity, S3 bucket-versioning and SQS encryption/redrive checks after adding source-login regions. Startup then fails with CalledProcessError and no Compose output, suggesting the captured Docker engine check; the original output did not identify the failed stage conclusively. Agent Docker access is denied by the tool environment, so host Docker health is not independently known. Launcher now prints each local startup stage and reports Docker-engine, Compose, migration, missing-executable and timeout failures separately. It does not echo captured provider/environment data. Focused validation: 25 tests and 23 subtests passed. User should start Docker Desktop, verify docker info in host Terminal, then retry. No running hybrid application or live S3 file acceptance is claimed yet.

## Credential bridge region correction — 18 November 2026

Host startup reported `CredentialRetrievalError`. Both login profiles have the expected IAM users but no saved region. Captured CLI diagnostics (credential stdout suppressed) confirmed `export-credentials` fails with `You must specify a region` without an explicit region; with `--region ap-south-1` it advances to an endpoint connection failure in the agent environment. Runtime-access setup now saves each login profile region and pins the region in new bridge commands. Launcher errors identify missing region or expired login using fixed messages without echoing provider output. Focused verification: 22 tests and 19 subtests passed. User must apply the two local region settings in host Terminal; no profile files, AWS permissions or resources were changed by the agent. Live startup remains pending.

## Guarded AWS hybrid startup — 18 November 2026

User worker STS evidence now names the correct IAM worker. Local configuration confirms separate API/worker process-credential bridges. Implemented an executable host launcher with expected-principal/account guards, mandatory versioning and SQS encryption/redrive checks, local-only service targets, isolated infrastructure, secret-separated child environments and owned-process cleanup. It does not modify AWS infrastructure, grants or model behavior. Current focused tests: 20 passed / 19 subtests; dependency-free suite: 103 passed. Explicit client doubles cover failed identity/security-state cases, not real AWS acceptance. The agent's live preflight stopped on credential retrieval before local startup. No successful AWS object upload, queue-consumer run, cloud release test or new cost/model measurement is claimed. Operator startup remains necessary in the host terminal.

## Host-reported infrastructure creation — 18 November 2026

The supplied terminal evidence shows stack-create-complete and the expected bucket, source queue/DLQ and access-policy outputs. Recorded it explicitly as host-reported creation, not independently verified agent execution or application acceptance. Filled a private 0600 hybrid configuration with the non-secret resource identifiers while preserving `.env`; database credentials and restricted runtime logins remain to configure. Documented IAM-user temporary browser logins and the official SDK process-credential bridge to avoid the missing Boto3 CRT dependency. No access keys, passwords, IAM attachments, live cloud upload, queue-consumer test, model training or measured bill was created/reported by the agent.

## Host-reported AWS template validation — 18 November 2026

User terminal output shows successful authenticated CloudFormation ValidateTemplate in Mumbai for the minimal S3/SQS template, with the expected project parameter and IAM acknowledgement. This is a template-validation result, not deployed infrastructure or evidence of working S3/KMS/SQS integration. The agent could not independently reach STS. The user's temporary CLI login is a root principal; restricted application/worker runtime identities are still required. No new tests, AWS provisioning or workload/cost measurements are claimed.

## Minimal S3-to-SQS event path — 18 November 2026

Added the requested SQS source/DLQ and scoped S3 publishing/worker consuming permissions to the minimal CloudFormation artifact. Kept SQS-managed queue encryption to avoid an additional KMS key; retained SSE-KMS for file storage. Resolved the bucket/notification-policy creation dependency with independently computed stack-derived names and verified ARN equality and acyclic dependencies. Updated hybrid worker configuration and cleanup/cost documentation. Existing event consumers reconcile idempotent exact-version work into PostgreSQL; scheduler and release authority did not change. Current 94 dependency-free checks passed; no schema/live AWS validation or measured SQS workload was executed. Earlier four-resource records are historical, not the current template.

## CloudFormation artifact — 18 November 2026

Finalized the minimal JSON CloudFormation template's setup outputs and operator instructions. It still declares exactly four resources and uses the AWS-managed S3 encryption key; local application/research semantics are unchanged. Eight focused structural tests passed. Schema lint could not run because the environment's package installation did not resolve cfn-lint. No authenticated AWS validation, deployment, security smoke, cost measurement or model experiment was performed. This is infrastructure preparation, not evidence of cloud acceptance or a research contribution.

## Minimal cloud option — 17 November 2026

Prepared optional S3-only hybrid infrastructure in response to the personal-account $1 limit. Four template resources cover private versioned SSE-KMS storage and unattached access policies; AWS-managed encryption avoids creating customer-managed keys. Compute, queue, application audit records, database and ML remain local. This is an application of existing AWS mechanisms, not a new security/ML contribution. No account credentials, AWS APIs, IAM attachments, provisioning, cloud workload results or paid resources were used. No hard spending cap or full cloud acceptance is claimed. Current local checks and blocked AWS/adapter validation are recorded in STATUS.md and the minimal runbook; the original full template is optional.

## Native browser review and invalid-session recovery — 14 November 2026

The browser-extension host remained unavailable, but native Safari access worked. Opened the actual login screen and observed live Research Lab checkpoint IDs/metrics and the current tenant's empty EDF queue/configured capacity. Window changes interrupted fixture sign-in/import attempts; an unrelated application sign-in prompt was not acted upon. Brave fallback encountered accessibility/window errors. These are partial manual observations, not another complete pass. No raw unrelated browser/authentication state was saved into the project.

Observed the scheduler retain its private layout with “Session expired” after invalidation; refresh returned to login. Added current-session-only HTTP 401 recovery for API/upload calls, excluding public auth failures and logout's own transition. Older responses cannot clear a newer session; concurrent denials trigger one transition; permission/rate/server errors retain their own behavior. Ten new Node-only cases passed: **36 frontend unit tests** total, plus **77 Python dependency-free tests**, build/dependency checks and browser discovery. An expanded real E2E case revokes only its own fixture session through the normal endpoint and checks automatic UI recovery; it remains pending host deployment. See `docs/MANUAL_BROWSER_REVIEW.md` for scope and limits.

## Current browser rename/CSP verification passed — 14 November 2026

Inspected host `logout-20261114T113943Z-14418/report.json`: desktop/mobile **2/2 passed**, 29.904198 seconds total, zero unexpected/skipped/flaky cases. Both diagnostics have zero page errors and zero CSP violations, with successful rename PATCH and logout HTTP 200. All remaining version/download/login/persistence assertions passed. Host frontend unit report: **26 passed**, 8.143684 seconds. Production image build completed and web reported healthy.

Preserved the actual browser/unit reports plus the preceding zero-vulnerability npm audit and explicit source/run references under `benchmarks/results/browser-final-20261114`. This closes the tested rename/CSP/browser correction; it does not imply a fresh consolidated backend/research suite pass, comprehensive concurrency validation, model superiority or AWS deployment. Research/production limitations remain listed in `docs/STATUS.md`.

## Patched dependency audit verified; rename/CSP correction — 14 November 2026

Read actual host migration artifacts `artifacts/security/zod-20261114T112316Z-7635`: Zod 4.6.7, resolvers 7.0.6, genuine synchronized npm lock, **zero npm vulnerabilities**, 18 patched-library form/dependency/session tests passed, and successful production image build. The post-upgrade desktop scenario passed; mobile failed at the rename heading after a five-second wait. No page errors were captured and the snapshot retained the old name with the new input value. Original diagnostics omitted PATCH status, so the exact rejection/timing cause is not established. Preserved actual audit, dependency snapshots and reports under `benchmarks/results/zod-upgrade-20261114`.

Changed rename metadata caching to update only after an HTTP-success/ok confirmation, cancel stale detail/list reads and reconcile those queries. Pending rename state prevents duplicate rename submission; security/version fields remain untouched. Eight new real QueryClient unit cases cover delayed confirmation, rejected/unconfirmed requests, stale reads and uncached data. Browser assertions now wait for PATCH confirmation and verify intended payload, and diagnostics capture mutation method/path/status without bodies or credentials.

The passing desktop log also revealed CSP rejecting a dropdown's inline SVG data URL. Replaced it with a same-origin static SVG, preserving the policy; browser tests now reject CSP violations. Verified the built CSS no longer contains SVG data URLs and the static asset is copied correctly. **26 frontend unit tests** pass against the patched dependency tree; TypeScript/Vite build, dependency guard and browser discovery pass. Rollup's Zod annotation warning is non-fatal and its comment is removed by the bundler; no dependency-source patch or blanket warning suppression was applied. Current mobile/CSP live correction awaits `scripts/retest-browser.sh`; no successful rerun is claimed.

## Zod advisory and staged migration — 14 November 2026

Host `npm audit` identified Zod <4.6.6, GHSA-mrhx-c7xc-m3w5. Verified the advisory/migration guide and resolver source/releases. Read actual cached npm packuments: Zod 4.6.7 and resolvers 7.0.6 exist; the latter supports Zod `^3.25.0 || ^4.0.0` and React Hook Form `^7.55.0`, compatible with the installed form package 7.92.0.

Pinned those target dependencies in the manifest and raised the form minimum. Extracted the real credential schema with backend-aligned string bounds, added actual resolver error/success cases and manifest/lock/installed consistency tests. Added prebuild/pretest guards, switched the web image to `npm ci`, and prepared `scripts/fix-web-audit.sh` for exact npm installation, genuine lock generation, actual audit, regression/build checks, web recreation and browser retesting. It neither forces peer dependencies nor suppresses the advisory. No AWS/model changes.

Normal installation failed registry DNS; offline lock-only resolution also failed cache eligibility and no patched tarballs were available. The real lockfile/modules remain old; no package integrity data was fabricated. The guard correctly rejects that state. Eighteen direct contract tests and source typechecking passed against the existing legacy installation, not the proposed Zod 4/resolver 7 integration. Preserved this explicitly labelled evidence under `benchmarks/results/zod-migration-prepared-20261114`. Patched installation, fresh audit, version-gated tests/build and post-upgrade browser checks remain pending host execution. The vulnerability is not declared fixed.

## Desktop/mobile browser completion — 14 November 2026

Inspected actual host report `apps/web/test-results/logout-20261114T110253Z-96696/report.json`: desktop/mobile both passed in 23.058 seconds total, zero unexpected/skipped/flaky cases. The seven frontend session unit tests passed in 0.811 seconds and the host web image built/restarted healthy. Preserved both reports under `benchmarks/results/browser-logout-20261114-passed`.

Both attached diagnostics have zero page errors and confirm logout HTTP 200, subsequent session lookup HTTP 401, invalid-password login HTTP 401, and valid login/session lookup HTTP 200. All preceding assertions for real uploads, approvals, SHA-256, exact V1/V2 downloads, preview, rename/history, scheduler choices and eight-page navigation passed. Reviewed the corrected mobile Files and loaded desktop Research screenshots: no transitional drawer overlay; actual model IDs and metrics are available. No new agent-driven browser access or concurrency-test claim is made.

The Docker web build reported one high-severity npm finding. An agent `npm audit --json` attempt failed DNS reaching the npm advisory endpoint; the exact package/advisory is not established. No blind forced upgrade or clean-audit claim was made. This remains an explicit security follow-up alongside the broader research/production limitations. Browser success does not establish complete project/research acceptance.

## Claude correction verified; browser logout continuation — 14 November 2026

Host output confirms the corrected API image built, 14 focused citation tests and 15 subtests passed (6.29 s), and the real Claude smoke passed all three cases. Inspected/preserved `assistant-smoke-5d2d2c34fdab437e91d1bb04a0f475fe.json`: 15.680320 seconds, 1,583 input / 215 output tokens, authorized server-rendered citations, cross-tenant exclusion and post-revocation denial. These token counts replace no earlier measurement; they are a new run with schema overhead.

The host desktop/mobile tests passed preceding assertions through V1/V2 approval/digests/exact bytes, preview, rename/history, scheduler selection and navigation, then failed at the signed-out heading. The failure artifacts did not capture the logout HTTP status or browser exception; its precise mechanism remains uncertain. Changed logout to server-confirmed revocation followed by a fresh document rather than clearing global query state during mounted-view transition; failures are caught and presented for retry. Added seven Node-only frontend tests covering pending confirmation, expired session, CSRF/rate-limit/server rejection and network errors; all passed. Frontend production build and desktop/mobile discovery passed. Browser tests now verify logout response/session denial and attach sanitized error/status diagnostics and screenshots on failure. No new successful live logout is claimed.

Reviewed five actual host screenshots: desktop Files/Assistant/Research and mobile Files/Assistant. Corrected misleading untrained/evidence-only labels during initial data loading and waited for mobile drawer transitions in screenshots. A DOM-emulator dependency install for deeper local reproduction failed DNS; it added no application dependency, and the existing Playwright runner executes the seven Node-only tests without Chromium. Added `scripts/retest-browser.sh` to rebuild only web and repeat the live browser checks with existing API/models. Test reports are excluded from image build contexts. AWS and model training were unchanged.

## Host full-suite failures and corrections — 14 November 2026

Inspected host run `20261114T102718Z-6de30f75`: ten groups passed, two failed, none blocked. Actual backend output: 94 passed, four skipped, 44 passing subtests in 20.40 seconds; research suite: three passed in 29.81 seconds. Preserved report, these test logs and both failure logs under `benchmarks/results/full-suite-20261114-6de30f75`.

The browser snapshots show actual lowercase `approved`, CLEAN evidence and ClamAV metadata; the assertion expected title-case `Approved` and waited three minutes. Corrected both V1/V2 checks to assert the current detail badge case-insensitively. No approval logic or scanner requirement changed. The later browser assertions still await live execution.

Claude returned `unavailable:ValueError`. The citation validator is an explicit local ValueError path, but the rejected raw response was not retained, so its exact formatting/ID issue is unknown. Replaced free-form citation extraction with a read-only, schema-defined output tool, authorized event-ID enum, per-claim server validation and server-rendered references. Confirmed request/response shape against official Anthropic tool-use documentation. No external action is exposed or executed. Added one bounded format repair, retaining both responses' actual token counts even if validation fails. Unknown references continue to fail closed, and the post-network authorization recheck remains in place. Semantic entailment remains unproven.

Twelve new dependency-free cases cover authorized tool output, canonical/fenced formatting, unknown/version IDs, embedded citations, malformed/excessive claims, unexpected tools, bounded repair and token accounting. Total **77 passed** locally; Python compilation, frontend build and desktop/mobile discovery passed. Added an API regression for failed validation and actual usage retention; that pytest/live path cannot run in the restricted Docker workspace. `scripts/retest-fixes.sh` rebuilds API, tests these changes, recreates API and attempts both failing suites using existing models. Its local attempt was denied Docker socket access. No successful live correction is claimed yet.

## Full-suite execution attempt — 14 November 2026

User requested opening the website and performing all tests. Browser control returned "The browser access host is unavailable"; Docker daemon probing was denied by the OS sandbox and localhost was inaccessible. No website interaction or visual inspection occurred.

Added `scripts/test-all.sh` / `test_all.py` to run existing suite groups with separate logs and honest blocked/failure reporting, preserving previous outputs. It uses current source/test bind mounts for container tests, clears provider credentials in unit-test containers, and retains real configured-provider behavior only in the isolated live Claude check. It neither builds infrastructure nor retrains models. Expanded the desktop/mobile scenario to assert real approval, SHA-256, exact file bytes, preview, rename, immutable replacement/history, scheduler choices, all eight pages, logout/bad login and persisted sessions; those new live assertions remain unverified.

Latest orchestration run: `artifacts/test-runs/20261114T102523Z-c9043274/report.json`, **five groups passed / seven blocked**. Python compilation, 65 dependency-free tests, all shell syntax, Compose normalization and TypeScript/Vite build passed. Six Docker-backed groups were blocked before suite execution. Both Playwright projects failed at Chromium startup due denied Mach-port registration and were classified as blocked, with raw failure logs retained. Playwright test discovery succeeded. These fresh attempts do not supersede or inflate the earlier host passing reports.

## Host Claude generation milestone — 14 November 2026

The user executed `./scripts/check-assistant.sh` and supplied three passing checks. Inspected the actual report `artifacts/live/assistant-smoke-2ccbab75846548adacc5caf4d4649368.json`, checked its citation/token structure and preserved an identical copy under `benchmarks/results`. All three cases passed in 12.701378 seconds: cross-tenant evidence excluded without generation, real authorized Claude explanation with event references and actual usage, and removal of assistant evidence/new download authorization after revocation.

Configured model: `claude-haiku-4-5-20251001`; actual usage 527 input / 315 output tokens. The real ClamAV fixture reached quarantine. The answer acknowledged that the supplied records do not establish the underlying antivirus cause, rather than inventing it. This is scoped functional evidence, not proof of semantic entailment, comprehensive prompt-injection resistance or research completion. No key was exposed or copied into the report; no AWS provisioning was performed. The earlier agent Docker permission block remains an environment limitation, now separate from the successful host generation result.

## Agent execution and artifact review — 14 November 2026

User explicitly authorized running the model/browser/Claude checks with the configured key. `check-models.sh` and `check-assistant.sh` were attempted but the OS sandbox denied Docker socket access; no new live run or Claude generation was performed. No escalation or alternative route around those restrictions was used.

Inspected the existing host-generated `ml-smoke-ddd6c2577d9f4006a4c9e7dc0f2d3509.json`: both model checks passed, eight actual decisions match the current checkpoint identities, clean exact downloads and real EICAR denial passed, elapsed 49.150490 seconds. Preserved this report under `benchmarks/results`. Multi-second scheduling measurements in this small run must not be confused with the separate batched synthetic inference measurements.

The existing Playwright `.last-run.json` reported passed and desktop/mobile screenshots were present. A fresh agent `npm run test:e2e` attempt could not launch Chromium: macOS denied Mach-port registration. That default-output rerun cleared the prior screenshots before the startup failure; they were not visually assessed. Updated the check script to preserve separate timestamped output and JSON reports on future runs.

`npm run build` initially failed because TypeScript discovered unrelated parent-directory ambient types (`node`/`three`). Explicitly scoped the web project's ambient types to React/React DOM/Vite; full TypeScript/Vite production build then passed. Playwright configuration/test discovery passed (desktop and mobile cases), not browser execution. Added a real application-level Claude smoke test for authorized citations/token counts and cross-tenant/revoked evidence denial; **65 dependency-free tests passed**, including its validator negative cases. Live explanation generation remains unverified.

## Latest host execution — 13 November 2026

The earlier entries below are chronological history and retain their original blocked status. Current evidence supersedes those blocks: the host core suite passed **85 tests with 4 skips and 28 passing subtests**; the isolated research image passed all **3 ML tests**; TypeScript/Vite built successfully; the configured Claude model was retrieved successfully from the account; and cloud template lint completed without AWS resource creation.

Read and hash-validated both trained checkpoints: LightGBM `7c8dc6549d00719b`, TGN `012b1b6623af2265`. Both trained on causal synthetic v2, seed 17, purged splits 1800/240/720. TGN completed ten epochs, retaining epoch 5 by validation score. Held-out duration MAE: 5.054 s (LightGBM), 4.297 s (TGN); demand MAE: 125.219 and 118.812, with large negative demand bias. This is evidence of actual training, not satisfactory demand estimation or a contribution claim.

The saved five-method, two-worker held-out comparison contains 720 jobs. LightGBM had lowest mean queue wait (676.681 s); EDF missed fewest deadlines (595). TGN was slightly worse than FIFO (mean 685.039 vs 685.001 s; 633 vs 630 misses). Comparison inference: 0.114 ms/job batched LightGBM versus 154.965 ms/job TGN, excluded from simulated queue wait. These findings argue against claiming TGN superiority from its smaller predictive MAE. One seed and synthetic service times do not establish real-world performance.

Preserved actual reports/manifests in `benchmarks/results/synthetic-v2-seed-17`. Added a live model-decision/real-antivirus smoke runner and a worker-only activation/check script, without retraining. Its live execution, browser automation, actual Claude explanation generation, repeated/ablated experiments, full integrity baselines and AWS deployment remain pending. No paid infrastructure was provisioned.

## 2026-11-13

**Inputs inspected:** `arch_secure.png` and `DOC-20261105-WA0025.pdf`. The root contained no application repository. The supplied diagram includes separate LightGBM and temporal-graph prediction branches, a safety scheduler, exact-version evidence, a release gateway and an explanatory Claude path.

**Existing techniques:** quarantine and antivirus; SHA-256; private versioned object storage; transactional authorization; evidence epochs; durable leased queues; FIFO/EDF; LightGBM; GRU temporal memory; time encodings; graph attention; permission-filtered RAG. Their use is not a novelty claim.

**Proposed integration:** combine version/epoch/generation-bound evidence with lease fencing, coalesced repair and learning-assisted workload ordering while keeping the release invariant outside model authority. This is an experimental systems design, not an established research contribution.

**Implemented source:** FastAPI security API, PostgreSQL schema/migration, S3/local adapters, real ClamAV wire client, queue workers and three deterministic schedulers, optional trained workload inference, TGN-inspired and LightGBM training code, experimental byte-image CNN, controlled-event Claude/BM25 integration, API-connected React pages, Compose, tests, harmless generator and simulation runner.

**Executed:** Python compilation; ten standard-library tests; generation of 200 harmless files/3,600 workload rows and 200 scenario definitions; 20 predicate-oracle conformance cases; FIFO/EDF/rule paired simulation. A generated PDF was rendered and visually inspected. Raw benchmark output is in `artifacts/results`; copied measured reports are in `benchmarks/results/local-seed-17`.

**Measured:** FIFO and EDF mean wait 1144.901263 seconds, P95 wait 4120.598507 seconds, 1684 deadline misses, utilization 0.311087845 on this synthetic workload. Rule mean wait 1144.869000 seconds, P95 4120.593523 seconds, same missed-deadline count. These are simulation values from synthetic service times, not real scanner measurements or evidence of research superiority.

**Blocked validation:** Docker socket access is denied by the workspace sandbox. PyPI and npm DNS requests fail; offline cache lacks required dependencies. Therefore pytest API integration, frontend typecheck/build, Playwright, real database/object store/ClamAV startup, ML training/inference execution, actual Claude invocation and dependency scans were not completed. No trained model, live end-to-end pass or publication readiness is claimed.

**Open hypotheses:** learned workload estimates may improve valid-download wait under constrained resources; version dependency repair may reduce redundant work at equal safety; attention/memory may help under workload changes. All remain unverified.


**Continuation:** Confirmed the frontend is not listening. Added real-stack startup/readiness diagnostics and Compose API/web health checks. Automatic approval rejected sandbox escalation for npm installation. Corrected train/serve graph inputs to a common causal bounded snapshot contract; real scheduler decisions now persist feature/graph snapshots for export. Eleven additional dependency-free tests passed (21 total). Tensor training, service startup and browser validation remain blocked and unclaimed.


**Host backend validation:** user-provided pytest output confirms 53 passed, 4 skipped, 1 non-fatal TestClient deprecation warning, and 28 passing subtests in 8.99 seconds. This suite uses scanner/storage doubles for API tests. Added a separate real-stack smoke runner; its source/helper checks passed, while its live path remains unexecuted. Models remain untrained.


**Live measured result:** inspected the host-produced smoke report: seven real-stack checks passed in 7.418906962 seconds, using ClamAV 1.5.4/signature database 28182. Pending holds, exact bytes/evidence, sharing/revocation, tenant denial, version replacement and EICAR quarantine were observed. This is a scoped functional milestone; concurrency and comparative research claims remain unverified. Prepared the separate CPU research image/profile for genuine tensor/training checks; it has not yet been built or run.


**Current source changes:** identified and repaired a synthetic feature leakage path (previous duration/demand labels were exposed before completion/maturity). Causal v2 uses strictly observed request/completion events, family cooldowns and held-out new files/users. Its purged partitions were checked (1800/240/720); no v2 model training or superiority result has been executed. Added checkpoint hashes, five-scheduler held-out comparison code, AWS templates/event inbox and a quieter UI. 56 dependency-free tests passed. New tensor/browser/cloud/provider runs remain pending; the earlier live baseline remains separately recorded.


## 16 November 2026 — host session-recovery browser verification

Inspected host run `logout-20261116T083827Z-53488`: desktop/mobile 2/2 passed in 24.090 s, no retries/skips/flaky cases, zero page JavaScript errors/CSP violations. The server-revoked fixture session returned to login on the next protected UI read without manual reload. Associated unit report: 36 passed, 1.238 s. Exact V1/V2 bytes, SHA-256, upload/approval, preview, confirmed rename, history, deterministic strategy changes and auth flows passed. Expected denied-auth requests generated 401 console messages. Preserved exact reports and session screenshots in `benchmarks/results/browser-session-recovery-20261116`. This closes the pending browser regression; no new Claude/ML/AWS/security benchmark or consolidated full-suite result is claimed.

## 16 November 2026 — consolidated agent run

Executed `./scripts/test-all.sh`; report `artifacts/test-runs/20261116T084214Z-6b555e3d/report.json`: 6 passed, 0 failed, 7 blocked. Passed syntax/configuration, 77 Python checks, 36 frontend unit tests and production build. Docker socket access was denied by the sandbox, blocking six container/live groups. Chromium was denied Mach-port registration before navigation, blocking browser execution. These are execution-environment blocks, not passing security/model/Claude results. The prior host 2/2 browser report remains separate. Host alternate-port full-suite runs must explicitly set `E2E_URL=http://localhost:5174` and retain the Compose port exports.


## 16 November 2026 — alternate-origin full-suite failures

Host consolidated run `20261116T084614Z-d1eecd96` passed 11 groups and failed backend/browser. All 27 API failures originated at registration: a fixed 5173 Origin conflicted with inherited Compose PUBLIC_ORIGIN 5174. API test configuration now pins its isolated origin before app construction, with additional negative/positive configured-origin cases. Browser snapshots show the detail dialog still loading at the five-second SHA-256 assertion; no API error or latency cause was established. The test now waits for and validates the actual detail response (30-second bound), and records read timing/status/transport failures. No fixed sleep, retries, relaxed CSRF or fake response was added. Local 36 frontend tests, 77 Python checks, build, syntax and browser discovery passed; corrected real backend/browser reruns remain pending under agent Docker/browser restrictions. Preserved logs and notes: `benchmarks/results/consolidated-20261116-origin-loading`.


## 16 November 2026 — consolidated host pass

Inspected host run `20261116T091240Z-a8d9fb5a`: **13 passed groups, 0 failed, 0 blocked**. Backend: 109 passed / 4 skipped / 59 subtests (9.79 s); separate research: 3 passed (16.44 s); stdlib: 77 passed (2.502 s); frontend: 36 passed (1.2 s); desktop/mobile: 2/2 passed (23.148 s), no retries/flaky/skipped cases, no page JavaScript errors/CSP violations/failed transport requests. Eight detail reads per project had maxima 223.067 / 290.453 ms. These measurements do not explain the earlier delay or establish production latency bounds.

Live security 7/7 (9.283 s), both trained-model workers 2/2 (5.578 s) and real Claude 3/3 (6.059 s) passed; ClamAV 1.5.4/signature DB 28184. AWS template lint, build and syntax/configuration passed. Exact logs/reports and live records are copied with SHA-256 provenance to `benchmarks/results/consolidated-pass-20261116`. No security checks were weakened, models retrained, new scheduler-quality benchmark executed or AWS resources provisioned. Earlier failed/blocked runs remain evidence; existing-suite success is not complete research/production acceptance.


## 16 November 2026 — native Chrome file checks and chat defect

Manual frontmost Chrome review created a disposable workspace and verified V1/V2 upload, independent CLEAN scan evidence, source SHA-256, byte-equal native downloads, safe TXT preview, two-version history/disabled old-target control and two completed EDF jobs. Chat question submission blanked the page; no answer/runtime stack was observed. Source inspection identified a likely Promise-returning scroll/effect-cleanup compatibility defect. Changed the effect to a block body returning nothing; added four explicitly mocked assistant-transport browser cases exercising void/Promise scroll returns, repeated messages/reference rendering and route cleanup. Existing browser scenario only navigated to Assistant, explaining the coverage gap despite the earlier 13-group host pass. Local 36 unit tests/build/discovery passed; new browser execution was blocked before navigation by OS Mach-port denial. Host deployment/live retest remain pending. Exact manual record and download digests: `benchmarks/results/native-review-20261116/review.json`. No model/AI/security-policy changes or AWS actions.


## 16 November 2026 — chat correction deployed and live-verified

Host web rebuild and `retest-browser.sh` passed six cases in 27.235 s (two real workspace flows and four explicitly mocked assistant rendering/cleanup cases), no retries/skips/flaky cases. Associated unit report: 36 passed in 1.692 s. Native Chrome then signed into the retained disposable workspace and submitted an actual question about its two verified versions. Real Claude returned an answered explanation with the correct most recent V2 approval and matching event references; UI usage 1,954 input / 265 output tokens, seven authorized references. The answer remained visible without a blank page. These native observations are distinct from the mocked regression cases. No disclosure expansion, console/network capture, full backend rerun or general semantic correctness claim. Evidence: `benchmarks/results/chat-recovery-20261116`.


## 17 November 2026 — user-reference frontend redesign

Implemented the supplied form's black outlines, bold labels, off-white paper and yellow offset accents across the real frontend. Refactored Auth into a reusable API-connected component, added required/error associations and password visibility, and updated responsive navigation/tables/dialogs/research/assistant styling. Current 36 Node frontend tests passed; build, dependency consistency, shell syntax and Compose normalization passed; six browser cases discovered only. Native Chrome reviewed an explicitly isolated actual Auth bundle: desktop layout, required errors, password toggle and registration toggle worked. Mobile iframe/reloads stalled; no backend-connected redesign pass is claimed. Ports 5174/8001 had no listeners; Docker/socket/HTTP/server-bind permissions prevent deployment here. Added `start-ui.sh` for a host web-only rebuild and existing-stack startup without retraining/cloud actions. Record: `benchmarks/results/ui-reference-20261117/verification.json`. Prior November 16 core/Claude passes are not new-design integration evidence.
