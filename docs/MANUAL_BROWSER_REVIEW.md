# Manual browser review — 14 November 2026

## Deployed correction and real Claude follow-up — 16 November 2026

Host web rebuild/retest succeeded: six browser cases passed (27.235 s, no retries/skips/flaky cases), comprising two real workspace flows and four explicitly mocked assistant-transport compatibility cases. All 36 frontend unit tests passed (1.692 s).

Native Chrome was then raised in front of the user. Signed back into the existing disposable workspace; its one approved 72-byte file and original V1/V2 events were intact. Submitted: “Which file versions have verification approved events, and which was verified most recently?” The user message/loading state remained rendered; Claude returned an `answered` explanation with the two actual version IDs and correct most recent V2 approval. Seven authorized event references and **1,954 input / 265 output tokens** appeared. The successful explanation was left visible at localhost:5174/assistant. No mock interception was used in this native check.

The specific blank-page regression is now verified after deployment. The reference disclosure was not expanded, and no console stack/network trace was captured. Prior native file tests established matching V1/V2 bytes/digests; sharing/revocation/concurrency were not manually repeated here. Exact automated reports and bounded native observations: `benchmarks/results/chat-recovery-20261116`. The pending statements in earlier entries below are historical.

## Native Chrome live review — 16 November 2026

Brought Prooflane to the front at localhost:5174, created a disposable workspace, uploaded a 53-byte TXT fixture and observed APPROVED / ClamAV CLEAN. Its displayed SHA-256 matched the locally generated source; the native Chrome download also matched the original bytes. The safe TXT preview matched. Replaced the same logical file with a 72-byte V2 fixture and observed a new storage object version, a different matching digest and independent CLEAN evidence. Its download matched the replacement bytes. The Versions tab showed V1/V2 with the old-target download control disabled. The real queue showed two completed jobs and EDF decisions with deterministic constraints.

Submitting an assistant question produced a **blank page**. No answer was observed, and the runtime console stack was not captured. Source inspection found that the concise chat scroll effect returned `scrollIntoView()`'s result to React; newer scrolling APIs may return a Promise, which cannot serve as effect cleanup. This is a likely compatibility cause, not a captured runtime-stack diagnosis. Changed the effect to a block body with no return. Added four desktop/mobile chat rendering cases covering void/Promise scroll returns, two message responses, visible reference rendering and route cleanup; only assistant transport is explicitly mocked to avoid provider charges. Those fixtures are not proof of backend authorization or real Claude output.

The current source passes 36 frontend unit tests (2.9 s), production build and discovery of six browser cases. Attempting the new Promise case was blocked before navigation by OS denial of Chromium Mach-port registration. The running Docker web image has not been updated: agent socket access remains denied. Host command: export PROOFLANE_WEB_PORT=5174 PROOFLANE_API_PORT=8001, then run `./scripts/retest-browser.sh`. After deployment, repeat an actual live assistant question.

Left a fresh Chrome tab on Files showing approved V2, signed in to the disposable account. Source fixtures and downloaded copies were retained. No unrelated user files were uploaded. Manual review record: `benchmarks/results/native-review-20261116/review.json`. Earlier host all-green results predate this newly exercised interaction; they remain historical evidence, not proof that chat submission passed.

## Automated browser follow-up — 16 November 2026

The host subsequently rebuilt web successfully and ran the expanded real Playwright scenario: **desktop and mobile passed, 24.090 s total, no retries**. Associated frontend unit tests: **36 passed, 1.238 s**. The agent inspected the report and screenshots. Both projects have zero page JavaScript errors and CSP violations; expected denied-authentication requests produced HTTP 401 console messages. The session-revocation step reached the clean Welcome back page without manual reload, closing the previously pending session-recovery regression. Exact-version upload/download, digests, rename, preview, history, deterministic scheduler changes, page navigation and auth flows passed in the same scenario.

Evidence is preserved in `benchmarks/results/browser-session-recovery-20261116`. This host automated run does not change the limits of the earlier native manual review or constitute all platform/security/research tests. The pending descriptions below are historical.

## Follow-up — 16 November 2026

The current frontend unit suite was rerun: **36 passed in 6.5 s**, including session invalidation and guarded rename/logout. Docker Desktop was reachable through its native UI and showed “Engine running,” while all Prooflane containers were initially stopped. The stack Start control was activated, but subsequent native window errors prevented confirmation of running/healthy services. The CLI cannot access the Docker socket from the agent sandbox (`operation not permitted`); this differs from the user's earlier stopped-daemon error.

Read-only listener inspection established that other projects currently occupy both required host ports: 5173 is a Node process in `project_iimb`, and 8000 is a Python process in `Documents/ChatGPT/secure_soft`. Those processes were left untouched. Compose now supports `PROOFLANE_WEB_PORT` and `PROOFLANE_API_PORT`; the allowed origin follows the selected web port, and browser retests use the actual published binding. Alternate-port startup/retest instructions are in the README. No new live browser pass or successful deployment is claimed. The browser access host was unavailable and native Chrome/Docker window access subsequently failed.

## Observed live, through native Safari

The browser-extension access host was unavailable, but the native Safari surface opened a new tab at `http://localhost:5173`. This was an actual live UI observation, separate from the earlier saved Playwright screenshots.

- The login page rendered with readable email/password labels and the expected sign-in/workspace-creation controls.
- Research Lab displayed the genuine available LightGBM/TGN checkpoint identities `7c8dc6549d00719b` / `012b1b6623af2265` and measured MAEs matching the saved manifests. The active workspace had no imported experiment records at that observation.
- Verification Queue displayed the current EDF selection, configured capacity of two and an empty tenant queue. Configured capacity is not a live worker heartbeat count.
- When the active session became invalid, the queue page displayed “Session expired” inside the authenticated layout. Reloading returned to the login page. This established a client recovery issue; no bypass or file release was observed.

The attempted disposable-account sign-in and result import were interrupted by window changes; their success was not observed. Safari subsequently displayed an unrelated application sign-in prompt, which was left untouched. A separate Brave tab was attempted, but native accessibility/window errors prevented a stable continuation. No complete authenticated manual upload/share/download cycle was established in this review. The earlier actual host automated flows remain separate evidence.

## Correction and verification

The frontend now handles HTTP 401 from requests belonging to the current authenticated session by clearing its CSRF state and loading a fresh login document. Public login errors retain their form messages. Delayed failures from an earlier login cannot clear a newer session, concurrent failures trigger one transition, and HTTP 403/429/500 do not masquerade as expiry. Upload unauthorized responses use the same identity guard. Transient refresh failures no longer directly replace the private view with a form.

Ten new Node-only regression cases passed; **36 frontend unit tests** and **77 dependency-free Python tests** passed. TypeScript/Vite build and dependency consistency passed. The backend release/authorization policy is unchanged.

The real browser scenario now revokes only its own fixture session through the existing authenticated logout endpoint, then requires the next protected UI read to return to login without a manual refresh. This tests server-invalidated-session recovery, not elapsed-time expiry or a database/clock mutation. That new browser step and the deployed correction await the next host web build/retest; no successful live verification of this correction is claimed yet.

Run `./scripts/retest-browser.sh` to rebuild only web and execute the expanded desktop/mobile flow with existing API/models. The earlier two-pass browser report and clean audit remain preserved as pre-correction evidence. Browser review was interrupted; it is not a complete manual or production acceptance pass.
