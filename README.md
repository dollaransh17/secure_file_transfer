# secure_file_transfer

Prooflane is a research prototype for sharing versioned files. An owner can grant a workspace member permission to preview a file or to preview and download it. If the owner replaces the file, the new version goes through verification again.

## How a file is released

1. The API stores the upload in a private, versioned Amazon S3 bucket and records its version and SHA-256 digest in PostgreSQL.
2. A verification worker reads that exact version, scans it with ClamAV and checks its digest. Amazon SQS carries storage notifications so the application can reconcile verification jobs.
3. When a member opens or downloads a file, the gateway checks the requested action, current file version and expiry of the verification evidence. It retrieves the approved version and verifies its digest before returning the bytes.

## Research

The project compares FIFO, earliest-deadline-first, a fixed priority rule, LightGBM and a temporal graph model for scheduling verification work. A separate offline experiment compares three convolutional networks on file-format recognition using generated office documents.

## Run locally

Install Docker with Compose and start the Docker daemon. From the repository root, run:

```sh
./scripts/start-local.sh
```

The launcher creates a private `.env` with fresh local credentials, builds the application, waits for readiness and prints its URL. This local setup uses MinIO for storage. Run `docker compose stop` to stop it. To configure S3 and SQS for a separate AWS deployment, see [the hybrid setup](infrastructure/aws/MINIMAL.md).

## Repository contents

- [React frontend](apps/web/) and [FastAPI backend, workers and migrations](apps/api/)
- [Docker and AWS infrastructure](infrastructure/), [startup and validation scripts](scripts/), and [tests](tests/)
- [Training code](ml/), [scheduler benchmarks](benchmarks/) and [the offline CNN study](research/), including generated fixtures, trained research checkpoints, results and diagrams
- [Optional Vaultspace dashboard](vaultspace/) and [project documentation](PROJECT.md)

For the saved scheduling models, copy the two directories in `research/scheduler-models/` into your private `artifacts/models/` directory, or train fresh ones with the research workflow. The file-format CNN checkpoint is for the offline study. Uploaded files, environment files, cloud credentials, deployment outputs and private run logs stay local.

## Check the source

With Python 3.12 or 3.13, install `pip install -e '.[test]'`, run `python3 scripts/init_local_config.py`, then run `python -m pytest tests`. Install the optional `research` dependencies to include model-training tests.

From `apps/web/`, run `npm ci`, `npm run test:unit` and `npm run build`. The unit tests use Playwright Chromium, which can be installed with `npx playwright install chromium`. The browser end-to-end suite requires a running application.
