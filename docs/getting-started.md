# Getting started

This tutorial takes you from a clean clone to a working dashboard in under 10 minutes.

## What you will do

1. Install dependencies
2. Fetch market data into local CSV files
3. Open the Streamlit dashboard
4. Confirm the four pages load with real data

## Prerequisites

- Python 3.12 or higher
- pip
- Network access to Yahoo Finance (via yfinance) and CoinGecko

## Step 1: Clone and install

```bash
git clone https://github.com/fsoaz/financial-market-dashboard.git
cd financial-market-dashboard

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

**Expected result:** The virtual environment is active and `pip list` shows `streamlit`, `yfinance`, `plotly`, and `pandas`.

## Step 2: Fetch market data

Run commands from the repository root so paths under `data/` resolve correctly.

```bash
python main.py
```

**Expected result:** Terminal output lists each configured asset as `success` or `failed`, and CSV files appear under `data/raw/` and `data/processed/`.

> **Warning:** If you skip this step, the dashboard loads with no assets. See [Troubleshooting](how-to/troubleshooting.md).

Default assets come from `.env` (or built-in defaults): Brazilian and US stocks, major indexes, and a few cryptocurrencies. Customize them later with [Add assets](how-to/add-assets.md).

## Step 3: Start the dashboard

```bash
streamlit run src/dashboard.py
```

**Expected result:** Streamlit prints a local URL. Your browser opens `http://localhost:8501`.

## Step 4: What you should see

Use the sidebar navigation and check:

- [ ] **Market Overview** — Select an asset (for example `AAPL` or `PETR4.SA`). KPI cards show current price, returns, volatility, and max drawdown.
- [ ] **Price Charts** — Candlestick or line chart responds to asset type and date range filters.
- [ ] **Financial Indicators** — Cumulative return, drawdown, and return distribution charts render.
- [ ] **Asset Comparison** — Select two or more assets. Normalized prices and a correlation heatmap appear.

After you run `python main.py` again, click **Refresh Data** in the sidebar so Streamlit clears its in-process cache and reloads the CSVs.

## Next steps

- [Add assets](how-to/add-assets.md) — Change default stocks, indexes, or crypto
- [Schedule data updates](how-to/schedule-data-updates.md) — Automate daily fetches
- [Architecture](explanation/architecture.md) — How the CSV pipeline and cache work
- [Python API](reference/python-api.md) — Call `update_market_data` from your own scripts
