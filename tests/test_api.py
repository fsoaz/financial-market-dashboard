"""
Unit tests for API data processing.
"""

import pandas as pd
import pytest
import requests

from src import api
from src.api import DataFetchError, validate_response


class TestValidateResponse:
    """Tests for API response validation."""

    def test_valid_response(self):
        """Test validation with all required columns present."""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "close": [100],
                "open": [99],
            }
        )
        result = validate_response(df, ["date", "close"])
        assert result is True

    def test_missing_columns(self):
        """Test validation with missing columns."""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "close": [100],
            }
        )
        result = validate_response(df, ["date", "close", "volume"])
        assert result is False

    def test_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        df = pd.DataFrame()
        result = validate_response(df, ["date", "close"])
        assert result is False

    def test_extra_columns_allowed(self):
        """Test that extra columns don't cause failure."""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "close": [100],
                "extra": [1],
            }
        )
        result = validate_response(df, ["date", "close"])
        assert result is True


def test_fetch_stock_data_standardizes_yfinance_response(monkeypatch):
    history = pd.DataFrame(
        {
            "Open": [99.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [98.0, 100.0],
            "Close": [100.0, 102.0],
            "Volume": [1000, 1200],
            "Adj Close": [100.5, 102.5],
        },
        index=pd.date_range("2026-01-01", periods=2, name="Date"),
    )

    class Ticker:
        def __init__(self, symbol):
            assert symbol == "^GSPC"

        def history(self, period):
            assert period == "1mo"
            return history

    monkeypatch.setattr(api.yf, "Ticker", Ticker)
    result = api.fetch_stock_data("^GSPC", period="1mo")

    assert result["symbol"].tolist() == ["^GSPC", "^GSPC"]
    assert result["asset_type"].tolist() == ["indexes", "indexes"]
    assert result["adj_close"].tolist() == [100.5, 102.5]
    assert pd.api.types.is_datetime64_any_dtype(result["date"])


def test_fetch_stock_data_uses_close_when_adjusted_close_is_missing(monkeypatch):
    history = pd.DataFrame(
        {"Close": [100.0]}, index=pd.date_range("2026-01-01", periods=1, name="Date")
    )

    class Ticker:
        def history(self, period):
            return history

    monkeypatch.setattr(api.yf, "Ticker", lambda symbol: Ticker())

    result = api.fetch_stock_data("AAPL")
    assert result["adj_close"].tolist() == [100.0]
    assert result["asset_type"].tolist() == ["stocks"]


def test_fetch_stock_data_rejects_empty_history(monkeypatch):
    class Ticker:
        def history(self, period):
            return pd.DataFrame()

    monkeypatch.setattr(api.yf, "Ticker", lambda symbol: Ticker())
    with pytest.raises(DataFetchError, match="No data returned for symbol: AAPL"):
        api.fetch_stock_data("AAPL")


def test_fetch_crypto_data_converts_prices(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"prices": [[1_767_225_600_000, 100.0], [1_767_312_000_000, 110.0]]}

    def get(url, params, timeout):
        assert url.endswith("/coins/bitcoin/market_chart")
        assert params == {"vs_currency": "usd", "days": 7}
        assert timeout == 30
        return Response()

    monkeypatch.setattr(api.requests, "get", get)
    result = api.fetch_crypto_data("bitcoin", days=7)

    assert result["close"].tolist() == [100.0, 110.0]
    assert result["open"].tolist() == result["close"].tolist()
    assert result["asset_type"].tolist() == ["crypto", "crypto"]
    assert result["date"].iloc[0] == pd.Timestamp("2026-01-01")


@pytest.mark.parametrize("payload", [{}, {"prices": []}])
def test_fetch_crypto_data_rejects_missing_prices(monkeypatch, payload):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr(api.requests, "get", lambda *args, **kwargs: Response())
    with pytest.raises(DataFetchError, match="No .*data"):
        api.fetch_crypto_data("bitcoin")


def test_fetch_crypto_data_wraps_request_errors(monkeypatch):
    def get(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(api.requests, "get", get)
    with pytest.raises(DataFetchError, match="Failed to fetch crypto data for bitcoin"):
        api.fetch_crypto_data("bitcoin")


def test_fetch_all_market_data_keeps_successful_assets(monkeypatch):
    fetched = []

    def stock(symbol):
        fetched.append(symbol)
        if symbol == "VALE3.SA":
            raise DataFetchError("unavailable")
        return pd.DataFrame({"symbol": [symbol]})

    def crypto(symbol):
        fetched.append(symbol)
        return pd.DataFrame({"symbol": [symbol]})

    monkeypatch.setattr(api, "fetch_stock_data", stock)
    monkeypatch.setattr(api, "fetch_crypto_data", crypto)

    result = api.fetch_all_market_data(
        stocks=["AAPL", "VALE3.SA"], indexes=["^GSPC"], cryptos=["bitcoin"]
    )
    assert list(result) == ["AAPL", "^GSPC", "bitcoin"]
    assert fetched == ["AAPL", "VALE3.SA", "^GSPC", "bitcoin"]
