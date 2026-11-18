# Verification status

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

## Both IAM logins configured; guarded host launcher — 18 November 2026

The user supplied the expected worker STS ARN, and the local worker login binding matches. Both `prooflane-api` and `prooflane-worker` process profiles are now configured with their corresponding non-root login profiles. Added `scripts/start-hybrid.sh` / `start_hybrid.py` to check both AWS identities, bucket versioning and source queue encryption/redrive before starting any local services. It rejects root, wrong-account and API-as-worker identities, removes inherited static credential variables from backend child environments, and keeps backend secrets out of the frontend process. These checks verify identity and required service settings; they do not audit all effective IAM grants.

The launcher creates no AWS resources. It starts local PostgreSQL/Redis/ClamAV in the isolated `prooflane-hybrid` Docker project, runs migrations, and supervises native API/two workers/Vite with separate profile environments. It refuses occupied API/web ports, prints readiness only after database-backed API and frontend proxy health, and stops only its own native process groups on exit. Infrastructure/data remain retained. The prepared private configuration is complete and mode 0600; `.env` and Claude/model settings are preserved.

**20 focused startup/storage/configuration tests passed, with 19 subtests (2.03 s); 103 dependency-free checks passed (2.380 s).** Negative cases cover mixed/root identities, missing profiles, inherited credentials, versioning suspension, missing queue encryption/redrive, unsafe/incomplete local targets and sanitized provider failures. Shell syntax, Python compilation and launcher help passed. Cloud transports in those tests are explicit doubles.

The agent's live `--check` attempt stopped on `CredentialRetrievalError` before starting Docker/API/workers/frontend. Internal CLI credential-export diagnostics also failed here; no credential values were displayed or saved. The tool environment has not successfully verified AWS file/queue access. Run `./scripts/start-hybrid.sh` in the host Terminal with Docker Desktop active; actual S3/KMS/SQS/ClamAV/application acceptance is still pending. Evidence: `artifacts/aws-deployment-20261118/verification.json`.

## Worker browser verified; native dependencies available — 18 November 2026

After a user password-entry handoff, native Safari visibly showed `prooflane-worker` in the AWS account menu. The CUA segment is complete. The CLI `prooflane-worker-login` profile still locally points to `user/prooflane-api`, so a fresh authorization in that verified Safari session is needed; the separate `prooflane-worker` process profile is absent. API's process-credential bridge is configured. No AWS file or queue operation is claimed from a browser sign-in.

Native Python dependencies are now installed. Executed `tests/test_s3_storage.py` and `tests/test_cloud_config.py`: **11 passed in 6.84 s**, covering exact-version adapter behavior, missing versioning/version IDs, SDK credential routing, encryption headers and production configuration rejection. Transport is explicitly doubled; this is not live AWS integration. Filled the private hybrid database URL using the existing Compose password configuration without printing it or changing `.env`. Local database connection, service startup, worker queue consumption and AWS file release acceptance remain pending. This supersedes the earlier dependency-install block below.

## API runtime login corrected — 18 November 2026

The user completed CLI login as `user/prooflane-api`; the agent independently read that same non-secret `login_session` binding from the local profile. The earlier root binding is corrected. The separate process-credential profile `prooflane-api` and worker login profile remain absent, and no AWS-backed application test has run.

Host `.venv` uses Python 3.12.13 but lacked pip and backend dependencies. `ensurepip --upgrade` successfully installed pip 26.0 inside the workspace. Installing `.[test]` failed because the build subprocess could not resolve/reach the package host for setuptools. The host terminal must complete installation; no native FastAPI/SQLAlchemy/Boto3/pytest availability or server startup is claimed. Existing `.env`, Claude configuration and model artifacts were preserved. Evidence: `artifacts/aws-deployment-20261118/verification.json`.

## Minimal AWS stack reported created — 18 November 2026

The user supplied a successful `stack-create-complete` wait followed by all ten expected DescribeStacks outputs in `ap-south-1`, including the versioned bucket, source/DLQ URLs and two managed policy ARNs. **Infrastructure creation is host-reported complete.** This is separate from the earlier validation/change-set results; the agent has not independently accessed the account. The raw output values are recorded in ignored `artifacts/aws-deployment-20261118/verification.json`.

