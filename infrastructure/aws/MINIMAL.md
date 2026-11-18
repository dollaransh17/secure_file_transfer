# Minimal AWS option: local application, S3 storage and SQS events

This is the preferred option for the requested **$1 maximum budget**. The user reported successful creation of the minimal infrastructure stack in Mumbai on 18 November 2026; application integration acceptance remains pending. It makes the existing local research application use actual AWS storage; it does not host the website publicly or validate the full AWS architecture. No domain is required. Commands in this guide are operator instructions, not agent-executed AWS provisioning.

| Location | Components |
|---|---|
| AWS | One private, versioned S3 bucket; SSE-KMS using the AWS-managed `aws/s3` key; S3 Bucket Keys; an SQS storage-event queue and dead-letter queue |
| Mac | React, FastAPI, PostgreSQL, Redis, ClamAV, verification workers, LightGBM/TGN and experiment files |
| Existing external integration | Claude, only when configured; its API charges are separate from AWS |

The template also defines bucket/queue policies and two **unattached** IAM managed policies. It creates no IAM user/access key, customer-managed KMS key, EC2/ECS instance, RDS, ElastiCache, NAT gateway, load balancer, ECR repository, Secrets Manager secret or CloudWatch log group. The original full cloud template remains a separate, more expensive alternative.

The deployable CloudFormation file is [`minimal-storage.json`](minimal-storage.json). JSON is supported directly by CloudFormation. Its only parameter is `ProjectName` (default `prooflane-lab`), used as a tag; bucket/source queue names are computed from the account and full unique stack ID suffix. This allows the S3 notification permission to exist before bucket creation without a circular dependency. Stack outputs provide the bucket name/ARN, region, both policy ARNs, encryption alias, Bucket Key setting, source queue URL/ARN and DLQ URL. The stack needs the `CAPABILITY_IAM` acknowledgement because it creates managed policies; these policies remain unattached until deliberately assigned to existing identities.

## Security behavior

S3 public access is blocked, ACLs are disabled, versioning is enabled, and the bucket policy denies non-TLS requests and uploads without explicit SSE-KMS. The application requests `alias/aws/s3` encryption and Bucket Keys on upload. The API policy permits versioned reads and writes; the worker policy permits versioned reads plus receive/delete/visibility/attribute operations on the source SQS queue. Both scope KMS use to S3 in the same account/region and this bucket's encryption context. Neither policy grants S3 delete, queue purge, queue administration or DLQ recovery privileges. Existing identity policies must also be reviewed; attaching a restricted policy does not remove broader permissions already present.

