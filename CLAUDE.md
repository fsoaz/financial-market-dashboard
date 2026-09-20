# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup (Python 3.12+)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # lint tooling (ruff)

# Fetch + process market data into data/raw and data/processed
python main.py

# Launch the Streamlit dashboard (reads CSVs from data/)
streamlit run src/dashboard.py

# Tests
pytest                                # all
pytest tests/test_indicators.py -v    # single file
pytest tests/test_indicators.py::TestDailyReturn::test_basic_daily_return  # single test
pytest --cov=src --cov-report=html    # coverage

# Lint (config in pyproject.toml: line-length 100, py312 target, rules E/F/W/I/UP/B)
ruff check .
ruff format --check .

# Quality gate (needs coverage.json; GROQ_API_KEY optional locally — absent = BLOQUEADO)
pytest --cov=src --cov-report=json --junitxml=test-results.xml
python scripts/quality_gate.py --coverage-file coverage.json --junit-file test-results.xml

# Terraform (checked in CI on any infra/terraform/** PR)
cd infra/terraform && terraform fmt -check && terraform validate

# Docker — serves the dashboard only; it does NOT fetch data (see "Docker image" below)
docker build -t financial-market-dashboard .
docker run -p 8501:8501 -e DATA_BACKEND=s3 -e S3_BUCKET=... -e S3_PREFIX=market-data financial-market-dashboard
```

`pytest` config lives in `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`) rather than a separate ini file.

## CI / CD

Four workflows in `.github/workflows/`:

- **ci.yml** (push/PR to `main`, manual) — `lint` (ruff check + format check) and `test` (pytest with term/xml/json coverage + JUnit report, uploaded as the `quality-gate-inputs` artifact), then `quality-gate`.
- **docker-publish.yml** — triggers on a *successful CI run* on `main` (`workflow_run`), builds the image and pushes it to ECR tagged with the head SHA and `latest`. Assumes an AWS role via OIDC.
- **data-update.yml** — cron `15 22 * * 1-5` plus manual. Runs `main.py` with `DATA_BACKEND=local`, asserts both `data/raw` and `data/processed` are non-empty, then `aws s3 sync`s them to the private bucket under `market-data/{raw,processed}` with `--delete`.
- **terraform.yml** — plan on PRs touching `infra/terraform/**`; apply only on `workflow_dispatch`. Uses the `production` environment and an S3 remote state backend written at runtime into `backend.hcl`.

The **quality gate** (`scripts/quality_gate.py`) is deterministic-first: coverage below `QUALITY_GATE_MIN_COVERAGE` (default 70%) blocks immediately without calling the model; only when coverage passes does it ask Groq (`GROQ_MODEL`, default `openai/gpt-oss-20b`) for a verdict. Things to preserve when touching it:

- **The decision tokens are Portuguese — `APROVADO` / `BLOQUEADO`** — and so are its user-facing messages. `parse_decision` raises unless the response contains exactly one distinct token, so don't loosen the prompt or translate the tokens independently of the parser.
- **It is stdlib-only by design** (`urllib`, not `requests`) so CI needs no extra install step. Keep it that way.
- A missing `GROQ_API_KEY` is treated as BLOQUEADO, not skipped. The gate job is skipped for PRs from forks (no secrets).
- `[tool.coverage.run] source = ["src"]`, so `scripts/` and `main.py` are not measured; coverage percentages reflect `src/` only.

## Architecture

Two-stage pipeline: **`main.py` ingests data → CSVs → `dashboard.py` reads CSVs**. The dashboard and the fetcher communicate only through storage, never in-process. Run `main.py` before the dashboard has fresh data to show.

Data flow in `update_market_data()` (main.py):
`fetch_all_market_data` (api.py) → `clean_data` (utils.py) → `save_to_csv` raw → `add_financial_indicators` (indicators.py) → `save_to_csv` processed.

Module roles:
- **src/config.py** — `Config` class, single source for paths, default asset lists, storage backend, and env vars (loaded from `.env` via python-dotenv). Imported by nearly everything. `Config.ensure_directories()` runs on import (it creates the local dirs even under the S3 backend). Asset defaults are Brazilian + US (e.g. `PETR4.SA`, `^BVSP`).
- **src/api.py** — external fetching. Stocks/indexes via `yfinance` (`period="2y"`); crypto via CoinGecko REST (`days=365`). Raises `DataFetchError`; `fetch_all_market_data` catches per-symbol and skips failures rather than aborting.
- **src/indicators.py** — pure pandas/numpy math. `add_financial_indicators` adds the columns saved to processed CSVs (`daily_return`, `cumulative_return`, `drawdown`). `add_technical_indicators` (SMA/EMA/RSI/MACD/Bollinger) exists but is **not** wired into the main pipeline — it's called on demand.
- **src/utils.py** — I/O, cleaning, formatting, correlation, and the local/S3 storage switch.
- **src/dashboard.py** — all Streamlit UI; imports from `indicators` and `utils`. No business logic beyond presentation. Loaded data is cached in-process via `@st.cache_data(ttl=3600)`; the sidebar "Refresh Data" button sets a session flag that clears the cache on the next run. There is no custom disk-cache layer — `CACHE_EXPIRY_HOURS` in `Config` is currently unused.

### Storage backend (local vs S3)

`Config.DATA_BACKEND` is `local` (default) or `s3`, validated by `Config.validate()`, which every I/O entry point in `utils.py` calls first. `save_to_csv`, `load_from_csv`, and `load_all_data` each branch on it:

- **local** — files under `Config.DATA_DIR` / `Config.PROCESSED_DIR` via `Config.get_csv_path`.
- **s3** — objects at `Config.s3_key(symbol, processed)`, i.e. `{S3_PREFIX}/{raw|processed}/{symbol}.csv` in `S3_BUCKET`. The layout deliberately mirrors the local one, which is what lets `data-update.yml` produce files locally and plain `aws s3 sync` them up. **Use `Config.s3_folder(processed)` for listing and `Config.s3_key(symbol, processed)` for a single object** — the two are separate helpers precisely because `s3_key("")` is not a valid listing prefix (it ends in `.csv` and matches nothing; this was a real bug).

`boto3` is imported **lazily inside the S3 branches**, so local development and the test suite never import it. Keep new backend code in this shape rather than importing boto3 at module level. Any listing must go through a **paginator** (`get_paginator("list_objects_v2")`) — a bare `list_objects_v2` call caps out at 1000 keys and drops the rest without erroring. `S3_BUCKET` is required when the backend is `s3` (`Config.validate` raises otherwise).

### Deployment (infra/terraform)

Terraform provisions: a private, versioned, encrypted S3 data bucket; an ECR repo; and an EC2 Auto Scaling group behind an ALB (port 8501 target group, `/_stcore/health`). `user-data.sh.tftpl` pulls the ECR image and runs the container with `DATA_BACKEND=s3`, `S3_BUCKET`, `S3_PREFIX` — **production reads market data from S3, not from disk**. `github-oidc.tf` defines the OIDC provider and the CI deploy role, scoped to the `production` environment. Remote state is an S3 backend configured from `backend.hcl` (see `backend.hcl.example`, `terraform.tfvars.example`).

### Docker image

`docker-entrypoint.sh` only launches Streamlit (`--server.address=0.0.0.0 --server.port=8501 --server.headless=true`). It does **not** run `main.py`, and `.dockerignore` excludes `data`, `tests`, and `docs` — so the image ships with no CSVs. A container started with the default `DATA_BACKEND=local` therefore shows an **empty dashboard**; the image expects the S3 backend (as the Terraform user-data supplies) or a mounted `data/` volume. The image runs as non-root `appuser` (uid 1000) and has a `HEALTHCHECK` against `/_stcore/health`.

## Conventions that matter

- **Column names are lowercase snake_case everywhere internally**: `date, symbol, asset_type, open, high, low, close, volume, adj_close`. `fetch_stock_data` normalizes yfinance's mixed-case columns at the boundary. New code consuming DataFrames should assume this schema. `asset_type` is one of `stocks`, `indexes`, `crypto`.
- **Crypto OHLC is synthetic**: CoinGecko's `market_chart` endpoint gives close prices only, so `fetch_crypto_data` sets `open=high=low=close` and `volume=0`. Candlestick charts are therefore only meaningful for stocks/indexes — the dashboard falls back to line charts for crypto. Don't write logic that trusts crypto high/low/volume.
- **Indexes vs stocks** are distinguished by the `^` symbol prefix (e.g. `^GSPC`), set in `fetch_stock_data`.
- **CSVs are keyed by symbol**: one file/object per asset, `{symbol}.csv`, under `raw/` or `processed/`. `load_all_data` derives the symbol from the filename stem (local) or the key's last segment (S3), and sorts case-insensitively so asset order is deterministic — a regression test covers this.
- **Dates are timezone-aware and parsed with `utc=True`**: yfinance timestamps cross DST boundaries, so a single ticker's CSV mixes offsets (e.g. `-05:00` and `-04:00`). `convert_dates` (used by `load_from_csv`) must parse with `utc=True` or pandas raises "Mixed timezones detected" and the asset is silently dropped. Any new code building `Timestamp`s to compare against the `date` column must match its tz (see `filter_by_date_range`'s YTD branch).
- **Cross-asset alignment is by calendar date, not row position**: assets have different histories (2y stocks vs 1y crypto) and different RangeIndexes. `calculate_correlation_matrix` indexes returns by normalized tz-naive date before joining; never `pd.DataFrame({sym: series})` on the raw RangeIndex — it correlates unrelated dates.
- **`src.*` imports need the repo root on `sys.path`**: `streamlit run src/dashboard.py` puts `src/` on the path, not the root, so `dashboard.py` inserts the repo root itself before its `from src.… import` lines. Don't "tidy away" that insert or reorder it above the imports.
- **Committed sample data**: `data/raw` and `data/processed` CSVs are tracked in git (not gitignored), so the dashboard works on a fresh clone without running `main.py`. Running `main.py` will show them as modified.

## Caveats / known gaps

- **The quality gate currently blocks on every run**: total coverage is ~37% against a 70% minimum, because `src/dashboard.py` (676 lines, the largest module) has no tests at all — it never reaches the Groq call. Raising `dashboard.py` coverage, or lowering `QUALITY_GATE_MIN_COVERAGE`, is the only way to get a green gate.
- `load_from_csv` swallows all exceptions and returns `None`, so a bad/unreadable CSV makes an asset vanish from the dashboard with no visible error. Check logs if an expected asset is missing.
- The technical-indicator functions (`add_technical_indicators`, `calculate_macd`, `calculate_bollinger_bands`) have no caller yet — public API surface for a documented-but-unwired feature, not dead code. Same for `calculate_max_drawdown` and `api.validate_response`.
- `requirements.txt` pins `pathlib>=1.0.1`, the abandoned PyPI backport of the stdlib module. It is not imported anywhere and should be dropped rather than relied on.

## Docs

User-facing docs live under `docs/` (Diátaxis: getting-started, `how-to/`, `reference/`, `explanation/`), linked from the README hub. `CONTRIBUTING.md` requires docs to be updated in the same PR as behavior/config/API changes — keep `docs/reference/python-api.md` and `docs/reference/configuration.md` in sync when touching public functions or `Config`/`.env.example`. `CHANGELOG.md` follows Keep a Changelog, versioned against `__version__` in `src/__init__.py` (currently `1.0.0`, with unreleased infra/security entries).

Known docs drift: `docs/reference/configuration.md` does not yet document `DATA_BACKEND`, `S3_BUCKET`, or `S3_PREFIX`, though they are in `.env.example`. Add them there when you next touch config.