Prepared ignored `artifacts/aws-hybrid.env` with the exact reported bucket, queue and region at mode 0600. The local database password remains a placeholder; API/worker profiles are not yet configured. Preserved the existing `.env` and Claude key. Added a restricted temporary-login runbook and the official process-credential bridge because Boto3 direct console-login support requires CRT. Root credentials must not be used by runtime processes. IAM identity setup, local hybrid startup, actual SSE-KMS uploads, worker/S3/SQS/DLQ operation and release tests remain pending. No new test pass or measured AWS workload/cost is claimed.

## AWS template validation reported successful — 18 November 2026

The user supplied successful host output from `aws cloudformation validate-template` for the current minimal JSON template in `ap-south-1`. AWS returned the expected `ProjectName` parameter, S3/SQS hybrid description and `CAPABILITY_IAM` requirement for the two managed policies. This advances template validation beyond the earlier offline-only checks; it does not prove resource creation, deployed permissions or live delivery. The agent's separate STS attempt could not reach the AWS endpoint, so this is explicitly host-reported evidence rather than an independently executed agent AWS check.

The CLI login reports a root principal. Root credentials must not be used by the application/worker runtime; restricted runtime identities remain part of setup. Change-set review, deployment and S3/SQS acceptance are still pending. No resource creation, IAM attachment or cloud workload result was reported in the supplied output.

## SQS added to minimal CloudFormation — 18 November 2026

The minimal option now declares **seven resources**: S3 bucket/policy, SQS standard source queue, DLQ, source queue policy and two unattached IAM managed policies. This supersedes the earlier storage-only artifact. S3 ObjectCreated notifications target the encrypted queue; worker permissions permit source-queue consumption while the API receives no SQS grants. Queue encryption uses SSE-SQS; file encryption remains SSE-KMS with AWS-managed `aws/s3`. No new customer-managed key or cloud compute was added.

Bucket/queue names derive from the account and full unique stack ID suffix, allowing exact source ARN restrictions and pre-creation notification permission without a resource dependency cycle. Configured 20-second polling, 180-second visibility, five-receive redrive, four-day source retention and fourteen-day DLQ retention. Source-account/bucket restrictions, queue TLS, restricted DLQ redrive, lengths and dependency graph are tested. The existing worker event thread consumes `STORAGE_EVENT_QUEUE_URL`, deduplicates receipts and reconciles into PostgreSQL's durable verification queue; events do not approve content. Updated hybrid configuration/runbook and review now include queue costs, retained queues and idle polling.

**94 dependency-free tests passed (1.649 s)**, including eleven minimal-template cases and existing exact-version notification/parser checks. Python compilation, generation and offline resource review passed. Schema lint, authenticated AWS validation and real S3→SQS delivery/consumer/DLQ acceptance remain pending; the last cfn-lint install attempt in this environment could not resolve the package. No AWS API calls, deployment, IAM attachments, model retraining or paid resource creation occurred. Seven additional S3 adapter pytest cases remain unexecuted here as previously recorded.

## Minimal CloudFormation template — 18 November 2026

Regenerated `infrastructure/aws/minimal-storage.json` with described configuration outputs, bucket ARN and Bucket Key setting. The only parameter tags the project; generated bucket naming avoids a fixed-name collision. Added operator notes for IAM acknowledgement, deliberate policy attachment, optional read-only AWS validation and the extra template-storage bucket the CloudFormation console may create. No compute, SQS, customer-managed KMS key or domain was added.

Eight focused structural tests passed (0.002 s), including reference resolution and private/versioned/KMS/TLS/access boundaries. The `cfn-lint` installation attempt found no matching distribution in this environment, so schema lint was not executed. No AWS validation, account access, resource creation or IAM attachment occurred. The prior November 17 records remain historical evidence for their source revision.

## Minimal AWS footprint — 17 November 2026

Prepared a separate four-resource `minimal-storage.json`: one private versioned S3 bucket, a TLS/SSE-KMS deny policy and two unattached IAM access policies. Uses the AWS-managed `aws/s3` key and Bucket Keys; no cloud compute, database, NAT, load balancer, queue, customer-managed key or domain. The full 60-resource template remains an explicit alternative. `aws_review.py` defaults to minimal mode and performs no AWS actions.

