# Threat model and operational requirements

## Assumptions

Adversaries include malicious uploaders, unauthorized authenticated users, cross-tenant identifier probing, replayed or delayed results, duplicated work, accidental object replacement and crashed workers. Trust the API, scanner runtime, PostgreSQL authorization/evidence state, protected baseline and configured object store identity. A malicious database administrator, compromised backend/worker or malicious storage provider is outside this implementation's guarantee. SHA-256 plus S3 encryption is not a proof of retrievability or an authenticated-storage protocol against a malicious provider.

No actual malware corpus is downloaded or executed. ClamAV scans bytes without executing them. CNN input must be locally supplied, permitted data; ELF/PE execution is never required. Scanner container isolation and archive limits still need deployment hardening and testing.

## Implemented controls

Argon2id passwords, opaque hashed server sessions, expirations/rotation, HttpOnly/Strict cookies, CSRF headers and Origin checks, exact CORS origins, tenant filters, role checks, file ACLs, server-side authorization on every download, private storage, quarantine-first uploads, format/size bounds, exact S3 VersionId reads, policy/generation fencing, bounded retries, SHA-256, immutable version records, no-store/nosniff/frame protections, sanitized assistant evidence, and audit records.

Redis rate limiting is shared across instances. The development limiter is best-effort when Redis is down; production fails closed. Behind a reverse proxy, configure trusted proxy identities and per-user/IP limits before exposing the service; the initial middleware uses the direct peer address. This may group users behind the bundled proxy. Production settings reject insecure cookies, HTTP origins, non-PostgreSQL state and local storage. Production S3 requires KMS configuration and role-based credentials.

## Deployment requirements

Terminate TLS 1.3 at a maintained load balancer/reverse proxy; do not use replay-sensitive 0-RTT for upload, sharing or authentication. Local HTTP is bound to loopback and only appropriate for isolated development. Disable public database, object-store, Redis and scanner ports. Separate API, worker and research identities. Never trust uploaded logs as assistant instructions. Never give ML/LLM components authorization-writing privileges in a hardened deployment.

Use an externally managed secret store. Rotate development secrets. Enforce private S3 policies and block public access. Restrict KMS to the necessary bucket encryption contexts. Back up PostgreSQL and enable private encrypted database storage. Apply object retention/lifecycle policies and monitor failed scans/dead jobs. Do not log request bodies, cookies or Anthropic keys.

The current app has no password reset, MFA, email verification, invite delivery, password rotation UI, advanced audit tamper evidence, persistent security log retention policy, distributed logout-all operation, quota enforcement, deletion garbage collector or automated cloud deployment. These are material production limitations.

## Validation still required

Run live ClamAV clean/EICAR/error/oversized archive tests, actual S3/MinIO version pinning tests, PostgreSQL concurrent revocation/release tests, stale worker fencing stress, tenant-isolation fuzzing, dependency scanning and an external security review. Existing scanner-double tests are useful negative cases but cannot establish those live-service properties.

Dependency audit commands after installing and locking dependencies:

```sh
python -m pip install pip-audit
pip-audit
cd apps/web
npm audit
```

No dependency audit was executed in the restricted authoring environment. Dependency lock files must be generated and reviewed once package resolution is available.
