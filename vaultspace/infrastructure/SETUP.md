# Vaultspace AWS setup — phase 1

Template: `vaultspace-storage.json`. It provisions storage and permissions; it does not deploy the website, change the running app, or create access keys. Cognito, EC2, CloudWatch, and a cloud database are later phases. SQLite remains on your laptop for now.

## 1. Create the stack

1. Sign in to AWS with an identity allowed to create S3, bucket policies, and IAM resources. Application credentials created below cannot deploy this stack.
2. Choose Asia Pacific (Mumbai), `ap-south-1`, if appropriate for your account. Use the same region in subsequent commands.
3. Open CloudFormation → Create stack → With new resources (standard).
4. Select Choose an existing template → Upload a template file. Upload `vaultspace-storage.json`.
5. Stack name: `vaultspace-storage`.
6. Parameter `CreateLocalDemoUser`:
   - `false`: for existing temporary credentials through IAM Identity Center or a development role. Attach the output managed policy to that role/permission set using your account administrator.
   - `true`: for a personal student account that needs a dedicated local-development IAM user. This creates a programmatic identity with only this bucket's app permissions. No console password or key is created.
7. Leave the other stack options at their defaults unless your account requires a service role or permissions boundary. Acknowledge IAM resource creation and Submit.
8. Wait for `CREATE_COMPLETE`. On failure, read the first failed resource in Events; do not repeatedly recreate the stack without checking the reason.
9. Under Outputs, record BucketName, Region, ObjectPrefix, BackendPolicyArn, and (if enabled) LocalDemoUserName. Outputs contain no credentials.

CloudFormation generates the bucket's unique name automatically. No EC2 instance or paid KMS key is provisioned. S3 storage and requests can incur usage charges; do not assume free-tier eligibility.

## 2. Configure local authentication

AWS CLI is already installed on this laptop. Run credential configuration yourself in Terminal, not in a chat message.

### Existing IAM Identity Center access

Ask your administrator to add BackendPolicyArn to a dedicated permission set and assign your account access. Permission sets may require policy attachment/provisioning in each target account. Then:

```sh
aws configure sso --profile vaultspace
aws sso login --profile vaultspace
```

Use the SSO start URL, SSO region, account, and role supplied by your organization. The SSO region may differ from the bucket region.

### Dedicated local demo user

If `CreateLocalDemoUser=true`:

1. Open IAM → Users → the exact LocalDemoUserName from stack Outputs.
2. Security credentials → Access keys → Create access key.
3. Choose Local code, review AWS's credential guidance, and complete the creation.
4. In your own Terminal run:

```sh
aws configure --profile vaultspace
```

Enter the access key ID and secret key at the prompts, region `ap-south-1`, and output format `json`. Do not put keys in this repository, the template, screenshots, or chat. The AWS shared credentials file is stored on your machine and is not encrypted by the CLI. Remove this development key when the demo is finished. On AWS hosting, use an IAM role instead of this user.

## 3. Verify the bucket using the app identity

Replace YOUR_BUCKET_NAME with the BucketName output. These commands operate on a new sample object named `objects/setup-check.txt` only.

```sh
aws sts get-caller-identity --profile vaultspace
printf 'Vaultspace cloud storage test\n' > /tmp/vaultspace-setup-check.txt
aws s3api put-object --bucket YOUR_BUCKET_NAME --key objects/setup-check.txt --body /tmp/vaultspace-setup-check.txt --region ap-south-1 --profile vaultspace
aws s3api head-object --bucket YOUR_BUCKET_NAME --key objects/setup-check.txt --region ap-south-1 --profile vaultspace
aws s3api list-objects-v2 --bucket YOUR_BUCKET_NAME --prefix objects/ --region ap-south-1 --profile vaultspace
```

`head-object` should report `ServerSideEncryption: AES256`. In the S3 console, using your provisioning identity, inspect Permissions: all four Block Public Access settings are on, ACLs are disabled, and the bucket policy denies non-TLS requests. Browser object URLs without authentication should return AccessDenied. The limited app identity is intentionally not allowed to browse all buckets or change bucket configuration.

Remove the test object when done:

```sh
aws s3api delete-object --bucket YOUR_BUCKET_NAME --key objects/setup-check.txt --region ap-south-1 --profile vaultspace
```

## 4. Connect the application next

Provide only BucketName, Region, and whether you configured the `vaultspace` profile. No credentials are needed in chat.

The next code change will add a Boto3 storage adapter using the standard AWS credential chain, profile `vaultspace`, bucket output, and prefix `objects/`. S3 keys will be `objects/<random-file-id>`; the server continues to check file ownership and share expiry before retrieving bytes. Frontend code never receives AWS keys.

Existing local file records refer to local file bytes. Before switching, either migrate those objects to S3 while preserving IDs, or use a separate local metadata directory for the S3 demo and seed it there. Do not simply switch the storage backend against the existing database without migrating files.

The TLS bucket policy protects the backend-to-S3 connection. It does not add HTTPS to the local website. Public hosting will require its own HTTPS configuration and production server.

## Troubleshooting

- `AccessDenied` during stack creation: deployment identity lacks required S3/IAM permissions, or account policies/permissions boundaries restrict resource creation. Use an authorized provisioning identity; the app policy is intentionally insufficient.
- `AccessDenied` during upload: check the selected profile, bucket, region, and `objects/` key prefix. If using SSO, ensure the output policy is attached and the permission set provisioned.
- Root-level `aws s3 ls` denied: expected with this restricted policy. Use the prefix-specific list command above.
- `ExpiredToken`: renew SSO credentials with `aws sso login --profile vaultspace`.
- App uploads still local: expected until the S3 adapter is implemented. Template deployment alone does not change Python code.
- Stack deletion leaves a bucket: intentional. Both bucket and TLS policy are retained. The retained storage remains billable until removed.

## Cleanup after the project

Preserve any needed files first. Remove the demo user's access keys if created. Delete the CloudFormation stack. It removes its managed IAM policy and optional IAM user, but retains the S3 bucket and TLS bucket policy. To stop storage charges, manually empty and delete that retained bucket after confirming the contents can be discarded. A separately uploaded template file in a CloudFormation console staging bucket is not removed by deleting this stack; manage only the template object you uploaded if cleaning that up, not other projects' objects.

## Validation status

The template has been parsed locally as JSON and checked against the documented CloudFormation properties. It has not been deployed or validated against your AWS account. For AWS service validation, run with a provisioning profile:

```sh
aws cloudformation validate-template --template-body file://infrastructure/vaultspace-storage.json --region ap-south-1 --profile YOUR_DEPLOYMENT_PROFILE
```

Validation is read-only and does not provision resources. Successful validation does not prove the account has deployment permissions.

References:
- https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html
- https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-s3-bucket.html
- https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-deletionpolicy.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html
