# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
aligned with `__version__` in `src/__init__.py`.

## [Unreleased]

### Added

- AWS CLI authentication and Terraform deployment runbook, including IAM Identity Center,
  IAM login, safe diagnostics, HTTP 400 troubleshooting, and credential precedence
- Terraform dependency lock file and ignored local state/configuration artifacts
- `docs/reference/ci-cd.md` documenting the four GitHub Actions workflows, the AI quality
  gate, and every secret and repository variable the pipeline consumes
- `docs/README.md` as an index for the Diátaxis tree
- Configuration reference for the storage backend (`DATA_BACKEND`, `S3_BUCKET`,
  `S3_PREFIX`), including the `Config.validate()` failure modes and the S3 key layout
- Architecture sections covering both storage backends and the deployed AWS topology,
  including the plain-HTTP load balancer and the read-only instance role
- Deployment guide sections covering what the stack creates, the Terraform outputs to
  wire into repository secrets, how to populate a fresh stack, and how to roll out a new
  image with an instance refresh

### Changed

- The *Update market data* workflow takes its S3 prefix from the `S3_PREFIX` repository
  variable (default `market-data`) instead of hardcoding it, so it can no longer drift
  from the `s3_prefix` Terraform variable unnoticed
- `CONTRIBUTING.md` is now the canonical contributor workflow; `AGENTS.md` links to it
  instead of restating it

### Fixed

- README no longer claims the Docker container fetches market data on startup. The image
  excludes `data/` and the entrypoint only starts Streamlit, so `docker run` without a
  populated volume produced an empty dashboard. The section now documents the fetch step
  and the required mount
- `CONTRIBUTING.md` pre-PR checks now include `ruff format --check .` and coverage, which
  CI enforces but the checklist omitted
- Documented that `S3_PREFIX` defaults to empty in `src/config.py` while every deployed
  path assumes `market-data`

- `load_all_data` now lists S3 objects under the correct folder prefix. It previously
  built the prefix from `Config.s3_key("")`, producing a key like
  `market-data/processed/.csv` that matched no object, so a dashboard running with
  `DATA_BACKEND=s3` loaded no assets at all
- `load_all_data` now paginates the S3 listing, so buckets holding more than 1000
  objects no longer lose every asset past the first page

### Security

- Restricted the GitHub Actions OIDC trust to the protected `production` environment
- Replaced wildcard deployment actions with an explicit, resource-scoped policy and
  prevented the CI role from modifying its own IAM permissions

## [1.0.0] - 2026-08-07

### Added

- Diátaxis documentation under `docs/` (getting started, how-to guides, configuration and Python API reference, architecture explanation)
- `CONTRIBUTING.md` with test and docs-with-code expectations
- `CACHE_EXPIRY_HOURS` documented and listed in `.env.example` (Config attribute; Streamlit TTL remains hardcoded at 1 hour)

### Changed

- README rewritten as a documentation hub with accurate clone URL, install/run order, and links into `docs/`
- Softened project description to match current scope (local CSV + Streamlit)

### Fixed

- Removed broken screenshot links pointing at missing `assets/screenshots/` files
- Aligned environment documentation with `.env.example` and `src/config.py` (including `COINGECKO_API_URL`)

[1.0.0]: https://github.com/fsoaz/financial-market-dashboard/releases/tag/v1.0.0
