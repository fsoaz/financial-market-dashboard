# Troubleshooting

Fixes for the failure modes that show up most often during setup and daily use.

## 1. Dashboard shows no assets

**Symptoms:** Empty dropdowns, blank pages, or no KPI cards after starting Streamlit.

**Causes:**

- You have not run `python main.py` yet (`data/processed/` has no CSVs).
- You ran `main.py` from a directory other than the repository root, so files landed elsewhere or paths did not match.
- Fetch failed for every symbol (network or API errors).

**Fix:**

```bash
cd /path/to/financial-market-dashboard
source venv/bin/activate
python main.py
streamlit run src/dashboard.py
```

Confirm files exist:

```bash
ls data/processed/
```

If the directory is empty, check the `main.py` summary for `failed` assets and see section 2.

---

## 2. yfinance or CoinGecko fetch failures

**Symptoms:** `main.py` prints `failed` for one or more symbols; logs mention `DataFetchError`.

**Causes:**

- Invalid stock/index ticker or crypto coin ID
- Network timeout or temporary API outage
- CoinGecko rate limiting on the free public API

**Fix:**

- Verify stock/index symbols on Yahoo Finance (for example `PETR4.SA`, `^BVSP`).
- Verify crypto IDs on CoinGecko (use `bitcoin`, not `BTC`).
- Wait a few minutes and re-run `python main.py` if you hit rate limits.
- Raise log detail temporarily:

  ```env
  LOG_LEVEL=DEBUG
  ```

  Then re-run `python main.py` and read the traceback.

`fetch_all_market_data` skips failed symbols and continues with the rest. A partial success still writes CSVs for the assets that succeeded.

---

## 3. Charts look stale after updating data

**Symptoms:** You ran `python main.py` again, but the UI still shows old prices.

**Cause:** Streamlit caches loaded processed CSVs with a 1-hour TTL (`@st.cache_data(ttl=3600)` in `src/dashboard.py`).

**Fix:**

1. Click **Refresh Data** in the sidebar, or
2. Stop Streamlit (`Ctrl+C`) and run `streamlit run src/dashboard.py` again.

---

## 4. Import errors when running the dashboard

**Symptoms:** `ModuleNotFoundError: No module named 'src'` or similar.

**Fix:** Always start Streamlit from the repository root:

```bash
streamlit run src/dashboard.py
```

`src/dashboard.py` adds the repo root to `sys.path` so `src.*` imports work when Streamlit puts `src/` on the path. Running from another working directory can still break relative data paths.

---

## Still stuck?

- Read [Architecture](../explanation/architecture.md) for how data moves from APIs to the UI.
- Open an issue with the full `main.py` summary and relevant log lines (no secrets from `.env`).
