# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup (Python 3.12+)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Fetch + process market data into data/raw and data/processed
python main.py

# Launch the Streamlit dashboard (reads CSVs from data/)
streamlit run src/dashboard.py

# Tests
pytest                                # all
pytest tests/test_indicators.py -v    # single file
pytest tests/test_indicators.py::TestDailyReturn::test_basic_daily_return  # single test
pytest --cov=src --cov-report=html    # coverage
```

There is no linter configured. No pytest config file — discovery uses defaults (`tests/`, `test_*.py`).

## Architecture

Two-stage pipeline: **`main.py` ingests data → CSV files on disk → `dashboard.py` reads CSVs**. The dashboard and the fetcher communicate only through the `data/` directory, not in-process. Run `main.py` before the dashboard has fresh data to show.

Data flow in `update_market_data()` (main.py):
`fetch_all_market_data` (api.py) → `clean_data` (utils.py) → `save_to_csv` raw → `add_financial_indicators` (indicators.py) → `save_to_csv` processed.

Module roles:
- **src/config.py** — `Config` class, single source for paths, default asset lists, and env vars (loaded from `.env` via python-dotenv). Imported by nearly everything. `Config.ensure_directories()` runs on import. Asset defaults are Brazilian + US (e.g. `PETR4.SA`, `^BVSP`).
- **src/api.py** — external fetching. Stocks/indexes via `yfinance`; crypto via CoinGecko REST. Raises `DataFetchError`; `fetch_all_market_data` catches per-symbol and skips failures rather than aborting.
- **src/indicators.py** — pure pandas/numpy math. `add_financial_indicators` adds the basic columns saved to processed CSVs (daily_return, cumulative_return, drawdown). `add_technical_indicators` (SMA/EMA/RSI/MACD/Bollinger) exists but is **not** wired into the main pipeline — it's called on demand.
- **src/utils.py** — I/O, cleaning, formatting, correlation. CSV load/save go through `Config.get_csv_path`.
- **src/dashboard.py** — all Streamlit UI; imports from `indicators` and `utils`. No business logic beyond presentation. Loaded data is cached in-process via `@st.cache_data` (1h TTL); the sidebar "Refresh Data" button clears it. There is no custom disk-cache layer — `CACHE_EXPIRY_HOURS` in `Config` is currently unused.

## Conventions that matter

- **Column names are lowercase snake_case everywhere internally**: `date, symbol, asset_type, open, high, low, close, volume, adj_close`. `fetch_stock_data` normalizes yfinance's mixed-case columns at the boundary. New code consuming DataFrames should assume this schema. `asset_type` is one of `stocks`, `indexes`, `crypto`.
- **Crypto OHLC is synthetic**: CoinGecko's `market_chart` endpoint gives close prices only, so `fetch_crypto_data` sets `open=high=low=close` and `volume=0`. Candlestick charts are therefore only meaningful for stocks/indexes — the dashboard falls back to line charts for crypto. Don't write logic that trusts crypto high/low/volume.
- **Indexes vs stocks** are distinguished by the `^` symbol prefix (e.g. `^GSPC`), set in `fetch_stock_data`.
- **CSVs are keyed by symbol**: one file per asset, `{symbol}.csv`, in `data/raw/` or `data/processed/`. `load_all_data` derives the symbol from the filename stem.
- **Dates are timezone-aware and parsed with `utc=True`**: yfinance timestamps cross DST boundaries, so a single ticker's CSV mixes offsets (e.g. `-05:00` and `-04:00`). `convert_dates` (used by `load_from_csv`) must parse with `utc=True` or pandas raises "Mixed timezones detected" and the asset is silently dropped. Any new code building `Timestamp`s to compare against the `date` column must match its tz (see `filter_by_date_range`'s YTD branch).
- **Cross-asset alignment is by calendar date, not row position**: assets have different histories (2y stocks vs 1y crypto) and different RangeIndexes. `calculate_correlation_matrix` indexes returns by normalized date before joining; never `pd.DataFrame({sym: series})` on the raw RangeIndex — it correlates unrelated dates.

## Caveats / known gaps

- `load_from_csv` swallows all exceptions and returns `None`, so a bad/unreadable CSV makes an asset vanish from the dashboard with no visible error. Check logs if an expected asset is missing.
- The technical-indicator functions (`add_technical_indicators`, `calculate_macd`, `calculate_bollinger_bands`) have no caller yet — public API surface for a documented-but-unwired feature, not dead code.
