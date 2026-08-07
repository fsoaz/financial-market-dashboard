# Configuration reference

Runtime settings come from environment variables loaded by `python-dotenv` into the `Config` class in `src/config.py`.

Copy the template and edit as needed:

```bash
cp .env.example .env
```

Do not commit `.env`. Keep `.env.example` as the shared template.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_STOCKS` | `PETR4.SA,VALE3.SA,AAPL,MSFT` | Comma-separated Yahoo Finance equity tickers |
| `DEFAULT_INDEXES` | `^BVSP,^GSPC,^IXIC,^DJI` | Comma-separated Yahoo Finance index tickers |
| `DEFAULT_CRYPTO` | `bitcoin,ethereum,solana` | Comma-separated CoinGecko coin IDs |
| `COINGECKO_API_URL` | `https://api.coingecko.com/api/v3` | CoinGecko API base URL |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `CACHE_EXPIRY_HOURS` | `1` | Stored on `Config.CACHE_EXPIRY_HOURS` |

### `CACHE_EXPIRY_HOURS` behavior

`Config` reads `CACHE_EXPIRY_HOURS`, but the Streamlit dashboard does **not** use that value today. Chart data is cached with a hardcoded TTL of 3600 seconds (`@st.cache_data(ttl=3600)` in `src/dashboard.py`). Changing `CACHE_EXPIRY_HOURS` in `.env` does not change UI cache duration until the dashboard is wired to `Config`.

Use **Refresh Data** in the sidebar to clear the Streamlit cache immediately.

## Paths (not env-driven)

| Attribute | Location |
|-----------|----------|
| `Config.BASE_DIR` | Repository root |
| `Config.DATA_DIR` | `data/raw/` |
| `Config.PROCESSED_DIR` | `data/processed/` |

CSV filenames are `{symbol}.csv` (crypto uses the CoinGecko ID as the stem). Symbols that contain characters unsafe for filenames (for example `^` in `^GSPC`) are used as-is in the filename.

## Example `.env`

```env
DEFAULT_STOCKS=PETR4.SA,VALE3.SA,AAPL,MSFT
DEFAULT_INDEXES=^BVSP,^GSPC,^IXIC,^DJI
DEFAULT_CRYPTO=bitcoin,ethereum,solana
COINGECKO_API_URL=https://api.coingecko.com/api/v3
LOG_LEVEL=INFO
CACHE_EXPIRY_HOURS=1
```

## Related

- [Add assets](../how-to/add-assets.md)
- [Python API](python-api.md) — `Config` usage from code
