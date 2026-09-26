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

The Groq request sends a `financial-market-dashboard/1.0` user agent. If a local run
returns HTTP 403 with Cloudflare error 1010, compare it with an authenticated request to
`https://api.groq.com/openai/v1/models` using `curl`. A successful `curl` request isolates
the block to the Python HTTP client; a blocked `curl` request needs investigation with Groq.

> **Language note.** The gate's prompt, log lines, and decision tokens are in Portuguese:
> `APROVADO` means approved and `BLOQUEADO` means blocked. The rest of the project is in
> English.

## Standalone code agent

`scripts/code_agent.py` is a separate, manual one-file repair tool. It is not called by a
GitHub Actions workflow. Run it from the repository root with Python 3.12:

```bash
export GROQ_API_KEY=...  # use a local secret, never commit it
export OBJETIVO="Corrigir o cálculo do indicador"
export ARQUIVO_ALVO="src/indicators.py"
export COMANDO_VERIFICACAO="pytest tests/test_indicators.py"
python scripts/code_agent.py
```

The tool runs the verification command from the repository root. If it already passes,
it makes no change. Otherwise it asks Groq for the complete replacement file, applies
one proposed change at a time, and reruns verification. It edits only `ARQUIVO_ALVO`;
review its output before using the change. It refuses paths outside the repository,
`.github/`, `scripts/`, `.git/`, and secret or credential filenames. It also rejects
new dangerous commands, files over 12,000 bytes, and replacements that remove more
than half the original lines.

Optional settings are `ARQUIVOS_CONTEXTO` (space-separated read-only paths),
`MAX_TENTATIVAS` (default `3`), `GROQ_MODEL` (default `openai/gpt-oss-20b`),
and `API_URL` (default Groq chat completions endpoint). The older `MODELO` and
`GROQCLOUD_API_KEY` names still work when the repository-standard names are unset.
The agent appends `resultado=nada_a_fazer`, `resultado=alterado`, or `resultado=falhou`
to `GITHUB_OUTPUT` when set, and an attempt table to `GITHUB_STEP_SUMMARY` when set.
On success it writes `pr_body.md`; after all attempts fail it restores the original
target, writes `issue_body.md`, and exits successfully so the report can be consumed.
Invalid configuration or a protected target exits with an error.

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