For `KMS_KEY_ID=alias/aws/s3`, the client sends explicit `aws:kms` encryption without a key-ID header, letting S3 select/create the AWS-managed key on first use. Customer-managed key identifiers remain explicit. This follows the [documented S3 upload behavior](https://docs.aws.amazon.com/AmazonS3/latest/userguide/specifying-kms-encryption.html).

Downloads still pass through the deterministic local release gateway and exact `VersionId` reads. Browsers receive no AWS credentials or direct bucket access. AWS-backed development now uses Boto3's normal credential chain, even if old MinIO values remain in `.env`; explicit local MinIO endpoints still use local credentials. Prefer temporary profile credentials and separate API/worker identities. These policies do not provide cross-account KMS sharing; application sharing continues through the server within the same storage account.

Application uploads create durable verification jobs in local PostgreSQL. S3 `ObjectCreated:*` notifications also flow to a standard SQS queue, consumed by the existing local worker event thread when `STORAGE_EVENT_QUEUE_URL` is configured. Notifications only reconcile exact-version metadata and schedule required work; they cannot approve files or override the release gateway. Receipts and job keys deduplicate equivalent work; unknown/uncommitted versions are retried rather than treated as approved. SQS is for storage-event transport; it does not replace PostgreSQL's verification-job queue or the selectable verification scheduling strategies.

The source queue policy grants `SendMessage` only to S3 for this exact bucket/account and denies non-TLS requests. Both queues use SQS-managed encryption (SSE-SQS), so no extra KMS key or queue KMS grant is required. Long polling is 20 seconds, visibility 180 seconds, source retention four days, redrive after five receives, and DLQ retention fourteen days. The DLQ accepts redrive only from this source queue. Failed notifications need manual investigation; no CloudWatch alarm or recovery automation is claimed. Arbitrary external objects with no committed application version metadata eventually dead-letter. Direct S3 deletions and policy changes are not subscribed event types. External AWS delivery/redelivery/fault behavior has not been live-validated. Production HTTPS, secure-cookie and storage guards are unchanged. The host example is development-only and binds services to loopback.

## Costs and the $1 limit

AWS-managed keys have no monthly key-storage charge; KMS requests can still be charged. Bucket Keys reduce KMS request traffic. S3 charges can include storage of **all retained versions**, requests and applicable data transfer. SQS requests, including empty long-poll receives and DLQ operations, can also be charged. Stop local event consumers when not testing to avoid continued idle polling requests. Actual free-plan eligibility/credits must be checked in this personal account before any deployment. No service configuration here guarantees a $1 hard cap; AWS budget notifications can be delayed. If the limit is absolute and the account does not provide a verified no-charge free plan, keep using local MinIO.

Sources: [KMS pricing](https://aws.amazon.com/kms/pricing/), [S3 pricing](https://aws.amazon.com/s3/pricing/), [SQS pricing](https://aws.amazon.com/sqs/pricing/), [S3 Bucket Keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-key.html), [S3 destination permissions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/grant-destinations-permissions-to-s3.html), [AWS Free Tier plans](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html), [budget notification limitations](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html).

## Safe preparation: no AWS calls

From the repository root:

```sh
python3 infrastructure/aws/build_minimal_template.py
python3 scripts/aws_review.py --mode minimal --output artifacts/aws-minimal-review.json
PYTHONPATH=apps/api:. python3 -m unittest discover -s tests -p '*stdlib.py' -q
docker compose --profile cloud-check build cloud-check
docker compose --profile cloud-check run --rm --no-deps cloud-check
```

Rebuild `cloud-check` before running it so its command includes the new minimal template. The review records resources and constraints; it is not an account-specific price quote or deployment authorization. The template has seven CloudFormation resources: one bucket, one bucket policy, two queues, one queue policy and two managed policies.

`aws_review.py` now defaults to minimal mode; reviewing the full hosting stack requires `--mode full`. Adapter/configuration tests can be run with installed host API test dependencies using `python -m pytest -q tests/test_s3_storage.py tests/test_cloud_config.py`. Their transport doubles do not establish AWS integration success.

Before resource creation, review the selected account, region, verified credits/free-plan terms, intended uploads/downloads/versions, seven-resource template and restricted IAM attachment destination. Create only `minimal-storage.json` after approval. Do not deploy `template.json` or `repositories.json` for this option. No deployment command is run by the preparation workflow.

Once the correct personal account/profile and region are confirmed, this optional AWS command validates the template without creating the application resources (replace the two placeholders):

```sh
aws cloudformation validate-template \
  --profile YOUR_PERSONAL_PROFILE \
  --region YOUR_REGION \
  --template-body file://infrastructure/aws/minimal-storage.json
```

Validation is not deployment or AWS acceptance. Prefer CLI submission with the inline template body when eventually deploying: the CloudFormation console's "Upload a template file" option may create an additional S3 bucket to store templates. This extra template-storage bucket is outside the seven application resources. See [CloudFormation console behavior](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html).

## Create the reviewed stack from your terminal

These are operator instructions, not commands executed by the agent. Use this sequence for a **new** `prooflane-hybrid` stack only. If that stack already exists, review an UPDATE change set instead; do not delete existing resources to retry. Confirm that the reported $26 credit balance is active, unexpired and applicable to S3/KMS/SQS, and that the estimated experiment fits the account budget.

1. Select an existing **personal-account deployment profile**, and set the chosen region. The example uses Mumbai; change it consistently if using another region. AWS CLI is already installed on this Mac. The deployment identity needs CloudFormation and permission to create the bucket, queues and managed policies. Do not use root credentials or put keys in this repository.

   ```sh
   cd ~/secure_file_transfer
   aws configure list-profiles
   export AWS_PROFILE=YOUR_PERSONAL_DEPLOYMENT_PROFILE
   export AWS_REGION=ap-south-1
   aws sts get-caller-identity
   ```

   Compare the returned Account with your personal AWS console account before proceeding. A named profile alone does not prove which account its credentials belong to. If identity lookup fails, fix that profile/session first.

2. Validate the minimal artifact and prepare a change set. The change set records the proposal but does not create the seven application resources until execution:

   ```sh
   aws cloudformation validate-template --region "$AWS_REGION" \
     --template-body file://infrastructure/aws/minimal-storage.json
   aws cloudformation create-change-set --region "$AWS_REGION" \
     --stack-name prooflane-hybrid --change-set-name initial-review \
     --change-set-type CREATE --capabilities CAPABILITY_IAM \
     --template-body file://infrastructure/aws/minimal-storage.json
   aws cloudformation wait change-set-create-complete --region "$AWS_REGION" \
     --stack-name prooflane-hybrid --change-set-name initial-review
   aws cloudformation describe-change-set --region "$AWS_REGION" \
     --stack-name prooflane-hybrid --change-set-name initial-review \
     --query 'Changes[].ResourceChange.{Action:Action,Resource:LogicalResourceId,Type:ResourceType}' \
     --output table
   ```

   Review exactly seven additions: `Files`, `FilesPolicy`, `StorageEvents`, `EventDeadLetter`, `StorageQueuePolicy`, `ApiStoragePolicy`, `WorkerStoragePolicy`. There should be no server, database, load balancer or customer-managed KMS key. Account-specific validation may still fail due to permissions, quotas or service restrictions. Stop on an error and inspect it; do not skip the failed check.

3. **This step creates AWS resources.** Run it only after accepting the reviewed account, resource list and costs:

   ```sh
   aws cloudformation execute-change-set --region "$AWS_REGION" \
     --stack-name prooflane-hybrid --change-set-name initial-review
   aws cloudformation wait stack-create-complete --region "$AWS_REGION" \
     --stack-name prooflane-hybrid
   aws cloudformation describe-stacks --region "$AWS_REGION" \
     --stack-name prooflane-hybrid --query 'Stacks[0].Outputs' --output table
   ```

   Keep `Bucket`, `Region`, `StorageEventQueueUrl`, `ApiStoragePolicyArn` and `WorkerStoragePolicyArn`. The AWS-managed `aws/s3` key is selected/created when SSE-KMS is first used; do not create a customer-managed key manually. If creation fails, inspect `aws cloudformation describe-stack-events --region "$AWS_REGION" --stack-name prooflane-hybrid`; no success is implied by an earlier change-set result.

4. Attach the output API policy to the existing identity used by the **API runtime profile**, and the output worker policy to the existing identity used by the **worker runtime profile**. Use IAM's policy attachment controls for the selected role/user, or the corresponding administrator-managed permission set. Prefer temporary credentials. Runtime profiles should not inherit deployment/administrator privileges; adding a narrow policy does not subtract broad existing grants. If you do not yet have restricted runtime identities, configure those before starting the application. Never share access keys in chat or put them in frontend configuration.

5. Prepare the private host configuration, then follow the local startup section below:

   ```sh
   mkdir -p artifacts
   cp -n infrastructure/aws/hybrid.example artifacts/aws-hybrid.env
   chmod 600 artifacts/aws-hybrid.env
   ```

   Set `S3_BUCKET` from `Bucket`, `AWS_REGION` from `Region`, `STORAGE_EVENT_QUEUE_URL` from `StorageEventQueueUrl`, and `AWS_PROFILE` to the API runtime profile. Keep `S3_ENDPOINT=` empty, `KMS_KEY_ID=alias/aws/s3`, and `S3_BUCKET_KEY_ENABLED=true`. Set the isolated local PostgreSQL password/URL as described below. In worker terminals, override `AWS_PROFILE` with the worker runtime profile **after** exporting this configuration. Keep the existing Claude key in `.env`; no key transfer to AWS is needed.

References: [AWS change-set review](https://docs.aws.amazon.com/cli/latest/reference/cloudformation/create-change-set.html), [executing a change set](https://docs.aws.amazon.com/cli/latest/reference/cloudformation/execute-change-set.html), [identity lookup](https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html).

## After an approved bucket exists: run the application locally

First configure [restricted runtime logins](RUNTIME_ACCESS.md). This includes the IAM sign-in permission and a CLI process-credential bridge for the existing Python SDK, so the backend does not use the root profile or need long-term access keys.

Once both runtime profiles and the private configuration are ready, `./scripts/start-hybrid.sh` automates the isolated local startup below. Use `./scripts/start-hybrid.sh --check` for read-only identity/storage/queue checks first. It does not deploy AWS resources. Run it from a host terminal with AWS network access and Docker Desktop running. The agent's restricted execution environment cannot establish the live AWS/Docker connections needed to verify startup here.

The following is an operator runbook, **not an executed deployment**. Use a separate local database/Compose project so existing MinIO version records are not interpreted as S3 records. Do not migrate existing object metadata without migrating and verifying the exact corresponding bytes/versions. If the existing Prooflane API/web/workers occupy ports 8001/5174, stop those specific old services before binding the host processes; leave unrelated projects and the old data volumes intact.

1. Start an isolated local infrastructure project. Ensure loopback ports 15432, 16379 and 13310 are free; ClamAV may need time to download signatures. A separate Compose project creates separate database/signature volumes:

   ```sh
   docker compose -p prooflane-hybrid -f docker-compose.yml -f docker-compose.dev.yml up -d --wait --wait-timeout 600 postgres redis clamav
   ```

2. Use a Python 3.12/3.13 environment with `pip install -e '.[test]'` (add `research` only for host ML inference). Keep the existing `.env` private; do not overwrite the configured Claude key. Copy `infrastructure/aws/hybrid.example` to ignored `artifacts/aws-hybrid.env`. Fill the stack's bucket/region and `StorageEventQueueUrl`, an existing temporary AWS profile and the URL-escaped local PostgreSQL password matching `POSTGRES_PASSWORD`. This file contains local development overrides, no AWS access keys. The `prooflane-hybrid` project uses a fresh volume, even though its database name is also `prooflane`.

3. In each backend terminal, activate that environment, start at the repository root, and export the private overrides before running commands:

   ```sh
   set -a
   . artifacts/aws-hybrid.env
   set +a
   alembic upgrade head
   uvicorn prooflane.main:app --host 127.0.0.1 --port 8001
   ```

   In a separate terminal with the same exported configuration, run `python -m prooflane.worker`; repeat for a second worker. For least privilege use the API profile in the API terminal and the worker storage/event-consumer profile in worker terminals. Each configured worker starts a long-polling event thread; equivalent notifications/jobs are coalesced. Resolve unavailable credentials as an error; never fall back to local storage.

4. In a frontend terminal, only the proxy setting is needed:

   ```sh
   PROOFLANE_DEV_API_URL=http://127.0.0.1:8001 npm --prefix apps/web run dev -- --host 127.0.0.1 --port 5174 --strictPort
   ```

   Open `http://localhost:5174`. Register a disposable workspace, upload a small harmless TXT, wait for actual ClamAV approval, inspect SHA-256/exact storage version, download and compare bytes. Confirm a matching `STORAGE_EVENT_RECONCILED` record, receipt deduplication and eventual source queue drain; inspect DLQ depth separately. Then test sharing, revocation, replacement and quarantine. AWS-backed acceptance has not yet been executed.

**Do not start the main Compose API/worker/storage-init services for this host workflow:** their internal configuration deliberately targets MinIO. `start-local.sh`, `start-ui.sh` and the existing live smoke scripts remain local-MinIO workflows; they are not AWS acceptance tools. Do not expose development ports publicly. Proper HTTPS and secure cookies are required for deployment.

## Cleanup

Stopping local processes stops their SQS polling, but does not remove cloud data or stop S3 storage charges. The bucket and both queues are retained on stack deletion. Uploaded versions remain billable; retained queue messages expire according to their configured retention periods. After the experiment, review/delete all object versions and delete markers deliberately, investigate/export required queue evidence, then remove the empty bucket, retained queues and stack/policies. Application runtime identities cannot perform this administrative cleanup. Do not enable automatic deletion that could destroy research evidence. No cleanup or deletion has been executed.