Host hybrid configuration keeps the API, PostgreSQL, Redis, scanners, workers and ML on the Mac. Actual AWS storage now uses the SDK credential chain even in development; MinIO credentials are only supplied for an explicit development endpoint. Added configurable Bucket Key headers. Exact-version storage/release semantics and production guards remain in place. The Vite proxy can target the host API at 8001. See the [minimal runbook](../infrastructure/aws/MINIMAL.md), including isolated local state, credential boundaries, costs and retained-version cleanup.

Current checks: **90 dependency-free Python tests passed (1.464 s)**, including 13 new minimal-cloud/credential/encryption checks; Python compilation, deterministic generation/local review and frontend TypeScript/Vite build passed. Seven additional adapter contract cases were added to pytest but not executed here: host API/pytest dependencies are absent and the OS sandbox denies Docker socket access. The updated three-template `cfn-lint` command also needs a host run after rebuilding `cloud-check`. No AWS API calls, IAM attachments, cloud deployment, spending, AWS-backed smoke test or model retraining occurred. AWS-managed key request charges and S3 usage remain applicable; no $1 hard-cap guarantee is made. Current source hashes and results: `artifacts/aws-minimal-20261117/verification.json`.

## Reference-led UI refinement — 17 November 2026

Applied the supplied form reference to the real frontend: off-white surfaces, bold black headings, outlined controls, yellow offset accents and clear red errors. Extracted the real API-connected sign-in/registration component, added an accessible password visibility toggle, required-state/error associations and a desktop/mobile layout. Updated navigation, file tables, status labels, dialogs, graph surfaces, research tables and assistant styling. Mobile file tables retain name/status/version/actions while secondary size/date details remain available in the inspector; the sidebar can scroll on short screens. No new dependencies or fabricated metrics were introduced.

**Current 36 frontend unit tests passed (2.436 s)**; TypeScript/Vite builds and dependency consistency passed. Shell syntax and Compose configuration passed; six existing browser cases were discovered. Native Chrome rendered an isolated bundle of the actual Auth component, and required-field validation, password visibility and registration toggle were observed working. This preview was explicitly labeled as having no backend. Its mobile iframe preview/later reloads stalled; no full responsive visual pass is claimed. The authenticated redesigned pages need post-start visual/functional checks.

The November 16 core/full-suite and real Claude results below remain valid historical evidence. Today ports 5174/8001 had no listeners; the agent cannot access Docker or bind a local Vite server under its OS sandbox. The new design is **not yet deployed/live-verified**. Run `./scripts/start-ui.sh` from the host terminal to build only web and start existing services with readiness checks (default frontend 5174, API 8001). It reuses an existing research worker image when available and does not train models or provision AWS. Then run `./scripts/retest-browser.sh` with matching port exports for a fresh live regression run.

Evidence: `benchmarks/results/ui-reference-20261117/verification.json`; isolated component review artifacts are under `artifacts/ui-reference-20261117`.

## Deployed chat correction verified — 16 November 2026

The host rebuilt web and reported the container healthy. Its expanded browser suite passed **6/6 in 27.235 s**, with no skips, failures, retries or flaky cases: two real desktop/mobile workspace scenarios and four explicitly mocked assistant-transport regressions covering void/Promise-returning scrolling, repeated message rendering, references and client-side route cleanup. Associated frontend unit report: **36 passed in 1.692 s**. Both workspace diagnostic records have zero page errors, CSP violations and failed requests.

The agent then brought native Chrome to the front, signed back into the retained disposable workspace and submitted a real question about its verification history. **Claude answered successfully without the blank page**, correctly identifying both verified versions and the most recent V2 approval. The UI displayed seven authorized event references and actual usage **1,954 input / 265 output tokens**. The successful answer was left visible in Chrome. This is separate from the four mocked-transport browser cases. The reference disclosure was not expanded and no native console/network trace was captured; one response does not establish general RAG correctness.

Evidence: `benchmarks/results/chat-recovery-20261116` (report retained in the local run archive), including exact host browser/unit reports and a bounded native observation record. Deployment and the specific live chat retest are now complete. The earlier pending notes below are historical. The prior all-green 13-group run remains evidence for its revision; it was not rerun wholesale after this frontend-only correction. Full research/production acceptance remains incomplete.

