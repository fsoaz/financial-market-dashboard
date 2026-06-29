"""
Configuration module for the Financial Market Dashboard.

This module handles project configuration, constants, environment variables,
and path management.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Centralized configuration management for the application.

    This class provides access to all configuration settings through
    class attributes and environment variables.
    """

    # Base directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # Data directories
    DATA_DIR: Path = BASE_DIR / "data" / "raw"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"

    # API Configuration
    COINGECKO_API_URL: str = os.getenv(
        "COINGECKO_API_URL", "https://api.coingecko.com/api/v3"
    )

    # Default Assets
    DEFAULT_STOCKS: list[str] = [
        s.strip() for s in os.getenv("DEFAULT_STOCKS", "PETR4.SA,VALE3.SA,AAPL,MSFT").split(",")
    ]
    DEFAULT_INDEXES: list[str] = [
        s.strip() for s in os.getenv("DEFAULT_INDEXES", "^BVSP,^GSPC,^IXIC,^DJI").split(",")
    ]
    DEFAULT_CRYPTO: list[str] = [
        s.strip() for s in os.getenv("DEFAULT_CRYPTO", "bitcoin,ethereum,solana").split(",")
    ]

    # Cache settings
    CACHE_EXPIRY_HOURS: int = int(os.getenv("CACHE_EXPIRY_HOURS", "1"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_csv_path(cls, symbol: str, processed: bool = False) -> Path:
        """
        Get the CSV file path for a given symbol.

        Args:
            symbol: The asset symbol.
            processed: If True, return path in processed directory.

        Returns:
            Path object pointing to the CSV file location.
        """
        base_dir = cls.PROCESSED_DIR if processed else cls.DATA_DIR
        return base_dir / f"{symbol}.csv"


# Initialize directories on module import
Config.ensure_directories()
