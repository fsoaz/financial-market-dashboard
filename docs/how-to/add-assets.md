# How to add assets

Change which stocks, indexes, and cryptocurrencies the app fetches and displays.

## Prefer `.env`

Edit `.env` in the repository root (copy from `.env.example` if needed):

```env
DEFAULT_STOCKS=PETR4.SA,VALE3.SA,AAPL,MSFT,GOOGL
DEFAULT_INDEXES=^BVSP,^GSPC,^IXIC,^DJI
DEFAULT_CRYPTO=bitcoin,ethereum,solana,cardano
```

Rules:

- Use comma-separated lists with no spaces required (spaces around commas are stripped).
- Stocks and indexes use Yahoo Finance ticker symbols (for example `AAPL`, `PETR4.SA`, `^GSPC`).
- Indexes that start with `^` are tagged as indexes automatically.
- Crypto uses CoinGecko coin IDs (for example `bitcoin`, not `BTC`).

See [Configuration](../reference/configuration.md) for every environment variable.

## Apply the change

1. Save `.env`.
2. From the repository root, fetch data for the new list:

   ```bash
   python main.py
   ```

3. If the dashboard is already running, click **Refresh Data** in the sidebar.

## Verify

- New CSV files exist under `data/raw/` and `data/processed/` for each symbol (crypto files use the coin ID as the filename stem).
- The asset appears in dashboard dropdowns.

## Failure modes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Symbol marked `failed` in `main.py` output | Invalid Yahoo ticker | Confirm the symbol on Yahoo Finance |
| Crypto fetch fails | Wrong CoinGecko ID or rate limit | Use the [CoinGecko coins list](https://www.coingecko.com/en/api); wait and retry |
| Dashboard still shows old list only | Cache not cleared, or CSV missing | Re-run `main.py`, then **Refresh Data** |

> **Note:** Editing `Config` defaults in `src/config.py` also works, but `.env` keeps local choices out of version control. Do not commit a filled `.env` with secrets or personal lists you do not want public.
