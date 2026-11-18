# Vaultspace dashboard connected to Prooflane

The backend project is `~/secure_file_transfer`. This integration makes no changes to that project, its AWS identities, infrastructure, file records, or configuration.

## Run

First ensure Docker Desktop is responsive. In a terminal run the existing hybrid launcher:

```sh
cd ~/secure_file_transfer
./scripts/start-hybrid.sh
```

If that launcher is already running, use its existing terminal to stop it with Ctrl+C before restarting. Do not launch a second copy or kill unrelated port owners. Renew the project's existing restricted AWS sessions if the launcher's checks request it; this dashboard requires no new AWS resources or credentials. Read the backend's infrastructure/aws/RUNTIME_ACCESS.md for its profile setup.

In another terminal:

```sh
cd ~/secure_file_transfer/vaultspace
python3 prooflane_dashboard.py
```

Or double-click `start-prooflane.command`. Open **http://localhost:8080**. Keep the terminal open. The original `server.py` remains the independent local demo; it does not connect to Prooflane.

## Accounts and actions

Use an existing Prooflane email/password, or register a new workspace. Vaultspace's old demo accounts do not automatically exist in Prooflane. Registration creates a separate tenant. To demonstrate same-workspace sharing, an account with the researcher role can open a file's share action and add a member with an initial password, then grant that member access. Follow the backend's existing limitations for member credentials/password rotation. Never put passwords in project files or chat.

Uploads are multipart POSTs to `/api/files` and enter Prooflane verification. The dashboard polls every 10 seconds to display current scan states. Downloads use the exact current application version at `/api/files/{file_id}/versions/{version_id}/download`; the backend remains responsible for all permission, freshness, scanner and integrity checks. The dashboard does not bypass pending or quarantined states.

Sharing grants access to named workspace members, not anonymous expiring links. Owners can revoke grants. Deletion uses the backend's soft-delete endpoint; it does not purge S3 versions. File metadata, events, accounts and grants all come from Prooflane. No local demo database or object store is read by the connected server.

## Proxy boundary

`prooflane_dashboard.py` serves the existing layout with `static/prooflane.js` and forwards `/api/` to loopback port 8001. It rejects unexpected Host and cross-origin requests. After validating the browser's origin, it translates Origin to the existing backend's configured public origin (`http://localhost:5174`). Cookies and CSRF tokens pass through; backend authentication and authorization remain authoritative. The proxy has no credentials or database access. Only the existing API/workers access AWS.

Defaults can be overridden with `PROOFLANE_API_URL` (loopback HTTP only), `PROOFLANE_PUBLIC_ORIGIN` (must match backend PUBLIC_ORIGIN), and `VAULT_DASHBOARD_PORT` (default 8080). This is a loopback development integration, not a production reverse proxy. Do not expose either development server publicly.

## Verification and current blocker

Passed: Python compilation, JavaScript syntax, and 3 HTTP integration tests covering static asset selection/file exposure, cookie/CSRF/body forwarding, and rejection of invalid origins/hosts. The existing API OpenAPI document and dashboard root respond, but database-backed `/api/health` and `/api/auth/me` timed out during integration. Docker status also hung. Login, AWS upload, scanning, sharing and download have therefore not been verified end-to-end in this session. The backend infrastructure needs recovery before those flows can complete. No user files were uploaded and no AWS permissions were changed.

After restarting infrastructure, verify:

```sh
curl --max-time 15 http://127.0.0.1:8001/api/health
```

Then sign in at localhost:8080, upload a harmless TXT, wait for its actual approval, download and compare bytes, and check member access/revocation. An upload timeout has an unknown outcome: refresh the file list before deciding whether to retry.

Run proxy tests with:

```sh
python3 -m unittest discover -s tests -p test_prooflane_proxy.py -v
node --check static/prooflane.js
```