## Earlier native chat failure — 16 November 2026

Native Chrome testing now confirms actual registration, V1/V2 upload, separate CLEAN scan evidence, SHA-256, matching downloaded bytes, TXT preview, version history and two completed jobs/EDF decisions. **Submitting an assistant question blanked the page.** The earlier 13-group pass did not submit a chat question in the UI; its separate Claude API smoke does not cover this rendering failure.

A likely scroll-Promise/effect-cleanup compatibility defect was corrected in source using a block-bodied effect. Four explicitly mocked-transport browser regression cases were added; actual Claude authorization remains covered separately. Current 36 frontend unit tests and production build passed; browser discovery finds six cases. The new browser case was blocked before navigation by the agent OS sandbox, and the source fix is not deployed to Docker. Host web rebuild/retest and another real live chat submission are pending. See [MANUAL_BROWSER_REVIEW.md](MANUAL_BROWSER_REVIEW.md) and `benchmarks/results/native-review-20261116/review.json`. No complete current-source acceptance is claimed.

## Consolidated pass — 16 November 2026

**All 13 existing test groups passed in host run `20261116T091240Z-a8d9fb5a`: 0 failed, 0 blocked.** The agent inspected the saved logs/report, browser diagnostics and representative screenshots. This closes the test-origin and file-detail readiness regressions from the earlier failed consolidated run. Full research and production acceptance remain incomplete.

Exact reports, logs, live smoke records and session-recovery screenshots are preserved under `benchmarks/results/consolidated-pass-20261116` (report retained in the local run archive). SHA-256 provenance is recorded in `verification.json`. The original report is `artifacts/test-runs/20261116T091240Z-a8d9fb5a/report.json`.

| Check | Actual result in this consolidated run |
|---|---|
| Backend pytest | **109 passed, 4 skipped, 59 subtests**, 9.79 s |
| Research pytest | **3 passed**, 16.44 s; genuine model training/inference tests |
| Dependency-free Python | **77 passed**, 2.502 s |
| Frontend unit tests | **36 passed**, 1.2 s |
| Production frontend build | Dependency consistency, TypeScript and Vite passed |
| Real browser scenarios | **Desktop/mobile 2/2 passed**, 23.148 s; no retries, skips or flaky cases |
| Browser diagnostics | Zero page JavaScript errors, CSP violations or failed transport requests in both projects |
| Live security | **7/7 passed**, 9.283 s; real PostgreSQL/MinIO/workers/ClamAV |
| Live trained-model workers | **2/2 passed**, 5.578 s; LightGBM and TGN checkpoint-backed predictions, exact clean downloads and EICAR denial |
| Live Claude | **3/3 passed**, 6.059 s; authorized citations/actual usage, cross-tenant exclusion and revocation |
| AWS template lint | Passed; no AWS deployment or authenticated account validation |
| Syntax / Compose configuration | Python, shell and Compose checks passed |

Three backend skips are optional model tests unavailable in the core image; all three ran successfully in the separate research image. The fourth requires a Docker CLI inside the core container; outer Compose validation passed. A passing group summary does not mean no individual tests were skipped.

## Verified behavior and limits

API test configuration now pins its isolated origin before app construction; negative/positive cases cover both 5173 and 5174. Production CSRF/authorization policy was retained. The browser scenario waits for the real detail GET, requires HTTP 200 and expected filename/digest, then checks rendering. Maximum observed detail-read durations in this run were **223.067 ms desktop / 290.453 ms mobile** across eight reads per project. This does not establish the cause of the earlier delay or a production latency bound.

Desktop/mobile passed registration, real upload/approval, SHA-256, exact V1/V2 downloaded bytes, safe TXT preview, server-confirmed rename, replacement/history, disabled old-target control, FIFO/EDF/rule changes, page navigation, logout/session denial, wrong-password rejection, valid login/persistence and recovery after server revocation without manual reload. Expected authentication-denial requests generated HTTP 401 console messages. Automated navigation to Assistant does not replace the separate real Claude smoke; navigation to Research Lab does not import a research experiment.

