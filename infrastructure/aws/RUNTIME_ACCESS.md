# Local runtime access after stack creation

The infrastructure stack is separate from runtime authentication. Do not run Prooflane with the `default` root profile. For this local research setup, two restricted IAM console users can obtain temporary CLI credentials using `aws login`; no long-term access keys are needed. Production should use workload IAM roles instead.

## Create the two restricted identities

In the personal account's **IAM → Users → Create user**, create:

| User | Customer-managed policy from stack outputs | Additional AWS-managed policy |
|---|---|---|
| `prooflane-api` | `ApiStoragePolicyArn` | `SignInLocalDevelopmentAccess` |
| `prooflane-worker` | `WorkerStoragePolicyArn` | `SignInLocalDevelopmentAccess` |

Alternatively, a standalone API identity policy can combine the deployed API storage permissions with `signin:AuthorizeOAuth2Access` / `signin:CreateOAuth2Token` for the account/region's local CLI client. A generated account-specific copy is under ignored `artifacts/aws-deployment-20261118/prooflane-api-policy.json` where prepared. If using that combined policy for `prooflane-api`, it replaces the two-policy API attachment above; it does not need another sign-in policy. It has not been created or attached in AWS by the agent.

Enable AWS Management Console access for these IAM users so you can complete the browser-based CLI login. Set passwords privately in AWS; do not put passwords in this repository or chat. Follow console password-change instructions when required, and configure MFA. Do not create access keys or attach AdministratorAccess, AmazonS3FullAccess or AmazonSQSFullAccess. Existing identities with these names need a permission review before reuse; do not add permissions to an unrelated user just because its name matches.

AWS's new account experience may not permit IAM users with console access. If the console-access option is unavailable, stop at this step and report that limitation so a supported federated/workload-role access path can be selected for the account. Do not upgrade the plan, create long-term keys or fall back to the root profile just to bypass it. See [AWS IAM user creation guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html).

The sign-in policy permits the OAuth login flow; it does not grant S3, SQS or IAM administration. AWS documents this prerequisite in [CLI console authentication](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html) and [SignInLocalDevelopmentAccess](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SignInLocalDevelopmentAccess.html).

## Log in using the matching IAM console session

Run one login at a time. When the browser opens, select the IAM user named for that login, not the existing root session. If the user is not listed, sign into the console as that IAM user first. The credentials remain on your Mac.

```sh
aws login --profile prooflane-api-login --region ap-south-1
aws sts get-caller-identity --profile prooflane-api-login --region ap-south-1

aws login --profile prooflane-worker-login --region ap-south-1
aws sts get-caller-identity --profile prooflane-worker-login --region ap-south-1
```

Expected caller ARNs end in `:user/prooflane-api` and `:user/prooflane-worker`, respectively, in your personal account. Stop and correct the selected browser identity if either output ends in `:root` or names a different principal/account. Keep root's `default` profile separate.

### If the browser keeps selecting root

The profile name does not constrain the identity chosen in the browser. Check the actual local binding without making an AWS request:

```sh
aws configure get login_session --profile prooflane-api-login
```

If it ends in `:root`, the browser selected root; an STS cache is not the cause. A remote login flow lets you open the authorization URL in a separate private browser window. The combined API policy generated above grants only the `/localhost` client, so `/remote` must also be authorized before using this flow. Where prepared, this account/region-specific file contains only the two sign-in actions for the remote client:

```sh
aws iam put-user-policy --profile default \
  --user-name prooflane-api --policy-name ProoflaneRemoteCliLogin \
  --policy-document file://artifacts/aws-deployment-20261118/api-remote-login-policy.json
```

This is an operator-run IAM change under the administrator profile, not an agent-executed command. It grants no storage or IAM administration permissions. If it returns `NoSuchEntity`, the IAM user has not been created under that name; creating the policy alone did not create a user. Correct the IAM user setup first. If the user already has `SignInLocalDevelopmentAccess`, its remote sign-in grant is already included and this extra inline policy is unnecessary.

```sh
aws login --profile prooflane-api-login --region ap-south-1 --remote
```

