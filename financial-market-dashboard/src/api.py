"""
API module for retrieving financial market data.

This module handles all API communications with external data sources:
- yfinance for stocks and market indexes
- CoinGecko API for cryptocurrencies
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

from src.config import Config

logger = logging.getLogger(__name__)


class DataFetchError(Exception):
    """Custom exception for data fetching errors."""

    pass


def fetch_stock_data(symbol: str, period: str = "2y") -> pd.DataFrame:
    """
    Fetch historical stock or index data using yfinance.

    Args:
        symbol: The stock/index ticker symbol (e.g., 'AAPL', '^GSPC').
        period: Time period for historical data (default: '2y').

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume, Adj Close.

    Raises:
        DataFetchError: If data cannot be retrieved.
    """
    try:
        logger.info(f"Fetching stock data for {symbol}")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

        if df.empty:
            raise DataFetchError(f"No data returned for symbol: {symbol}")

        # Reset index to make Date a column
        df = df.reset_index()

        # Standardize column names - handle different yfinance versions
        df.columns = df.columns.str.strip().str.lower()
        
        # Rename columns to standard names
        rename_map = {}
        for col in df.columns:
            if 'adj' in col and 'close' in col:
                rename_map[col] = 'adj_close'
            elif col == 'date':
                rename_map[col] = 'date'
        
        df = df.rename(columns=rename_map)
        
        # Ensure adj_close exists, use close if not available
        if 'adj_close' not in df.columns and 'close' in df.columns:
            df['adj_close'] = df['close']

        # Ensure date column is datetime
        if 'date' in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        # Add symbol column
        df["symbol"] = symbol
        df["asset_type"] = "indexes" if symbol.startswith("^") else "stocks"

        # Select and order columns
        required_cols = ["date", "symbol", "asset_type", "open", "high", "low", "close", "volume"]
        available_cols = [c for c in required_cols if c in df.columns]
        if 'adj_close' in df.columns:
            available_cols.append('adj_close')

        logger.info(f"Successfully fetched {len(df)} records for {symbol}")
        return df[available_cols]

    except Exception as e:
        logger.error(f"Error fetching stock data for {symbol}: {str(e)}")
        raise DataFetchError(f"Failed to fetch data for {symbol}: {str(e)}")


def fetch_crypto_data(coin_id: str, days: int = 365) -> pd.DataFrame:
    """
    Fetch historical cryptocurrency data from CoinGecko API.

    Args:
        coin_id: CoinGecko coin ID (e.g., 'bitcoin', 'ethereum').
        days: Number of days of historical data (default: 365 = ~1 year).

    Returns:
        DataFrame with columns: Date, Close, Volume.

    Raises:
        DataFetchError: If data cannot be retrieved.
    """
    try:
        logger.info(f"Fetching crypto data for {coin_id}")
        # Use market_chart endpoint instead of ohlc for better reliability
        url = f"{Config.COINGECKO_API_URL}/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": days}

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not data or "prices" not in data:
            raise DataFetchError(f"No data returned for cryptocurrency: {coin_id}")

        # Convert prices to DataFrame
        prices_data = data.get("prices", [])
        if not prices_data:
            raise DataFetchError(f"No price data for {coin_id}")

        df = pd.DataFrame(prices_data, columns=["timestamp", "close"])

        # Convert timestamp to datetime (milliseconds to seconds)
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["symbol"] = coin_id
        df["asset_type"] = "crypto"
        df["open"] = df["close"]  # Approximate
        df["high"] = df["close"]  # Will be updated if OHLC available
        df["low"] = df["close"]   # Will be updated if OHLC available
        df["volume"] = 0  # Not available in this endpoint

        logger.info(f"Successfully fetched {len(df)} records for {coin_id}")
        return df[["date", "symbol", "asset_type", "open", "high", "low", "close", "volume"]]

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching crypto data for {coin_id}: {str(e)}")
        raise DataFetchError(f"Failed to fetch crypto data for {coin_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching crypto data for {coin_id}: {str(e)}")
        raise DataFetchError(f"Failed to fetch data for {coin_id}: {str(e)}")


def fetch_all_market_data(
    stocks: Optional[list[str]] = None,
    indexes: Optional[list[str]] = None,
    cryptos: Optional[list[str]] = None,
) -> dict[str, pd.DataFrame]:
    """
    Fetch market data for multiple assets across different types.

    Args:
        stocks: List of stock symbols (default: Config.DEFAULT_STOCKS).
        indexes: List of index symbols (default: Config.DEFAULT_INDEXES).
        cryptos: List of crypto IDs (default: Config.DEFAULT_CRYPTO).

    Returns:
        Dictionary mapping symbol to DataFrame.
    """
    stocks = stocks or Config.DEFAULT_STOCKS
    indexes = indexes or Config.DEFAULT_INDEXES
    cryptos = cryptos or Config.DEFAULT_CRYPTO

    all_data: dict[str, pd.DataFrame] = {}

    # Fetch stocks
    for symbol in stocks:
        try:
            all_data[symbol] = fetch_stock_data(symbol)
        except DataFetchError as e:
            logger.warning(f"Skipping {symbol}: {e}")

    # Fetch indexes
    for symbol in indexes:
        try:
            all_data[symbol] = fetch_stock_data(symbol)
        except DataFetchError as e:
            logger.warning(f"Skipping {symbol}: {e}")

    # Fetch cryptos
    for coin_id in cryptos:
        try:
            all_data[coin_id] = fetch_crypto_data(coin_id)
        except DataFetchError as e:
            logger.warning(f"Skipping {coin_id}: {e}")

    logger.info(f"Successfully fetched data for {len(all_data)} assets")
    return all_data


def validate_response(data: pd.DataFrame, required_columns: list[str]) -> bool:
    """
    Validate that a DataFrame contains required columns.

    Args:
        data: DataFrame to validate.
        required_columns: List of required column names.

    Returns:
        True if validation passes, False otherwise.
    """
    if data.empty:
        return False

    missing_cols = set(required_columns) - set(data.columns)
    if missing_cols:
        logger.warning(f"Missing columns: {missing_cols}")
        return False

    return True


def get_current_price(symbol: str, asset_type: str) -> Optional[float]:
    """
    Get the current/latest price for an asset.

    Args:
        symbol: Asset symbol.
        asset_type: Type of asset ('stocks', 'indexes', 'crypto').

    Returns:
        Current price or None if unavailable.
    """
    try:
        if asset_type == "crypto":
            url = f"{Config.COINGECKO_API_URL}/simple/price"
            params = {"ids": symbol, "vs_currencies": "usd"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get(symbol, {}).get("usd")
        else:
            ticker = yf.Ticker(symbol)
            return ticker.fast_info.get("lastPrice")
    except Exception as e:
        logger.error(f"Error getting current price for {symbol}: {e}")
        return None