Live security used ClamAV **1.5.4 / signature DB 28184**. It checked unshared denial, sharing/revocation, tenant isolation, immutable replacement/current-target enforcement, exact bytes/evidence and harmless EICAR quarantine. This is functional coverage, not concurrent fault injection. The deterministic gateway remained independent of learned predictions and Claude.

The current dependency policy pins Zod **4.6.7** and resolvers **7.0.6**, with manifest/lock/installed consistency checks and `npm ci` in the image. The preserved earlier host audit reported zero vulnerabilities; no new registry audit was run in this consolidated suite. Nonfatal Rollup dependency-comment warnings and the Starlette test-client deprecation remain recorded in the logs.

Previous failures and blocked agent attempts remain in [RESEARCH_LOG.md](RESEARCH_LOG.md) and their original reports. Earlier native manual review remains limited as documented in [MANUAL_BROWSER_REVIEW.md](MANUAL_BROWSER_REVIEW.md); the host automated pass is not a new native manual pass. No model retraining, paid infrastructure or AWS resources were created by this suite.

## Actual trained models and experiment

Saved reports/manifests: [synthetic-v2-seed-17](../benchmarks/results/synthetic-v2-seed-17/README.md). Dataset SHA-256: `865049578a32926789c96334124c38339c61f0c609eba8007318d5829e3a3039`. Seed 17, purged train/validation/test sizes 1,800/240/720, two simulated workers. TGN completed ten epochs, retaining epoch 5 by validation score.

| Model/checkpoint | Duration MAE | Duration RMSE | Demand MAE | Demand bias |
|---|---:|---:|---:|---:|
| LightGBM `7c8dc6549d00719b` | 5.054 s | 6.049 s | 125.219 | −125.219 |
| TGN `012b1b6623af2265` | 4.297 s | 5.287 s | 118.812 | −118.747 |

| Scheduler | Mean queue wait | P95 queue wait | Deadline misses |
|---|---:|---:|---:|
| FIFO | 685.001 s | 1524.600 s | 630 |
| EDF | 681.307 s | 1524.555 s | 595 |
| Rule | 681.268 s | 1524.570 s | 611 |
| LightGBM | 676.681 s | 1524.477 s | 627 |
| TGN | 685.039 s | 1524.603 s | 633 |

LightGBM had lowest mean wait; EDF fewest misses. TGN was slightly worse than FIFO on both, despite lower prediction MAE. Both learned models substantially underpredicted demand. Comparison inference cost was 0.114 ms/job for batched LightGBM and 154.965 ms/job for TGN, measured separately and excluded from simulated wait. These are one-seed synthetic queue/service/request measurements, not actual user download latency, uncertainty estimates or real-world generalization. No policy-invalid release count was measured by this simulation. Historical v1 data exposed labels prematurely and must not be used for learned-model evaluation.

## Remaining work

1. Broaden browser/accessibility and failure-path coverage, and maintain fresh dependency audits/locked builds. The current rename/logout/CSP/browser checks and recorded Zod migration/audit have passed.
2. Stress concurrent PostgreSQL revocation/release, version changes, policy advancement, expired leases and stale completions. Current tests/live smoke do not prove these races safe.
3. Run repeated seeds, workload-family holdouts and memory/attention ablations; account for inference overhead in end-to-end scheduling. Improve demand modeling using training/validation evidence before a fresh final held-out assessment.
4. Complete real event-schedule fault injection and all five integrity-monitoring baselines; measure resource/storage cost, legitimate-download delay and policy-invalid releases under faults. The current oracle evaluates final-state predicates.
5. Broaden RAG entailment/adversarial evaluation, accessibility/browser coverage, dependency locking/audits, account recovery/invitations, retention and operations.
6. AWS deployment still requires region/domain/ACM certificate, digest-pinned images, account/permission validation and explicit cost approval. No AWS resources or secrets were created; template lint is not deployment validation.

Use `./scripts/test-all.sh` for a fresh consolidated run, `./scripts/retest-browser.sh` for web build/browser checks, and `npm --prefix apps/web run test:unit` for the 36 Node-only frontend tests. Full execution history and prior failures are retained in [RESEARCH_LOG.md](RESEARCH_LOG.md).
