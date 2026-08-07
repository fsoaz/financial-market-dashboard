# Python API reference

This project exposes a Python module API for fetching, cleaning, and analyzing market data. There is no first-party HTTP API.

Import from the repository root with the package on `PYTHONPATH` (normal when you run `python main.py` or `streamlit run src/dashboard.py` from the root).

## `main` — data update

### `update_market_data`

Download market data, write raw CSVs, optionally add indicators and write processed CSVs.

```python
from main import update_market_data

results = update_market_data(
    stocks=["AAPL", "MSFT"],
    indexes=["^GSPC"],
    cryptos=["bitcoin"],
    save_processed=True,
)
# results -> {"AAPL": "success", "MSFT": "success", ...}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stocks` | `list[str] \| None` | `Config.DEFAULT_STOCKS` | Equity tickers |
| `indexes` | `list[str] \| None` | `Config.DEFAULT_INDEXES` | Index tickers |
| `cryptos` | `list[str] \| None` | `Config.DEFAULT_CRYPTO` | CoinGecko IDs |
| `save_processed` | `bool` | `True` | Also write `data/processed/` with indicators |

**Returns:** `dict[str, str]` mapping symbol to `"success"` or `"failed"`.

**Failure modes:** Per-asset exceptions during clean/save set that symbol to `"failed"`. A total fetch failure returns an empty dict and logs an error.

CLI entry point: `python main.py` calls `main()`, which runs `update_market_data()` with defaults and prints a summary.

---

## `src.api` — external data

### `DataFetchError`

Raised when a single-asset fetch fails (empty response, HTTP error, or unexpected exception wrapped from yfinance/requests).

### `fetch_stock_data`

```python
from src.api import fetch_stock_data

df = fetch_stock_data("PETR4.SA", period="2y")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbol` | `str` | required | Yahoo Finance ticker |
| `period` | `str` | `"2y"` | yfinance history period |

**Returns:** DataFrame with columns including `date`, `symbol`, `asset_type`, `open`, `high`, `low`, `close`, `volume` (and `adj_close` when available). `asset_type` is `"indexes"` when `symbol` starts with `^`, otherwise `"stocks"`.

**Raises:** `DataFetchError` if no data is returned or the request fails.

### `fetch_crypto_data`

```python
from src.api import fetch_crypto_data

df = fetch_crypto_data("ethereum", days=365)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `coin_id` | `str` | required | CoinGecko coin ID |
| `days` | `int` | `365` | History length in days |

**Returns:** DataFrame with `date`, `symbol`, `asset_type` (`"crypto"`), `open`, `high`, `low`, `close`, `volume`. Open/high/low are approximated from close on the `market_chart` endpoint; volume is set to `0` for that endpoint.

**Raises:** `DataFetchError` on HTTP or parse failures.

### `fetch_all_market_data`

```python
from src.api import fetch_all_market_data

data = fetch_all_market_data(
    stocks=["AAPL"],
    indexes=["^BVSP"],
    cryptos=["solana"],
)
```

Fetches each symbol independently. Failed symbols are logged and skipped; successful ones appear in the returned `dict[str, pd.DataFrame]`.

### `validate_response`

```python
from src.api import validate_response

ok = validate_response(df, required_columns=["date", "close"])
```

**Returns:** `False` if the DataFrame is empty or missing required columns; otherwise `True`.

---

## `src.indicators` — financial metrics

All percentage returns and drawdowns are expressed as percentages (not decimals).

### Core series helpers

| Function | Signature | Returns |
|----------|-----------|---------|
| `calculate_daily_return` | `(prices: Series) -> Series` | Daily % returns (`pct_change * 100`) |
| `calculate_cumulative_return` | `(prices: Series) -> Series` | Cumulative % return from first price |
| `calculate_volatility` | `(returns: Series, annualize: bool = True) -> float` | Std of returns; annualized with √252 when `annualize=True` |
| `calculate_drawdown` | `(prices: Series) -> Series` | Running drawdown % from peak |
| `calculate_max_drawdown` | `(prices: Series) -> float` | Minimum drawdown (most negative) |

```python
from src.indicators import calculate_daily_return, calculate_volatility

returns = calculate_daily_return(df["close"])
vol = calculate_volatility(returns, annualize=True)
```

### Frame-level helpers

#### `add_financial_indicators`

Adds `daily_return`, `cumulative_return`, and `drawdown` columns.

```python
from src.indicators import add_financial_indicators

processed = add_financial_indicators(df, price_column="close")
```

#### `calculate_summary_statistics`

```python
from src.indicators import calculate_summary_statistics

stats = calculate_summary_statistics(df, price_column="close")
# keys: current_price, daily_return, cumulative_return,
#        volatility_daily, volatility_annual, max_drawdown,
#        start_date, end_date
```

Returns `{}` if the frame is empty or has fewer than two valid prices.

### Optional technical indicators

| Function | Notes |
|----------|--------|
| `calculate_sma(prices, window=20)` | Simple moving average |
| `calculate_ema(prices, window=20)` | Exponential moving average |
| `calculate_rsi(prices, period=14)` | RSI 0–100; windows with zero loss → 100 |
| `calculate_macd(prices, fast=12, slow=26, signal=9)` | Returns `(macd, signal, histogram)` |
| `calculate_bollinger_bands(prices, window=20, num_std=2.0)` | Returns `(upper, middle, lower)` |
| `add_technical_indicators(df, price_column="close")` | Adds SMA/EMA/RSI/MACD/Bollinger columns |

---

## `src.utils` — I/O and helpers

| Function | Purpose |
|----------|---------|
| `setup_logging(level=None)` | Configure root logging (`Config.LOG_LEVEL` default) |
| `clean_data(df)` | Drop all-NaN rows, ffill/bfill, dedupe on `date`+`symbol`, sort by date |
| `convert_dates(df, date_column="date")` | Parse dates with `utc=True` (handles mixed DST offsets) |
| `standardize_columns(df)` | Lowercase, underscore column names |
| `save_to_csv(df, symbol, processed=False)` | Write under `data/raw/` or `data/processed/` |
| `load_from_csv(symbol, processed=False)` | Load one CSV or return `None` |
| `load_all_data(processed=False)` | Load all `*.csv` in the chosen directory |
| `normalize_prices(df, price_column="close")` | Scale series to start at 100 |
| `calculate_correlation_matrix(data, price_column="close")` | Correlate daily returns aligned by calendar date |
| `format_currency(value, currency="USD")` | Display helper (`$`, `R$`, etc.) |
| `format_percentage(value, decimals=2)` | Display helper with optional `+` sign |
| `get_date_range_options()` | UI labels: `1 Month` … `Max` |
| `filter_by_date_range(df, date_range, date_column="date")` | Filter by those labels |

```python
from src.utils import load_all_data, normalize_prices

data = load_all_data(processed=True)
normalized = normalize_prices(data["AAPL"])
```

---

## `src.config` — `Config`

Class attributes (see [Configuration](configuration.md)):

- Paths: `BASE_DIR`, `DATA_DIR`, `PROCESSED_DIR`
- Assets: `DEFAULT_STOCKS`, `DEFAULT_INDEXES`, `DEFAULT_CRYPTO`
- APIs: `COINGECKO_API_URL`
- `CACHE_EXPIRY_HOURS`, `LOG_LEVEL`
- Methods: `ensure_directories()`, `get_csv_path(symbol, processed=False)`

Directories are created on import of `src.config`.

---

## Related

- [Architecture](../explanation/architecture.md)
- [Getting started](../getting-started.md)
