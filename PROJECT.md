# Prooflane

A local-first implementation of version-bound file verification and experimental workload scheduling. **The real local-stack smoke check passed; full research acceptance remains incomplete.** See [verification status](docs/STATUS.md) for executed checks, measured simulations, and remaining work. The application must not be treated as a validated production security product.

The release gateway independently enforces authorization, exact-version evidence, scanner policy, freshness and SHA-256. LightGBM and a TGN-inspired PyTorch/PyG model predict workload quantities for queue ordering. Claude explains permission-filtered event records. Neither model nor Claude can authorize a release.

For the requested minimal AWS footprint, see [S3/SQS hybrid setup](infrastructure/aws/MINIMAL.md): one private versioned bucket with AWS-managed KMS encryption, an S3 event queue and a dead-letter queue, while the frontend, API, database, scanners, models and workers run on the Mac. No domain, RDS, Fargate, NAT or load balancer is needed. Review account credits and usage before spending; there is no guaranteed $1 hard cap.

The user has now reported successful creation of that minimal stack in Mumbai. Once the two non-root AWS login/process profiles and ignored `artifacts/aws-hybrid.env` are configured, run **`./scripts/start-hybrid.sh`** for the AWS-backed host app. It checks caller identities, versioning and queue configuration, then starts isolated local infrastructure and host API/workers/frontend. It does not create AWS resources. The existing `start-local.sh` / `start-ui.sh` workflows still target MinIO. See [runtime access and startup](infrastructure/aws/RUNTIME_ACCESS.md); live AWS application acceptance remains pending.

## Apply the reference-inspired frontend

For an existing local installation, start Docker Desktop and run:

```sh
./scripts/start-ui.sh
```

This rebuilds only web and starts the existing services, defaulting to **http://localhost:5174** and API docs **http://localhost:8001/docs**. It reuses an existing research worker image when available and does not repeat training. Optional `PROOFLANE_WEB_PORT` / `PROOFLANE_API_PORT` exports override those defaults. First-time setup still uses the local startup section below.

The November 17 interface follows the supplied reference: bold black typography, outlined controls, restrained yellow shadows, accessible error states and consistent Lucide icons. Current unit/build checks passed; host deployment and full live redesign regression remain pending. See [verification status](docs/STATUS.md).

## Apply the latest update

```sh
./scripts/update-local.sh
```

This activates the refined UI/Claude configuration and runs the remaining model/cloud checks and genuine training locally. See [update workflow and verification limits](docs/UPDATE_WORKFLOW.md). It does not provision AWS resources. Research Lab can import the actual completed comparison after training.

**Current run:** LightGBM and TGN are genuinely trained; the five-scheduler comparison is saved. To check those existing models without repeating training, run `./scripts/check-models.sh`. See the [measured seed-17 report](benchmarks/results/synthetic-v2-seed-17/README.md); EDF missed fewer deadlines than either learned scheduler, and TGN did not improve queue wait over FIFO in this run.

The November 16 host consolidated suite passed all 13 groups. The subsequent chat correction passed six browser scenarios and a separate native live Claude explanation. The current reference-led frontend has passed 36 unit tests and its build, with isolated form review; its live deployment/retest is pending. See [current status](docs/STATUS.md) for exact historical results, current checks and execution limits.

## Local startup

Requires Docker Engine with Compose, internet access for image/package downloads, at least 6 GB available RAM, and free ports 5173, 8000, 9000 and 9001. PostgreSQL, Redis and ClamAV stay inside the Compose network; they do not reserve host ports 5432, 6379 or 3310.

```sh
python3 scripts/init_local_config.py
./scripts/start-local.sh
docker compose ps
docker compose logs -f worker clamav
```

The startup script pulls infrastructure images, builds `api`, `minio` and `web`, then starts containers with `--no-build`. Only the `api` service builds `prooflane-api:local`; migrations, storage initialization and workers reuse that image. The startup script prints the browser URL only after the frontend proxy and database-backed API health checks pass. If the browser reports `ERR_CONNECTION_REFUSED`, run:

