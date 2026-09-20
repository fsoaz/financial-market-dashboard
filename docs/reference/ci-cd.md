# CI and quality gate reference

What each GitHub Actions workflow does, and the secrets and variables it needs.

| Workflow | File | Trigger |
|----------|------|---------|
| CI | `.github/workflows/ci.yml` | Push and pull request on `main`, manual |
| Build and publish image | `.github/workflows/docker-publish.yml` | A successful CI run on `main` |
| Update market data | `.github/workflows/data-update.yml` | Cron `15 22 * * 1-5` (UTC), manual |
| Terraform infrastructure | `.github/workflows/terraform.yml` | Pull requests touching `infra/terraform/**`, manual |

## CI

Three jobs run on Python 3.12:

1. **Lint** — `ruff check .` and `ruff format --check .`.
2. **Tests** — `pytest` with coverage, uploading `coverage.json` and `test-results.xml`
   as the `quality-gate-inputs` artifact.
3. **AI quality gate** — needs both jobs above; runs `scripts/quality_gate.py`.

The quality gate job is skipped for pull requests from forks, because those runs cannot
read repository secrets.

## Quality gate

`scripts/quality_gate.py` applies a deterministic check first and an AI review second.

```bash
# Reproduce locally
pytest --cov=src --cov-report=json --junitxml=test-results.xml
python scripts/quality_gate.py --coverage-file coverage.json --junit-file test-results.xml
```

| Step | Behavior |
|------|----------|
| Coverage | Reads `totals.percent_covered` from `coverage.json`. Below the minimum → blocked, no AI call. |
| API key | With coverage passing but `GROQ_API_KEY` unset → blocked. |
| AI review | Sends coverage, test count, event name, and branch to Groq's OpenAI-compatible endpoint. No source code and no secrets are sent. |

The script exits `0` only when the decision is `APROVADO`; anything else exits `1` and
fails the job. It also writes a short summary to `$GITHUB_STEP_SUMMARY`.

> **Language note.** The gate's prompt, log lines, and decision tokens are in Portuguese:
> `APROVADO` means approved and `BLOQUEADO` means blocked. The rest of the project is in
> English.

### Configuration

| Name | Kind | Default | Effect |
|------|------|---------|--------|
| `QUALITY_GATE_MIN_COVERAGE` | Repository variable | `70` | Minimum percent coverage of `src/`. Must parse as a number between 0 and 100. |
| `GROQ_MODEL` | Repository variable | `openai/gpt-oss-20b` | Model used for the AI review. |
| `GROQ_API_KEY` | Repository secret | *(none)* | Required. Without it the gate blocks. |

## Build and publish image

Runs only when CI succeeds on `main`, checks out the exact commit CI tested, and pushes
two tags to ECR: the commit SHA and `latest`.

EC2 instances pull the image in user data, at boot only. Pushing a new `latest` does not
redeploy the running fleet — start an instance refresh on the Auto Scaling group to roll
it out. See [Deploy to AWS](../how-to/deploy-to-aws.md#update-the-running-dashboard).

## Update market data

Runs `python main.py` with `DATA_BACKEND=local`, asserts that CSVs were produced, then
syncs them into the private data bucket with `--delete`:

```text
s3://$DATA_BUCKET/market-data/raw
s3://$DATA_BUCKET/market-data/processed
```

> **The `market-data` prefix is a contract.** The workflow reads it from the `S3_PREFIX`
> repository variable, defaulting to `market-data`. It must match the `s3_prefix`
> Terraform variable, which is what the running container receives as `S3_PREFIX`. If the
> two disagree, CI writes to one prefix while the dashboard reads another, and the only
> symptom is an empty dashboard. Change both together.

## Terraform infrastructure

Pull requests touching `infra/terraform/**` run `fmt -check`, `validate`, and `plan`.
`apply` runs only on a manual dispatch, in the protected `production` environment. Remote
state configuration is generated at runtime from `TF_STATE_BUCKET`; nothing is committed.

Destroy is deliberately not exposed — an administrator runs it locally.

## Secrets and variables

| Name | Kind | Used by |
|------|------|---------|
| `AWS_DEPLOY_ROLE_ARN` | Secret | Image publish, data update, Terraform |
| `TF_STATE_BUCKET` | Secret | Terraform |
| `DATA_BUCKET` | Secret | Data update |
| `GROQ_API_KEY` | Secret | CI quality gate |
| `GROQ_MODEL` | Variable | CI quality gate |
| `QUALITY_GATE_MIN_COVERAGE` | Variable | CI quality gate |
| `S3_PREFIX` | Variable | Data update |

The AWS jobs authenticate through GitHub OIDC — there are no long-lived AWS keys. The
trust policy restricts the role to this repository and the `production` environment.

## Related

- [Configuration](configuration.md) — application environment variables
- [Deploy to AWS](../how-to/deploy-to-aws.md) — provisioning the stack the workflows target
- [Contributing](../../CONTRIBUTING.md) — the checks to run before opening a PR
