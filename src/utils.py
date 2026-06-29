"""
Utility functions for the Financial Market Dashboard.

This module provides helper functions for data processing, caching,
file I/O, and other common operations.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (default: from Config.LOG_LEVEL).
    """
    log_level = level or Config.LOG_LEVEL
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and preprocess a DataFrame.

    Args:
        df: Raw DataFrame.

    Returns:
        Cleaned DataFrame with missing values handled.
    """
    if df.empty:
        return df

    df = df.copy()

    # Remove rows with all NaN values
    df = df.dropna(how="all")

    # Forward fill then backward fill for remaining NaNs
    df = df.ffill().bfill()

    # Remove duplicates based on date and symbol
    if "date" in df.columns and "symbol" in df.columns:
        df = df.drop_duplicates(subset=["date", "symbol"], keep="last")

    # Sort by date
    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)

    return df


def convert_dates(df: pd.DataFrame, date_column: str = "date") -> pd.DataFrame:
    """
    Convert date column to datetime format.

    Args:
        df: DataFrame with date column.
        date_column: Name of the date column.

    Returns:
        DataFrame with datetime column.
    """
    if df.empty or date_column not in df.columns:
        return df

    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    return df


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names to lowercase with underscores.

    Args:
        df: DataFrame to standardize.

    Returns:
        DataFrame with standardized column names.
    """
    if df.empty:
        return df

    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
    return df


def save_to_csv(df: pd.DataFrame, symbol: str, processed: bool = False) -> Path:
    """
    Save DataFrame to CSV file.

    Args:
        df: DataFrame to save.
        symbol: Asset symbol (used in filename).
        processed: If True, save to processed directory.

    Returns:
        Path to saved file.
    """
    filepath = Config.get_csv_path(symbol, processed=processed)
    df.to_csv(filepath, index=False)
    logger.info(f"Saved data to {filepath}")
    return filepath


def load_from_csv(symbol: str, processed: bool = False) -> Optional[pd.DataFrame]:
    """
    Load DataFrame from CSV file.

    Args:
        symbol: Asset symbol.
        processed: If True, load from processed directory.

    Returns:
        DataFrame or None if file doesn't exist.
    """
    filepath = Config.get_csv_path(symbol, processed=processed)

    if not filepath.exists():
        logger.debug(f"File not found: {filepath}")
        return None

    try:
        df = pd.read_csv(filepath)
        df = convert_dates(df)
        logger.info(f"Loaded data from {filepath}")
        return df
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None


def load_all_data(processed: bool = False) -> dict[str, pd.DataFrame]:
    """
    Load all available CSV files for assets.

    Args:
        processed: If True, load from processed directory.

    Returns:
        Dictionary mapping symbol to DataFrame.
    """
    directory = Config.PROCESSED_DIR if processed else Config.DATA_DIR
    data: dict[str, pd.DataFrame] = {}

    if not directory.exists():
        return data

    for filepath in directory.glob("*.csv"):
        symbol = filepath.stem
        df = load_from_csv(symbol, processed=processed)
        if df is not None:
            data[symbol] = df

    return data


def is_cache_valid(filepath: Path, expiry_hours: int) -> bool:
    """
    Check if cached file is still valid.

    Args:
        filepath: Path to cached file.
        expiry_hours: Cache expiry time in hours.

    Returns:
        True if cache is valid, False otherwise.
    """
    if not filepath.exists():
        return False

    file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
    age = datetime.now() - file_time

    return age.total_seconds() < expiry_hours * 3600


def get_cached_or_fetch(
    symbol: str,
    fetch_func,
    expiry_hours: Optional[int] = None,
    **kwargs,
) -> pd.DataFrame:
    """
    Get data from cache or fetch fresh if expired.

    Args:
        symbol: Asset symbol.
        fetch_func: Function to call if cache is invalid.
        expiry_hours: Cache expiry time (default: Config.CACHE_EXPIRY_HOURS).
        **kwargs: Arguments to pass to fetch_func.

    Returns:
        DataFrame with asset data.
    """
    expiry = expiry_hours or Config.CACHE_EXPIRY_HOURS
    filepath = Config.get_csv_path(symbol)

    if is_cache_valid(filepath, expiry):
        logger.info(f"Using cached data for {symbol}")
        df = load_from_csv(symbol)
        if df is not None:
            return df

    logger.info(f"Fetching fresh data for {symbol}")
    df = fetch_func(symbol, **kwargs)
    save_to_csv(df, symbol)

    return df


