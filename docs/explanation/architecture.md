# Architecture

Why the app uses a CSV pipeline, how Streamlit serves charts, and where external APIs fit.

## Goals

- Keep the UI fast and offline-friendly after the first fetch
- Separate network I/O from interactive analysis
- Use simple, inspectable storage (CSV) suitable for education and local demos

There is no application database and no first-party HTTP API. Streamlit is the only process that serves the UI.

## Data flow

```mermaid
flowchart LR
  subgraph external [External APIs]
    YF[yfinance Yahoo]
    CG[CoinGecko HTTP]
  end
  subgraph etl [ETL CLI]
    Main[main.py update_market_data]
    API[src.api fetch_*]
    Ind[src.indicators]
    Util[src.utils CSV I/O]
  end
  subgraph storage [Local files]
    Raw[data/raw CSV]
    Proc[data/processed CSV]
  end
  subgraph ui [Streamlit UI]
    Dash[src.dashboard]
    Cache["st.cache_data TTL 1h"]
  end
  YF --> API
  CG --> API
  Main --> API
  API --> Util
  Util --> Raw
  Util --> Ind
  Ind --> Util
  Util --> Proc
  Proc --> Cache
  Cache --> Dash
```

1. **`python main.py`** calls `update_market_data`.
2. **`src.api`** pulls equities/indexes via yfinance and crypto via CoinGecko.
3. **`src.utils.clean_data`** normalizes rows; raw frames are saved under `data/raw/`.
4. **`add_financial_indicators`** adds returns and drawdown; processed frames go to `data/processed/`.
5. **`streamlit run src/dashboard.py`** loads processed CSVs through `load_all_data(processed=True)`, caches them for one hour, and routes sidebar pages to render functions.

The UI does not call yfinance or CoinGecko on each page view. Refresh market data with the CLI (or a scheduled job), then click **Refresh Data** in the sidebar.

## Why CSV instead of a database

- Transparent: open any file in a spreadsheet or `pandas.read_csv`
- Zero ops: no Postgres/Mongo to install for local use
- Fits the roadmap stage: database integration remains a future option

Trade-off: concurrent writers, large history, and multi-user hosting are out of scope for the current design.

## Caching

| Layer | Mechanism | Behavior |
|-------|-----------|----------|
| Streamlit | `@st.cache_data(ttl=3600)` | In-process; cleared by **Refresh Data** or process restart |
| Config | `CACHE_EXPIRY_HOURS` | Read into `Config` but not wired to the dashboard TTL yet |

See [Configuration](../reference/configuration.md).

## Module responsibilities

| Module | Responsibility |
|--------|----------------|
| `main.py` | Orchestrate fetch → clean → indicators → save |
| `src/api.py` | External HTTP/Yahoo access and `DataFetchError` |
| `src/indicators.py` | Returns, volatility, drawdown, optional technicals |
| `src/utils.py` | Logging, cleaning, CSV paths, correlation, formatting |
| `src/config.py` | Env-backed settings and directory layout |
| `src/dashboard.py` | Streamlit pages and Plotly charts |

## Asset typing

- Tickers starting with `^` are labeled `indexes` when fetched as stocks/indexes.
- CoinGecko IDs are labeled `crypto`.
- Everything else from yfinance equity fetches is labeled `stocks`.

## Related

- [Getting started](../getting-started.md)
- [Schedule data updates](../how-to/schedule-data-updates.md)
- [Python API](../reference/python-api.md)
