# Contributing

Thanks for improving the Financial Market Dashboard. This guide covers how to propose changes safely and keep documentation accurate.

This file is the canonical source for contributor workflow. `AGENTS.md` adds rules specific
to automated coding agents and defers to this file for everything else.

## Development setup

1. Fork and clone the repository.
2. Create a virtual environment and install dependencies (see [Getting started](docs/getting-started.md)).
3. Copy `.env.example` to `.env` for local overrides. Never commit `.env`.
4. Install lint tooling: `pip install -r requirements-dev.txt`.

## Branch naming

Use short, descriptive branch names:

- `fix/empty-dashboard-docs`
- `feat/add-rsi-overlay`
- `docs/troubleshooting-rate-limits`

## Making changes

1. Create a branch from `main`.
2. Implement the change.
3. Update documentation in the **same** pull request when behavior, config, or public APIs change. Do not defer docs to a follow-up PR.
4. Run the same checks CI runs, before opening a PR:

   ```bash
   ruff check .
   ruff format --check .   # use `ruff format .` to fix
   pytest --cov=src
   ```

   CI fails the build on any of the three. Coverage of `src/` must stay at or above the
   quality gate threshold (70% by default) — see
   [CI and quality gate](docs/reference/ci-cd.md).

5. Open a pull request with a clear description of *why* the change exists and how you verified it.

## Code expectations

- Match existing style in `src/` and `tests/`.
- Prefer realistic symbols in examples and tests (`AAPL`, `PETR4.SA`, `bitcoin`) over `foo`/`bar`.
- Keep secrets and personal API keys out of the repository.

## Documentation

Docs follow Diátaxis layout under `docs/`:

- Tutorials → `docs/getting-started.md`
- How-to guides → `docs/how-to/`
- Reference → `docs/reference/`
- Explanation → `docs/explanation/`

The [README](README.md) is the hub. Link to deeper pages instead of duplicating long reference material.

When you change environment variables, update both `.env.example` and `docs/reference/configuration.md`.

## Pull request checklist

- [ ] `ruff check .`, `ruff format --check .`, and `pytest` pass locally
- [ ] Coverage of `src/` is at or above the quality gate threshold
- [ ] Docs updated if user-facing or developer-facing behavior changed
- [ ] No `.env` or credentials committed
- [ ] CHANGELOG updated for user-visible changes (see [CHANGELOG.md](CHANGELOG.md))
