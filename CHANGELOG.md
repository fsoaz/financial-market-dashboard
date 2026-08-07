# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
aligned with `__version__` in `src/__init__.py`.

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