```sh
python3 scripts/doctor.py
docker compose logs --tail 80 migrate api web worker clamav
```

A browser refresh cannot start stopped services. If Docker access or package-network access is denied by the coding workspace, run the startup command from a local terminal that has those permissions.

Open **http://localhost:5173**, register a workspace, and upload a harmless TXT file. The scanner uses the official `clamav/clamav:1.5.4-debian13-slim` image, which publishes native ARM64 and AMD64 variants. ClamAV's initial signature download can take several minutes. Until scanning succeeds, downloads remain held. The API reference is http://localhost:8000/docs. MinIO console is http://localhost:9001 with the development credentials in `.env`.

If other projects occupy ports 5173/8000, use alternate loopback ports without stopping those projects:

```sh
export PROOFLANE_WEB_PORT=5174 PROOFLANE_API_PORT=8001
docker compose -f docker-compose.yml -f docker-compose.ml.yml up --no-build -d --wait --wait-timeout 600
./scripts/retest-browser.sh
```

This preserves the existing ML worker images and model artifacts. Open **http://localhost:5174**; API docs are at **http://localhost:8001/docs**. Compose derives the allowed browser origin from the web port, and the browser retest discovers the actual published port. Keep these exports in the terminal running subsequent Compose commands, or set both values in `.env`. The host `doctor.py` URL probes currently use the default ports.

The Compose stack creates PostgreSQL, Redis, a private versioned MinIO bucket, ClamAV, migrations, FastAPI, two workers and the React frontend. MinIO is built locally from the official `RELEASE.2025-04-22T22-12-26Z` source commit (`0d7408fc9969caf07de6a8c3a84f9fbb10a6739e`), because its historical registry distributions are unavailable in this setup. The first build downloads Go dependencies and compiles the server, so it takes longer. The API image initializes the private versioned bucket through Boto3; there is no `minio/mc` image dependency. This pinned historical version is for the isolated local research setup; select and audit a maintained storage target for production. No AWS or Claude credentials are required for core operation. The commands above are provided for local execution; the stack could not be launched in the authoring sandbox.

Registering creates an isolated tenant. To share within it, open **Sharing → Workspace members**, create a member with an initial password, have that person sign in, and grant read access from a file's **Access** tab. Independent registrations intentionally create separate tenants and cannot share across them. Invitation delivery, password reset and member password rotation are not yet implemented.

## Host development

Use Python 3.12 or 3.13 (not 3.14), Node 22 and a running infrastructure stack. For host development, set `DATABASE_URL` to your project PostgreSQL credentials at `localhost:15432`, `REDIS_URL=redis://localhost:16379/0`, and `CLAMAV_PORT=13310` in `.env` (matching `config/local.example`). The explicit development override publishes those loopback ports. The full Compose stack uses `postgres:5432`, `redis:6379` and `clamav:3310` internally regardless of those host-development settings:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,research]'
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis minio storage-init clamav
alembic upgrade head
uvicorn prooflane.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal with the same virtual environment and working directory:

```sh
python -m prooflane.worker
```

In a third terminal:

```sh
cd apps/web
npm install
npm run dev
```

The API loads `.env`; Vite proxies `/api` to FastAPI. Do not expose development services publicly. Host research inference also needs repository root on `PYTHONPATH` (launch from this directory).

## Tests

**Manual review follow-up:** native Safari opened the live login/research/scheduler pages and exposed stale UI after a session became invalid. Current-session HTTP 401 recovery now passes 36 frontend unit tests and the build. Its expanded real browser invalidation check passed on desktop and mobile on 16 November (2/2, 24.090 s; 36 frontend unit tests also passed). Reports are preserved in `benchmarks/results/browser-session-recovery-20261116`. See `docs/MANUAL_BROWSER_REVIEW.md` for the observed pages, interrupted actions and limits.

