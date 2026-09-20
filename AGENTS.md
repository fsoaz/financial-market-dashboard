# Repository Guidelines

[`CONTRIBUTING.md`](CONTRIBUTING.md) is canonical for contributor workflow: branch naming,
the checks to run before a PR, and the docs-with-code rule. This file adds the repository
map and the execution rules that apply to automated coding agents.

## Project Structure & Module Organization

This Python 3.12+ application separates market-data ingestion from its Streamlit dashboard. `main.py` fetches and processes data; `src/dashboard.py` reads stored CSVs and renders Plotly charts. In `src/`, `api.py` handles providers, `indicators.py` implements calculations, `utils.py` handles storage and cleaning, and `config.py` centralizes settings.

Tests live in `tests/`. Tracked sample CSVs live in `data/raw/` and `data/processed/`; refreshing data can modify them. Documentation and screenshots are under `docs/` and `docs/assets/`. AWS infrastructure lives in `infra/terraform/`, CI workflows in `.github/workflows/`, and the quality gate in `scripts/quality_gate.py` (documented in `docs/reference/ci-cd.md`).

## Build, Test, and Development Commands

Run commands from the repository root in an activated virtual environment:

- `pip install -r requirements.txt -r requirements-dev.txt` — install application, test, and lint dependencies.
- `python main.py` — fetch market data and regenerate CSVs.
- `streamlit run src/dashboard.py` — serve the dashboard at `http://localhost:8501`.
- `ruff check .` and `ruff format --check .` — reproduce CI lint and formatting checks; use `ruff format .` to format.
- `pytest` — run the test suite.
- `pytest --cov=src --cov-report=json --junitxml=test-results.xml` — produce coverage and quality-gate inputs.
- `docker build -t financial-market-dashboard .` — build the application image.

## Coding Style & Naming Conventions

Use four-space indentation, 100-character lines, and Ruff's Python 3.12 configuration in `pyproject.toml`. Use `snake_case` for functions, variables, and DataFrame columns; `PascalCase` for classes; and uppercase names for constants. Follow existing type hints and docstrings. Keep financial calculations in `indicators.py` and storage logic in `utils.py`.

## Testing Guidelines

Use pytest and pytest-cov. Name files `test_*.py` and functions `test_*`; group related cases in `Test*` classes where useful. Run focused checks with `pytest tests/test_utils.py -v`. Add regression cases for changed behavior, using `tmp_path` and `monkeypatch` to isolate storage and external services. The CI quality gate defaults to 70% coverage of `src/`, configurable through `QUALITY_GATE_MIN_COVERAGE`.

## Commit & Pull Request Guidelines

Follow [`CONTRIBUTING.md`](CONTRIBUTING.md) for branch naming, pre-PR checks, and the PR checklist. In addition: commits use prefixes such as `feat:` and `test:` with concise, descriptive subjects; explain the problem, changes, and verification in each PR; update relevant documentation in the same PR and `CHANGELOG.md` for user-visible changes.

## Security & Configuration

Copy `.env.example` to `.env` for local configuration; never commit credentials. When changing environment variables, update `.env.example` and `docs/reference/configuration.md` together. Local CSV storage is the default; S3 storage requires `DATA_BACKEND=s3` and `S3_BUCKET`, and `S3_PREFIX` must match the `s3_prefix` Terraform variable.

## Execution Rules

- Track recorded time and explicit remaining-work estimates against any stated task budget and the 15-hour project cap. Mark missing prior usage as unknown, never zero or invented. If either limit is likely to be exceeded, stop and report progress, remaining work, and the estimated overrun; state any uncertainty caused by missing records.
- Choose the simplest implementation that meets the acceptance criteria. Keep changes focused and proportional; do not implement hypothetical future requirements.
- Reuse existing code where appropriate. Add abstractions, layers, frameworks, dependencies, configuration, or extension points only when required by the task or an applicable architectural decision.
- Refactor only as needed to complete the task. Record unrelated improvement opportunities in review notes.
- Explain which requirement each architectural change or new dependency addresses, and obtain any required approval before introducing it.
- Preserve existing behavior unless the task requires a change. Add or update tests to verify required behavior changes.
- Preserve unrelated working-tree changes. Limit the final diff to the requested task and necessary supporting updates.