def normalize_prices(df: pd.DataFrame, price_column: str = "close") -> pd.Series:
    """
    Normalize prices to start at 100 for comparison.

    Args:
        df: DataFrame with price data.
        price_column: Name of the price column.

    Returns:
        Series of normalized prices.
    """
    if df.empty or price_column not in df.columns:
        return pd.Series(dtype=float)

    prices = df[price_column].dropna()
    if prices.empty or prices.iloc[0] == 0:
        return pd.Series(dtype=float)

    return (prices / prices.iloc[0]) * 100


def calculate_correlation_matrix(
    data: dict[str, pd.DataFrame], price_column: str = "close"
) -> pd.DataFrame:
    """
    Calculate correlation matrix for multiple assets.

    Args:
        data: Dictionary mapping symbol to DataFrame.
        price_column: Name of the price column.

    Returns:
        Correlation matrix DataFrame.
    """
    returns_dict = {}

    for symbol, df in data.items():
        if df.empty or price_column not in df.columns:
            continue

        # Calculate daily returns
        returns = df[price_column].pct_change()
        returns_dict[symbol] = returns

    if not returns_dict:
        return pd.DataFrame()

    # Create DataFrame with all returns
    returns_df = pd.DataFrame(returns_dict)

    # Drop NaN rows (align dates)
    returns_df = returns_df.dropna()

    return returns_df.corr()


def format_currency(value: float, currency: str = "USD") -> str:
    """
    Format a number as currency.

    Args:
        value: Numeric value.
        currency: Currency symbol.

    Returns:
        Formatted currency string.
    """
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "BRL": "R$"}
    symbol = symbols.get(currency, "$")

    if abs(value) >= 1e9:
        return f"{symbol}{value/1e9:.2f}B"
    elif abs(value) >= 1e6:
        return f"{symbol}{value/1e6:.2f}M"
    elif abs(value) >= 1e3:
        return f"{symbol}{value/1e3:.2f}K"
    else:
        return f"{symbol}{value:.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a number as percentage.

    Args:
        value: Numeric value.
        decimals: Number of decimal places.

    Returns:
        Formatted percentage string.
    """
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def get_date_range_options() -> list[str]:
    """
    Get predefined date range options for filtering.

    Returns:
        List of date range option strings.
    """
    return [
        "1 Month",
        "3 Months",
        "6 Months",
        "Year to Date",
        "1 Year",
        "2 Years",
        "5 Years",
        "Max",
    ]


def filter_by_date_range(
    df: pd.DataFrame, date_range: str, date_column: str = "date"
) -> pd.DataFrame:
    """
    Filter DataFrame by predefined date range.

    Args:
        df: DataFrame with date column.
        date_range: Date range option string.
        date_column: Name of the date column.

    Returns:
        Filtered DataFrame.
    """
    if df.empty or date_column not in df.columns:
        return df

    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])

    max_date = df[date_column].max()

    if date_range == "1 Month":
        min_date = max_date - pd.DateOffset(months=1)
    elif date_range == "3 Months":
        min_date = max_date - pd.DateOffset(months=3)
    elif date_range == "6 Months":
        min_date = max_date - pd.DateOffset(months=6)
    elif date_range == "Year to Date":
        min_date = pd.Timestamp(year=max_date.year, month=1, day=1)
    elif date_range == "1 Year":
        min_date = max_date - pd.DateOffset(years=1)
    elif date_range == "2 Years":
        min_date = max_date - pd.DateOffset(years=2)
    elif date_range == "5 Years":
        min_date = max_date - pd.DateOffset(years=5)
    else:  # "Max"
        return df

    return df[df[date_column] >= min_date]