**Latest verified web results:** desktop/mobile **2/2 passed** (29.904 s total), **26 frontend unit tests passed**, and the saved npm audit reports **zero vulnerabilities** with Zod 4.6.7/resolvers 7.0.6. Both browser diagnostics have zero page errors/CSP violations and confirm rename/logout responses. Reports: `benchmarks/results/browser-final-20261114`. This is scoped functional validation, not full research or production acceptance.

The subsequent native live review uncovered a chat auto-scroll/effect compatibility failure. Its deployed correction passed **all six desktop/mobile browser cases** (two real workspace flows plus four explicitly mocked chat-rendering regressions). A separate native Chrome check then rendered a real Claude answer with correct version/event references and actual token usage (1,954 input / 265 output). Evidence: `benchmarks/results/chat-recovery-20261116`.

Use `./scripts/retest-browser.sh` to repeat web build/browser validation against the existing API/models, or `./scripts/test-all.sh` for a fresh consolidated run of all existing groups. Historical failures and separate passing reports remain in `docs/RESEARCH_LOG.md`; current evidence and limitations are in `docs/STATUS.md`.

The latest host consolidated suite passed **all 13 groups** on 16 November 2026 (`20261116T091240Z-a8d9fb5a`): 109 backend tests with 4 skips and 59 subtests, 3 research tests, 77 dependency-free Python tests, 36 frontend unit tests, both desktop/mobile browser scenarios, real security/model/Claude smoke checks, frontend build, AWS template lint and syntax/configuration checks. Exact evidence is preserved in `benchmarks/results/consolidated-pass-20261116`. This is a pass of the existing suite, not complete research or production acceptance.

Run all existing suite groups against the already-running local stack with installed web dependencies/Chromium and built API/research/cloud-check images:

```sh
./scripts/test-all.sh
```

This runs source/Compose checks, backend pytest, the three model tests, cloud template lint, real security/model/Claude smoke checks, frontend build and desktop/mobile browser tests. It writes separate logs and `artifacts/test-runs/<run-id>/report.json`, exits nonzero for failures **or blocked checks**, and preserves earlier browser output. It does not retrain models, install dependencies or create AWS resources. The live Claude check requests one explanation and may make one additional billable format-repair request; both responses count toward recorded usage. Use `./scripts/check-browser.sh` to install the existing browser-test dependencies first if needed.

The browser flow checks registration, real upload/approval, SHA-256, exact downloaded bytes, safe TXT preview, rename, replacement/version history, scheduler choices, all eight navigation pages, logout, wrong-password rejection and session persistence. These expanded assertions passed on the host; Chromium remains unavailable in the authoring workspace.

```sh
PYTHONPATH=apps/api:. python3 -m unittest discover -s tests -p '*stdlib.py' -v
python -m pytest -q
cd apps/web
npm run build
npx playwright install chromium
npm run test:e2e
```

The latest consolidated host API-container suite reported **109 passed, 4 skipped and 59 passing subtests**. Three skips require optional ML dependencies; the separate research image passed all three model tests. The fourth requires a Docker CLI inside the core container; outer Compose configuration checks passed. API unit tests use explicit scanner doubles and local storage; the seven-check live smoke below exercised actual ClamAV and versioned storage. Browser tests require a running Compose stack and create their own accounts and files. The desktop/mobile browser flow passed on the host; PostgreSQL concurrency stress and broader browser/accessibility coverage remain pending.

## Live stack smoke check

With the full stack healthy, run the current script inside the existing API image (the bind mount avoids rebuilding just to add this script):

```sh
docker compose run --rm --no-deps -v "$PWD/scripts:/app/scripts:ro" api python scripts/live_smoke.py
```

