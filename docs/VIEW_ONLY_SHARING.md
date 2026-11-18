# View-only sharing

Read-only grants permit the in-app reader. Owners can separately grant Read + download using the Access level selector. This applies to existing grants as well as new grants; migration 0003 adds can_download with a false default, preserving existing grants as read-only. To change a grant, select the same email and the desired access level, then Grant access. Owners retain downloads and file mutations. Granting download access does not grant rename, delete, or resharing permissions.

## Demonstration

1. As the owner, open an approved file → Access → enter a workspace member email → Grant view-only access.
2. As that member in another browser session, refresh Shared with me → open the file → Open file (view only).
3. Text and images display in the reader. PDFs render to a canvas with Previous/Next page controls, with no PDF download or print toolbar. Owner download buttons are absent for members and version download buttons are disabled.
4. A direct download request by a read-only member returns 403. A Read + download member may download only when all verification checks pass.
5. The owner revokes the grant. Future reader and download requests fail. The UI clears a displayed preview when its detail polling detects access loss. This is a usability measure, not erasure of already delivered content.

## Backend boundary

The preview endpoint is `/api/files/{file_id}/versions/{version_id}/preview`. Both paths use the existing release gateway; preview still requires authorized current-version access, clean scanner evidence, valid policy/generation, evidence freshness, and a matching hash after reading the exact stored object version. Preview and download audit outcomes are distinguished. Calling the download release path requires ownership or an active same-tenant can_download grant.

No signed S3 URL is sent to shared readers. The API returns preview bytes with no-store and sandbox response headers. The reader renders text using React escaping, images using image elements, and PDFs using a locally bundled Mozilla PDF.js worker/canvas. PDF content is not put into HTML or executed as document JavaScript. Unsupported preview MIME types are refused.

## Limits

This controls application operations, not redistribution. Rendering requires sending content to the authorized member's browser. A determined recipient can capture network responses, use developer tools, copy text/images, or take screenshots. No download/print UI and a blocked attachment endpoint must not be described as DRM or a guarantee that recipients cannot save content. Content previously obtained before this change cannot be recalled.

## Tests

`tests/test_api.py` covers unauthorized attachment downloads, authorized exact-byte previews, owner downloads, revocation, quarantine, expired evidence, and tampered stored bytes using explicit scanner doubles. `apps/web/e2e/view-only.spec.ts` creates isolated accounts and a harmless generated PDF against the running hybrid app and checks the reader, attachment denial, and revocation on desktop/mobile. Existing local smoke sharing checks now use the preview contract.

Verified on 18 November 2026: 35 API tests passed; 36 frontend unit tests passed; TypeScript/production build passed; both live desktop/mobile view-only PDF tests passed (43.6 seconds total) against the existing AWS hybrid stack. Browser evidence is in apps/web/test-results-view-only. Runtime dependency audit reported zero vulnerabilities; the full audit still reports four development-tool findings through picomatch/Vite. These results do not establish prevention of copying or production security acceptance.

Separate download grants: 36 API tests passed, including upgrade/downgrade, blocked self-escalation, preview preservation, and revocation. Frontend build passed.
