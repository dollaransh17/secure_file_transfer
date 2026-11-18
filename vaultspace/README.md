# Vaultspace

A local secure file storage and sharing application for a Secure Software Engineering student project. AWS integration is the next phase.

## Run

Requires Python 3.10+; no packages or Node build needed.

```sh
python3 server.py
```

Open http://127.0.0.1:8000. To use another port, run `PORT=8080 python3 server.py`.

Register an account, or set VAULT_DEMO_PASSWORD before first starting the server to create the optional demo accounts:

| Account | Email | Password |
| --- | --- | --- |
| User A · Alex Morgan | alex@vaultspace.demo | Value of VAULT_DEMO_PASSWORD |
| User B · Jamie Chen | jamie@vaultspace.demo | Value of VAULT_DEMO_PASSWORD |

You can also register a new account with a password of at least 12 characters. Demo accounts are intentionally public test identities. Use sample documents only.

## Features

- Overview dashboard, storage usage, and recent activity.
- Account-separated file upload, download, and permanent deletion.
- Search, type filters, multiple upload, and drag/drop.
- Share links with 1 minute, 15 minute, 1 hour, or 24 hour expiry.
- Immediate link revocation and automatic invalidation on file deletion.
- Account-scoped activity log and a security center with an access-test form.
- Responsive layouts and keyboard accessible controls.

## Demonstration

1. Sign in as User A and upload a sample TXT/PDF.
2. Copy its file ID using the copy action. Download it to show owner access.
3. Sign out, then sign in as User B. A's file will not appear.
4. Open Security center, paste A's file ID, and run the access test. The server denies access and records the blocked attempt.
5. Sign back in as A. Create a 1-minute link; copy it while the dialog is open. The full link is displayed only once, and only a hash is retained in the database.
6. Open the link in another tab to download without signing in. After expiry, the link returns HTTP 410. Alternatively revoke it under Shared links to demonstrate immediate invalidation.
7. Try uploading an HTML or EXE file. Use an OS file-picker all-files option or drag/drop to select it. The server rejects it.
8. Show Activity log and Security center to connect each control to evidence.

## Architecture

Browser (HTML/CSS/JavaScript) → Python HTTP API → SQLite metadata and LocalStorage objects.

`storage.py` provides the object-storage boundary: `put`, `get`, and `delete`. Stored keys are randomly generated, never user filenames. Files and the database live under `.data/`, outside the served static directory, and are excluded from Git. Set `VAULT_DATA_DIR` to use a different local directory.

The backend is the authority for sessions, ownership, upload limits, and share validity; browser visibility is not used as an access control.

## Security scope

Implemented: PBKDF2-SHA256 passwords (600,000 rounds and unique salts), hashed session and sharing tokens, HttpOnly/SameSite cookies, 8-hour sessions, CSRF validation, Origin validation, parameterized SQL, escaped dynamic UI text, CSP, download attachments, random storage keys, account ownership checks, extension restrictions, 10 MB file limit, 100 MB per-user quota, and per-email authentication throttling (10 attempts / 5 minutes).

This is a loopback-only educational server, not a production deployment. It currently uses HTTP, so cookies do not carry the Secure flag; deployment requires HTTPS and Secure cookies. File bytes are not malware-scanned or encrypted by this application, extension checks are not content validation, and the SQLite audit trail is not tamper-proof. Local disk permissions and machine access remain part of the trust boundary. Password reset, email verification, MFA, distributed rate limiting, and hardened production hosting remain future work. Share links are bearer credentials: possession grants downloads until expiry/revocation; they are not single-use links.

## AWS integration plan

1. Replace LocalStorage with a private S3 adapter; enable Block Public Access, encryption at rest, and least-privilege IAM.
2. Preserve server ownership checks before issuing short-lived download URLs. For immediate revocation, keep downloads through an authorization proxy; an already issued S3 presigned URL normally remains usable until its expiry.
3. Replace local password authentication with Cognito; verify tokens on the server and map identity to file ownership.
4. Move metadata to an appropriate managed database and audit events to CloudWatch or a dedicated audit store.
5. Deploy behind HTTPS, enable Secure cookies, supply cloud credentials through IAM roles, and add content/malware validation.

No AWS credentials, account, or paid service is needed for the current version.

## Verification

```sh
python3 -m unittest discover -s tests -v
node --check static/app.js
```

The integration suite starts a temporary loopback HTTP server and disposable database. It covers authentication, CSRF, origin checks, logout, registration, private workspace isolation, download/delete/share ownership, allowed and oversized uploads, link expiry/revocation/deletion, audit evidence, and security headers. Node is optional and used only for the JavaScript syntax check.
