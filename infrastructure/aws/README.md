# AWS deployment packages

**For the personal account with a $1 maximum budget, use the [minimal storage/event option](MINIMAL.md).** It prepares one private, versioned S3 bucket using AWS-managed KMS encryption, an SQS event queue and a dead-letter queue; the app and all compute stay local. It needs no domain or customer-managed key. The user has reported successful creation of that minimal stack; live application acceptance remains pending. It does not guarantee a $1 hard spending cap. The full deployment below remains undeployed, optional and unsuitable for that budget without verified credits.

The full CloudFormation package contains a three-repository ECR stack and a 60-resource application stack. It provisions a VPC with two public/private subnet pairs, one NAT gateway, a TLS 1.3 HTTPS ALB, ECS Fargate API/frontend/scanner/two verification workers, private encrypted PostgreSQL RDS, private encrypted/authenticated Redis, versioned private S3 with SSE-KMS, a KMS-encrypted SQS storage-event queue and dead-letter queue, scoped task roles, Cloud Map discovery, CloudWatch logs and a dead-letter alarm.

**Creating these resources incurs AWS charges. No stack, repository, secret, image upload or deployment has been created by the agent.** Region, account, domain/certificate, images and costs must be reviewed before execution. This is a research deployment: one NAT, database and scanner; application rollout may interrupt service. It is not a high-availability production configuration.

## Generate and validate without creating resources

```sh
python3 infrastructure/aws/build_template.py
python3 scripts/aws_review.py --mode full --output artifacts/aws-full-review.json
docker compose --profile cloud-check build cloud-check
docker compose --profile cloud-check run --rm --no-deps cloud-check
```

The generator makes no AWS calls. Structural tests run locally; the `cloud-check` image runs the official CloudFormation schema linter. The image/linter have not been executed in the restricted authoring environment. An authenticated server-side validation is read-only:

```sh
aws cloudformation validate-template --region YOUR_REGION --template-body file://infrastructure/aws/template.json
aws cloudformation validate-template --region YOUR_REGION --template-body file://infrastructure/aws/repositories.json
```

Validation is not deployment. Quotas, regional image/engine availability, certificate ownership, IAM organization restrictions and actual task startup must still be checked in the selected account.

## Deployment sequence (requires approval before resource creation)

1. Confirm AWS account/region and an existing ACM certificate covering the selected domain. Copy `parameters.example.json` to an ignored private parameter file and fill real image URIs/certificate ARN; never put credentials or API keys in it.
2. Create the ECR repository stack from `repositories.json` only after approval. Build and push API, web and optional research images using the returned repository URIs; use immutable image tags and digest-pinned URIs in the application parameters. Architecture must match the built images (ARM64 is suitable for native Apple Silicon builds).
3. If using trained ML in AWS, run `python -m scripts.stage_models` after training and before image builds. It verifies checkpoint hashes and copies only model artifacts into `cloud-models/`; quarantined files, `.env`, runtime secrets and unrelated research data stay excluded. The API image exposes metadata; use the research image as `WorkerImage` to enable real inference dependencies. Without trained weights, deterministic scheduling remains available.
4. Put the Anthropic key into an existing Secrets Manager JSON secret under `ANTHROPIC_API_KEY`, using a secure input path that does not expose it in shell history. Set only its ARN and the desired model ID in parameters. This key transfer has not been performed. It requires authorization for that destination. RDS generates/manages its own password; ECS injects secret values at runtime. No secret is embedded in the template or frontend.
5. Create an application change set with `CAPABILITY_IAM` and the completed parameters. Review every resource/replacement and pricing in the selected region. Execute it only after explicit approval. The API runs migrations before serving; workers/frontend wait on the API service during initial stack creation. Register the domain's DNS ALIAS to `LoadBalancerDns` after deployment.
6. Run the live smoke suite against the deployed test environment after adapting the explicit local-only guard in a reviewed separate test command. Check HTTPS/TLS, current ACL release semantics, S3 VersionId/SSE-KMS, scanner signatures, SQS delivery and event deduplication, RDS/Redis TLS, CloudWatch alarms and actual ML model versions. No cloud acceptance has been performed.

The application receives database/Redis passwords through ECS `Secrets`, constructs escaped URLs in memory, and validates RDS certificates using the AWS global CA bundle. S3 uses the task IAM credential chain and exact version reads. API and worker roles have separate bucket permissions. S3 notifications can only send to the designated queue from the configured bucket/account. Consumer receipts and version/policy/generation-bound jobs make redelivery idempotent; unknown object metadata is retried before dead-lettering. Events never approve content.

## Operational boundaries

The database currently uses the application administrator role to apply migrations and serve requests; split migrator/application/worker SQL privileges before production. Secret rotation requires replacing running tasks so injected credentials refresh. A CloudWatch alarm is created but no notification recipient is configured. ClamAV signature state is ephemeral in this initial cloud task definition and must be persisted or mirrored for a scaled deployment. ECR scanning does not replace a complete dependency/security review. Add autoscaling, multi-AZ state, appropriate backup/restore drills, retention, tenant quotas and audit tamper evidence before production.

Deleting a stack does not erase the retained S3 bucket, KMS key or ECR images; RDS is deletion-protected and snapshots on replacement/deletion. Those retained resources can continue incurring charges. Review deletion and retention deliberately; never remove security evidence or storage just to make a deployment command succeed.
