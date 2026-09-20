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
| `DATA_BACKEND` | `local` | Where CSVs are read and written: `local` or `s3` |
| `S3_BUCKET` | *(empty)* | Bucket name. Required when `DATA_BACKEND=s3` |
| `S3_PREFIX` | *(empty)* | Key prefix placed before `raw/` and `processed/` |
| `DEFAULT_STOCKS` | `PETR4.SA,VALE3.SA,AAPL,MSFT` | Comma-separated Yahoo Finance equity tickers |
| `DEFAULT_INDEXES` | `^BVSP,^GSPC,^IXIC,^DJI` | Comma-separated Yahoo Finance index tickers |
| `DEFAULT_CRYPTO` | `bitcoin,ethereum,solana` | Comma-separated CoinGecko coin IDs |
| `COINGECKO_API_URL` | `https://api.coingecko.com/api/v3` | CoinGecko API base URL |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `CACHE_EXPIRY_HOURS` | `1` | Stored on `Config.CACHE_EXPIRY_HOURS` |

> **`S3_PREFIX` defaults differ.** `src/config.py` falls back to an empty prefix, but
> `.env.example`, `infra/terraform/variables.tf`, and `.github/workflows/data-update.yml`
> all assume `market-data`. Leaving `S3_PREFIX` unset while pointing at a deployed bucket
> reads from `raw/` and `processed/` at the bucket root, where nothing is written. Set it
> explicitly whenever you set `DATA_BACKEND=s3`.

### `CACHE_EXPIRY_HOURS` behavior

`Config` reads `CACHE_EXPIRY_HOURS`, but the Streamlit dashboard does **not** use that value today. Chart data is cached with a hardcoded TTL of 3600 seconds (`@st.cache_data(ttl=3600)` in `src/dashboard.py`). Changing `CACHE_EXPIRY_HOURS` in `.env` does not change UI cache duration until the dashboard is wired to `Config`.

Use **Refresh Data** in the sidebar to clear the Streamlit cache immediately.

## Storage backend

`Config.validate()` runs before every read and write in `src/utils.py` and raises
`ValueError` when:

| Condition | Message |
|-----------|---------|
| `DATA_BACKEND` is neither `local` nor `s3` | `DATA_BACKEND must be either 'local' or 's3'` |
| `DATA_BACKEND=s3` with an empty `S3_BUCKET` | `S3_BUCKET is required when DATA_BACKEND=s3` |

### `local` (default)

CSVs are read from and written to `data/raw/` and `data/processed/` under the repository
root. No credentials are needed.

### `s3`

The same layout is kept as object keys, so local and remote data are interchangeable:

```text
s3://<S3_BUCKET>/<S3_PREFIX>/raw/AAPL.csv
s3://<S3_BUCKET>/<S3_PREFIX>/processed/AAPL.csv
```

Credentials come from the default boto3 chain — environment variables, a shared profile,
or an instance role. The deployed stack uses an instance role granted `s3:GetObject` and
`s3:ListBucket` only, so the dashboard reads but never writes.

To run locally against a bucket you can already reach:

```bash
DATA_BACKEND=s3 S3_BUCKET=your-data-bucket S3_PREFIX=market-data \
  streamlit run src/dashboard.py
```

Writing to the bucket (`python main.py` with `DATA_BACKEND=s3`) additionally requires
`s3:PutObject`. In CI, that write is done by the `data-update` workflow rather than by the
application — see [CI and quality gate](ci-cd.md).

## Paths (not env-driven)

| Attribute | Location |
|-----------|----------|
| `Config.BASE_DIR` | Repository root |
| `Config.DATA_DIR` | `data/raw/` |
| `Config.PROCESSED_DIR` | `data/processed/` |

These paths apply to `DATA_BACKEND=local`. With `s3`, the equivalent keys come from
`Config.s3_folder()` and `Config.s3_key()` — see the `Config` section of the
[Python API reference](python-api.md).

CSV filenames are `{symbol}.csv` (crypto uses the CoinGecko ID as the stem). Symbols that contain characters unsafe for filenames (for example `^` in `^GSPC`) are used as-is in the filename.

## Example `.env`

```env
DATA_BACKEND=local
S3_BUCKET=
S3_PREFIX=market-data
COINGECKO_API_URL=https://api.coingecko.com/api/v3
DEFAULT_STOCKS=PETR4.SA,VALE3.SA,AAPL,MSFT
DEFAULT_INDEXES=^BVSP,^GSPC,^IXIC,^DJI
DEFAULT_CRYPTO=bitcoin,ethereum,solana
CACHE_EXPIRY_HOURS=1
LOG_LEVEL=INFO
```

This matches `.env.example`. Keep the two in sync when you add a variable.

## Related

- [CI and quality gate](ci-cd.md) — variables consumed by workflows
- [Deploy to AWS](../how-to/deploy-to-aws.md) — where the S3 backend is used
- [Add assets](../how-to/add-assets.md)
- [Python API](python-api.md) — `Config` usage from code