This creates an isolated test workspace and exercises real PostgreSQL, MinIO, workers and ClamAV through the running HTTP API. It checks clean downloads, evidence binding, sharing/revocation, cross-tenant denial, replacement versions and quarantine using the standard [harmless EICAR antivirus test pattern](https://www.eicar.org/download-anti-malware-testfile/). No pattern is executed. Use `--skip-eicar` to omit that check explicitly. Test audit records are retained; generated credentials are never printed or persisted. Results are written to `artifacts/live/smoke-<run-id>.json`. The recorded live run passed all seven checks in 7.419 seconds; see `benchmarks/results/live-smoke-8740b03aa3184656a5f877059fcf5de0.json`. This does not cover concurrent fault schedules.

## Research workflow

An optional CPU research image installs the model dependencies separately from core services. Its default command runs all three ML smoke tests:

```sh
docker compose --profile research build research
docker compose --profile research run --rm --no-deps research
```

The image follows the [official PyTorch CPU installation route](https://pytorch.org/get-started/previous-versions/) and [minimal PyG installation](https://pytorch-geometric.readthedocs.io/en/latest/install/installation.html). Its build verifies all model packages can be imported. The host successfully built the image and passed all three model tests. The recorded versions were CPU Torch 2.15.0, PyG 2.8.1 and LightGBM 4.7.0.

After those tests pass, generate a fresh context-bearing synthetic dataset and train the independent alternatives inside the research container:

```sh
docker compose --profile research run --rm --no-deps research python -m benchmarks.generate --output artifacts/dataset-context
docker compose --profile research run --rm --no-deps research python -m ml.train artifacts/dataset-context/workload.jsonl --method lightgbm --output artifacts/models/lightgbm
docker compose --profile research run --rm --no-deps research python -m ml.train artifacts/dataset-context/workload.jsonl --method tgn --output artifacts/models/tgn
```

The equivalent host commands below require `.[test,research]` installed in the virtual environment:

```sh
python -m benchmarks.generate --output artifacts/dataset --seed 17
python -m benchmarks.run artifacts/dataset/workload.jsonl --output artifacts/results
python -m ml.train artifacts/dataset/workload.jsonl --method lightgbm --output artifacts/models/lightgbm
python -m ml.train artifacts/dataset/workload.jsonl --method tgn --output artifacts/models/tgn
python -m ml.train artifacts/dataset/workload.jsonl --method tgn --no-memory --output artifacts/models/tgn-no-memory
python -m ml.train artifacts/dataset/workload.jsonl --method tgn --no-graph --output artifacts/models/tgn-no-graph
python scripts/import_results.py --tenant YOUR_TENANT_ID
```

The complete `python -m ml.pipeline --seed 17 --epochs 10` run trained both models on causal v2 data and compared all five schedulers on 720 held-out jobs. Reports and validated checkpoint manifests are preserved in `benchmarks/results/synthetic-v2-seed-17`. No general superiority is established: the models substantially underpredicted held-out demand, and TGN was slightly worse than FIFO on queue wait and misses. The five integrity-monitoring policies, repeated seeds and full ablations remain pending. Use `python scripts/export_training.py --tenant YOUR_TENANT_ID` to export real completed-job durations and temporally bounded authorized demand labels. Read the methodological limitations before interpreting metrics.

Research dependencies are not installed in the default API image. Once the research image is built and compatible models have been genuinely trained into `artifacts/models`, opt the workers into that image:

```sh
./scripts/check-models.sh
```

Select one trained strategy in the Verification Queue UI. Missing or invalid models fall back to deterministic scheduling. Only trusted local checkpoints are supported. Changing workers does not grant ML release authority.

## Claude

Set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` in `.env`, then recreate API. No model ID is hardcoded. The official SDK retrieves the configured model against the account before use; the host successfully checked its configured Haiku model and passed the actual event-grounded generation smoke test. Without configuration, the assistant returns authorized event references and an explicit unconfigured status. It never fabricates a Claude answer. Token usage and API failure types are persisted. Citation validation checks identifiers, not full semantic entailment.

## Documentation

- [Architecture, invariants and release semantics](docs/ARCHITECTURE.md)
- [Threat model and deployment controls](docs/SECURITY.md)
- [ML architecture and experimental methodology](docs/RESEARCH.md)
- [Implementation and verification status](docs/STATUS.md)
- [Research log](docs/RESEARCH_LOG.md)
- [Optional AWS deployment](infrastructure/aws/README.md)

The supplied architecture image and literature review remain unchanged in the repository root. No novelty, superiority or publication-readiness claim is made.
