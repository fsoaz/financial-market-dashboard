"""
Financial indicators calculation module.

This module provides functions for calculating various financial metrics:
- Daily and cumulative returns
- Volatility (daily and annualized)
- Drawdown analysis
- Moving averages and technical indicators (optional features)
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_daily_return(prices: pd.Series) -> pd.Series:
    """
    Calculate percentage daily returns from a price series.

    Args:
        prices: Series of closing prices.

    Returns:
        Series of daily percentage returns.
    """
    return prices.pct_change() * 100


def calculate_cumulative_return(prices: pd.Series) -> pd.Series:
    """
    Calculate cumulative return over time.

    Args:
        prices: Series of closing prices.

    Returns:
        Series of cumulative returns as percentages.
    """
    if prices.empty:
        return pd.Series(dtype=float)

    first_price = prices.iloc[0]
    if first_price == 0:
        return pd.Series(0, index=prices.index)

    return ((prices - first_price) / first_price) * 100


def calculate_volatility(returns: pd.Series, annualize: bool = True) -> float:
    """
    Calculate volatility (standard deviation of returns).

    Args:
        returns: Series of returns.
        annualize: If True, annualize the volatility (default: True).

    Returns:
        Volatility as a percentage.
    """
    if returns.empty or returns.isna().all():
        return 0.0

    daily_vol = returns.std()

    if annualize:
        # Annualize assuming 252 trading days per year
        return daily_vol * np.sqrt(252)

    return daily_vol


def calculate_drawdown(prices: pd.Series) -> pd.Series:
    """
    Calculate running drawdown from peak.

    Args:
        prices: Series of closing prices.

    Returns:
        Series of drawdown percentages.
    """
    if prices.empty:
        return pd.Series(dtype=float)

    # Calculate running maximum
    running_max = prices.cummax()

    # Calculate drawdown
    drawdown = ((prices - running_max) / running_max) * 100

    return drawdown


def calculate_max_drawdown(prices: pd.Series) -> float:
    """
    Calculate maximum drawdown.

    Args:
        prices: Series of closing prices.

    Returns:
        Maximum drawdown as a percentage (negative value).
    """
    drawdown = calculate_drawdown(prices)
    return drawdown.min() if not drawdown.empty else 0.0


def add_financial_indicators(df: pd.DataFrame, price_column: str = "close") -> pd.DataFrame:
    """
    Add all basic financial indicators to a DataFrame.

    Args:
        df: DataFrame with price data.
        price_column: Name of the price column to use.

    Returns:
        DataFrame with added indicator columns.
    """
    df = df.copy()

    if price_column not in df.columns:
        logger.warning(f"Price column '{price_column}' not found")
        return df

    prices = df[price_column]

    # Basic indicators
    df["daily_return"] = calculate_daily_return(prices)
    df["cumulative_return"] = calculate_cumulative_return(prices)
    df["drawdown"] = calculate_drawdown(prices)

    return df


def calculate_summary_statistics(df: pd.DataFrame, price_column: str = "close") -> dict:
    """
    Calculate summary statistics for an asset.

    Args:
        df: DataFrame with price data.
        price_column: Name of the price column.

    Returns:
        Dictionary containing key metrics.
    """
    if df.empty or price_column not in df.columns:
        return {}

    prices = df[price_column].dropna()

    if len(prices) < 2:
        return {}

    daily_returns = calculate_daily_return(prices)

    # Dates live in the 'date' column (rows use a RangeIndex after load/clean).
    # Align to the rows that survived dropna(); fall back to the index only when
    # there is no 'date' column (e.g. a datetime-indexed Series).
    if "date" in df.columns:
        dates = pd.to_datetime(df.loc[prices.index, "date"])
        start_date = str(dates.iloc[0].date())
        end_date = str(dates.iloc[-1].date())
    else:
        start_date = str(prices.index[0].date()) if hasattr(prices.index[0], "date") else str(prices.index[0])
        end_date = str(prices.index[-1].date()) if hasattr(prices.index[-1], "date") else str(prices.index[-1])

    return {
        "current_price": float(prices.iloc[-1]),
        "daily_return": float(daily_returns.iloc[-1]) if not daily_returns.empty else 0.0,
        "cumulative_return": float(calculate_cumulative_return(prices).iloc[-1]),
        "volatility_daily": float(calculate_volatility(daily_returns, annualize=False)),
        "volatility_annual": float(calculate_volatility(daily_returns, annualize=True)),
        "max_drawdown": float(calculate_max_drawdown(prices)),
        "start_date": start_date,
        "end_date": end_date,
    }


# === Optional Technical Indicators ===


def calculate_sma(prices: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate Simple Moving Average.

    Args:
        prices: Series of prices.
        window: Window size for SMA.

    Returns:
        Series of SMA values.
    """
    return prices.rolling(window=window).mean()


def calculate_ema(prices: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Args:
        prices: Series of prices.
        window: Window size for EMA.

    Returns:
        Series of EMA values.
    """
    return prices.ewm(span=window, adjust=False).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        prices: Series of prices.
        period: RSI period (default: 14).

    Returns:
        Series of RSI values (0-100).
    """
    delta = prices.diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # No losses in the window → RSI is 100 by definition. Guard explicitly so the
    # avg_loss == 0 case yields 100 (the old `replace(0, inf)` made rs=0 → RSI=0).
    rsi[avg_loss == 0] = 100.0

    return rsi


def calculate_macd(
    prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        prices: Series of prices.
        fast: Fast EMA period (default: 12).
        slow: Slow EMA period (default: 26).
        signal: Signal line period (default: 9).

    Returns:
        Tuple of (MACD line, Signal line, Histogram).
    """
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)

    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    prices: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.

    Args:
        prices: Series of prices.
        window: Rolling window size (default: 20).
        num_std: Number of standard deviations (default: 2).

    Returns:
        Tuple of (Upper band, Middle band/SMA, Lower band).
    """
    middle = calculate_sma(prices, window)
    std = prices.rolling(window=window).std()

    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    return upper, middle, lower


def add_technical_indicators(df: pd.DataFrame, price_column: str = "close") -> pd.DataFrame:
    """
    Add optional technical indicators to a DataFrame.

    Args:
        df: DataFrame with price data.
        price_column: Name of the price column.

    Returns:
        DataFrame with added technical indicator columns.
    """
    df = df.copy()

    if price_column not in df.columns:
        logger.warning(f"Price column '{price_column}' not found")
        return df

    prices = df[price_column]

    # Moving Averages
    df["sma_20"] = calculate_sma(prices, 20)
    df["sma_50"] = calculate_sma(prices, 50)
    df["ema_20"] = calculate_ema(prices, 20)

    # RSI
    df["rsi"] = calculate_rsi(prices)

    # MACD
    macd, signal, hist = calculate_macd(prices)
    df["macd"] = macd
    df["macd_signal"] = signal
    df["macd_histogram"] = hist

    # Bollinger Bands
    upper, middle, lower = calculate_bollinger_bands(prices)
    df["bb_upper"] = upper
    df["bb_middle"] = middle
    df["bb_lower"] = lower

    return df