Copy the printed authorization URL into a **private/incognito window**. Sign in as an IAM user with the personal account ID, username `prooflane-api` and that user's password. Do not use the root email/password. Paste any returned authorization code only into the waiting CLI, never into chat or a report. Confirm an overwrite only when the proposed new ARN ends in `:user/prooflane-api`, then repeat the identity check. This does not require signing out other accounts or changing the existing `default` profile. See the [AWS remote-login client permissions](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html).

## Let Python use those temporary sessions

Boto3's direct login provider requires CRT. The documented CLI process-credential bridge avoids adding that native dependency to this project's existing Python environment. These commands store **command configuration**, not keys, in the AWS profile config:

```sh
aws configure set region ap-south-1 --profile prooflane-api-login
aws configure set credential_process 'aws configure export-credentials --profile prooflane-api-login --region ap-south-1 --format process' --profile prooflane-api
aws configure set region ap-south-1 --profile prooflane-api

aws configure set region ap-south-1 --profile prooflane-worker-login
aws configure set credential_process 'aws configure export-credentials --profile prooflane-worker-login --region ap-south-1 --format process' --profile prooflane-worker
aws configure set region ap-south-1 --profile prooflane-worker

aws sts get-caller-identity --profile prooflane-api --region ap-south-1
aws sts get-caller-identity --profile prooflane-worker --region ap-south-1
```

