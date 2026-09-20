# Deploy to AWS with Terraform

This guide authenticates a human operator with temporary credentials and makes the S3
backend and AWS provider use the same identity. Do not put access keys, tokens, account
IDs, OAuth URLs, or generated `backend.hcl`/`terraform.tfvars` files in the repository.

## Prerequisites

- AWS CLI 2.32 or newer (`aws login` requires it)
- Terraform 1.6 or newer
- An existing, private S3 bucket for Terraform state
- Either an IAM Identity Center permission set or a dedicated IAM user
- A deployment role with only the permissions needed by this stack

The AWS-managed `SignInLocalDevelopmentAccess` policy only allows an IAM user to obtain
temporary CLI credentials. It does **not** grant access to S3, ECR, EC2, Elastic Load
Balancing, Auto Scaling, IAM, or the Terraform state bucket.

## 1. Inspect credential precedence safely

The repository uses `financial-market-dashboard` as the example profile and `us-east-1`
as the resource region.

```bash
aws --version
terraform version
aws configure list-profiles
aws configure get region --profile financial-market-dashboard
aws configure list --profile financial-market-dashboard
compgen -e | grep -E '^(AWS|TF)_' | sort
```

The last command prints environment variable **names only**, not their values. If
`aws configure list` reports credentials from `env` or `shared-credentials-file`, those
credentials take precedence over the intended login. Never paste the output of
`aws configure export-credentials`; it contains live temporary credentials.

## 2. Choose the correct sign-in flow

### IAM Identity Center (recommended)

Ask the administrator for the Start URL or Issuer URL, the Identity Center region,
the AWS account, and the permission set. The Identity Center region can differ from the
resource region.

```bash
aws configure sso --profile financial-market-dashboard
aws sso login --profile financial-market-dashboard
```

AWS CLI 2.36 uses PKCE by default and the authorization URL must be opened on the same
device. To authorize from another device, use this distinct flow:

```bash
aws sso login \
  --profile financial-market-dashboard \
  --use-device-code
```

Do not use `aws login` for an Identity Center identity.

### IAM user or IAM-federated console identity

An administrator must attach
[`SignInLocalDevelopmentAccess`](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SignInLocalDevelopmentAccess.html)
to the dedicated IAM user, directly or through a group, and separately allow it to assume
the deployment role. Check permissions boundaries and organization SCPs for explicit
denies of AWS Sign-In actions.

```bash
aws logout --profile financial-market-dashboard
aws login \
  --profile financial-market-dashboard \
  --region us-east-1
```

Use a new private browser window with no root-account session. Generate a fresh URL for
every attempt, open it immediately and only once, and keep the originating terminal open.
Do not copy the OAuth URL or code into chat, notes, logs, or URL shorteners.

Use `--remote` only when authorization must happen on a different device:

```bash
aws login --remote \
  --profile financial-market-dashboard \
  --region us-east-1
```

`aws login --remote` and `aws sso login --use-device-code` are not interchangeable.

## 3. Verify the identity

Clear static credential environment variables so the CLI and Terraform cannot silently
select them instead of the profile:

```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
export AWS_PROFILE=financial-market-dashboard
export AWS_REGION=us-east-1

aws sts get-caller-identity --no-cli-pager
```

The ARN must identify the intended user, permission set, or assumed deployment role; it
must not end in `:root`. The output contains an account ID, user ID, and ARN. Mask those
identifiers before sharing screenshots or logs.

If a tool does not yet understand `login_session`, keep the login in a separate profile
and let the tool invoke the CLI internally:

```ini
[profile financial-market-dashboard-login]
region = us-east-1

[profile financial-market-dashboard]
credential_process = aws configure export-credentials --profile financial-market-dashboard-login --format process
region = us-east-1
```

Do not execute that `export-credentials` command manually because it prints credentials.

## 4. Configure and run Terraform

Copy the examples and replace placeholders locally. Both generated files are ignored by
Git.

```bash
cp infra/terraform/backend.hcl.example infra/terraform/backend.hcl
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
```

Set `terraform_state_bucket` in `terraform.tfvars` to the same bucket named in
`backend.hcl`. This allows the GitHub deployment role to access its state after the first
administrator-run bootstrap. The state bucket must already exist and have versioning,
encryption, public-access blocking, and restricted bucket/IAM policies.

```bash
aws sts get-caller-identity --no-cli-pager

terraform -chdir=infra/terraform init \
  -backend-config=backend.hcl
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
```

Review the complete plan before running `terraform apply`. Re-run
`aws sts get-caller-identity` immediately before a long apply, especially when using AWS
CLI 2.36.x temporary login credentials.

The first apply is a bootstrap operation: the GitHub OIDC provider and deployment role do
not exist yet, so an authorized administrator must run it locally. Afterward, configure
the repository's `AWS_DEPLOY_ROLE_ARN` secret and `TF_STATE_BUCKET` secret, and protect the
GitHub `production` environment with required reviewers and restricted deployment
branches. The CI role can inspect but cannot change or delete its own role or inline policy;
an administrator must apply changes to those bootstrap resources. This prevents a
compromised workflow from granting itself additional IAM permissions. For the same reason,
destruction is deliberately not exposed by the GitHub workflow; an authorized
administrator must review and run `terraform destroy` locally.

## HTTP 400 during browser authorization

Work through these checks in order:

1. Confirm whether the identity is IAM Identity Center or IAM and use the matching flow.
2. For IAM login, confirm `SignInLocalDevelopmentAccess` is attached and no explicit deny
   overrides it.
3. Generate a new URL and open it once in a private browser profile without a root session.
4. Try the normal and remote/device flow separately; do not reuse codes between attempts.
5. Disable browser extensions and, if policy permits, retry without a VPN/proxy and on a
   different trusted network.
6. Verify DNS/TLS and clock synchronization. A 403, 404, or redirect from the endpoint is
   enough to show that the connection works:

   ```bash
   date --iso-8601=seconds
   date -u
   timedatectl status
   chronyc tracking
   getent hosts signin.us-east-1.amazonaws.com
   curl -I --connect-timeout 10 https://signin.us-east-1.amazonaws.com/
   ```

   Only one clock service needs to report synchronization. Never pass the full OAuth URL
   to `curl`.

7. Update the AWS CLI and retry. AWS CLI issue
   [#10186](https://github.com/aws/aws-cli/issues/10186) tracks HTTP 400 failures caused by
   stale AWS browser cookies. Issue
   [#10613](https://github.com/aws/aws-cli/issues/10613) tracks a separate AWS CLI 2.36.x
   credential renewal failure after roughly 10–11 minutes.

If escalation is needed, record the UTC time, CLI/OS/browser versions, identity type,
profile, region, flow used, HTTP status, path without query string, correlation ID, clock
state, and whether a private window changed the result. Keep raw debug logs local with
restricted permissions; remove authorization headers, cookies, query strings, codes,
tokens, account IDs, and ARNs before sharing them.

## References

- [AWS CLI sign-in](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html)
- [AWS CLI sign-in troubleshooting](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in-troubleshoot.html)
- [IAM Identity Center and PKCE](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3)