Do not run or paste the `export-credentials` command by itself: its JSON contains temporary credentials. The SDK captures it internally when using the process profile. Each process profile must resolve to its matching restricted IAM user. The bridge is documented under [Sharing Login credentials as process credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html); [Boto3 login provider requirements](https://docs.aws.amazon.com/sdkref/latest/guide/feature-login-credentials.html) describe the CRT dependency for direct login.

The login profiles need their own saved region. Passing `--region` to an outer STS command or setting the Boto3 client's region does not supply it to the credential-export subprocess. If existing bridges fail with `CredentialRetrievalError`, run the two `aws configure set region ... --profile ...-login` commands above first. These only change local CLI configuration, without changing IAM permissions or creating resources.

When sessions expire, repeat `aws login` for the matching `*-login` profile. The process profile automatically obtains refreshed credentials from that session while it remains valid. An expired login must be corrected; no root or local-storage fallback is configured.

## Use the private hybrid configuration

`artifacts/aws-hybrid.env` is ignored by version control. Where populated from the host-reported outputs, it already contains the deployed bucket, region and event queue URL. It still needs the isolated local database password. Leave the existing Claude key in `.env`.

In the current prepared installation the database URL has also been filled from the existing Compose password setting. Keep it private. After configuring both process profiles, use the foreground host launcher:

```sh
./scripts/start-hybrid.sh --check
./scripts/start-hybrid.sh
```

`--check` performs read-only AWS identity, bucket-versioning and SQS encryption/redrive checks. Startup rejects root, API-as-worker and wrong-account identities. The full command then starts only local PostgreSQL/Redis/ClamAV in the isolated `prooflane-hybrid` Compose project, migrates that database, and launches host API/two workers/frontend with separate profile environments. It creates no AWS resources or IAM permissions. It refuses occupied API/frontend ports without stopping their owners. Logs are private under `.runtime/hybrid`; Ctrl+C stops the host processes, leaving local infrastructure and retained AWS data intact. API/worker credentials and the Claude key are not passed to the frontend process.

The host launcher builds the frontend and serves that output with loopback-only Vite preview and the same `/api` proxy. It does not run Vite's development module transforms during acceptance tests. This is a local research preview, not a production public web server. After changing launcher/API code, stop the foreground launcher with Ctrl+C and restart it; existing PostgreSQL data and AWS objects remain.

The default browser URL is `http://localhost:5174`. Register a new Prooflane workspace because this isolated database does not contain the old MinIO application's users or object records. Native ML scheduling requires the optional research dependencies; missing models/dependencies retain deterministic fallback. After startup, a separate host terminal can run the existing real security smoke against this loopback API:

```sh
ENVIRONMENT=development PUBLIC_ORIGIN=http://localhost:5174 .venv/bin/python scripts/live_smoke.py --base-url http://127.0.0.1:8001 --output-dir artifacts/live-aws
```

Uploads have a separate bounded 90-second response budget (`--upload-timeout`, at most 180); regular requests retain 30 seconds. A timed-out upload has an unconfirmed outcome and is never automatically retried. Antivirus phases distinguish upload, quarantine polling, exact-version evidence and download denial; a generic transport timeout does not establish a scanner verdict.

Then run browser checks serially on this memory-limited host, keeping this stack running:

```sh
E2E_URL=http://localhost:5174 npm --prefix apps/web run test:e2e -- --workers=1
```

Do not run `retest-browser.sh` for this hybrid stack; it rebuilds the separate legacy Docker web service. The browser suite still includes two real workspace scenarios and four explicitly mocked assistant-rendering cases, not four live Claude calls.

This writes small real objects and runs ClamAV (including the standard harmless EICAR test), sharing/revocation and exact-version checks; it can incur S3/KMS/SQS request charges and retains test records/versions. The script's current report kind says "local-stack smoke"; that alone does not attest the storage provider. The launcher preflight/profile/configuration and subsequent AWS/SQS evidence must also be recorded. The smoke does not separately establish SQS delivery/DLQ correctness. No AWS-backed smoke success is claimed until that command actually runs successfully.

The manual terminal workflow below remains available if you prefer to run processes separately.

In the API terminal, activate the project Python environment and export the overrides:

```sh
set -a
. artifacts/aws-hybrid.env
set +a
export AWS_PROFILE=prooflane-api
```

In each worker terminal, use the same steps with the worker profile **after** sourcing the file:

```sh
set -a
. artifacts/aws-hybrid.env
set +a
export AWS_PROFILE=prooflane-worker
```

Then follow [the isolated local service startup](MINIMAL.md#after-an-approved-bucket-exists-run-the-application-locally). Do not start the old Compose API/worker/storage-init services, which target MinIO. Keep the frontend and backend on loopback. Verify real upload, ClamAV approval, digest/exact-version download and `STORAGE_EVENT_RECONCILED` before claiming AWS integration works.

These IAM identities are not owned by the infrastructure stack if created manually. Include them in the experiment's later reviewed cleanup. Deleting the stack does not remove them or the retained bucket/queues.

## Find an uploaded file in S3

Open an owned file in **All files → file inspector → Storage**. This shows the Prooflane filename beside its current version’s exact object key, S3 URI, bucket, region and object-version ID. **View this version in AWS S3** opens the console with that key/version selected; it requires separate AWS console permissions and grants no object access. The Storage tab is available to the owner. Existing files work without reuploading because their keys are already recorded. Restart the host launcher after applying this API/UI change.

## Mock CNN demonstration

The prepared private hybrid configuration explicitly sets `CNN_MODE=mock`. Restart the launcher to activate it. Open an owned file → **CNN analysis**. New successful verification completions record synthetic demo scores automatically; use **Generate analysis** on existing versions. `CNN_MODE=disabled` disables generation and hides the tab. No trained CNN, Torch dependency, external request or additional AWS service is used. The output is deterministic demo data derived from the recorded fingerprint, not malware probabilities. It is bound to the exact version/digest/generation, recorded as `MOCK_CNN_ANALYSIS`, and excluded from Claude retrieval. Mock output cannot change scan evidence, status, permissions or release rules. CLEAN plus matching integrity retains normal approval; INFECTED remains quarantined; pending/error states remain held. This is separate from the existing optional real CNN inference endpoint.

The CNN analysis UI calls the two synthetic values **Demo output A/B**, not security classes. It shows a generating state for an unrecorded result and replaces the action with a recorded-result explanation afterward; regenerating an unchanged fingerprint would yield unchanged scores. The separate untrained PyTorch ByteCNN prototype uses the first 65,536 bytes as a padded 256×256 single-channel array, two 3×3 convolution layers (16 then 32 channels), pooling and a linear classifier. This prototype is not invoked by mock mode.

The latest CNN panel replaces the two placeholder outputs with one **Demo score** percentage, a Simulated badge, a short preview summary, and the actual recorded verification status. The percentage remains explicitly illustrative, not a security rating or a measured threat probability; backend evidence and release behavior are unchanged.
