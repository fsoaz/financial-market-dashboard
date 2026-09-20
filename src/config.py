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

    # Data storage.  Local remains the default for development; production uses
    # the private S3 bucket provisioned by Terraform.
    DATA_BACKEND: str = os.getenv("DATA_BACKEND", "local").lower()
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_PREFIX: str = os.getenv("S3_PREFIX", "")

    # API Configuration
    COINGECKO_API_URL: str = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")

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

    @classmethod
    def validate(cls) -> None:
        """Validate settings that are required by the selected backend."""
        if cls.DATA_BACKEND not in {"local", "s3"}:
            raise ValueError("DATA_BACKEND must be either 'local' or 's3'")
        if cls.DATA_BACKEND == "s3" and not cls.S3_BUCKET:
            raise ValueError("S3_BUCKET is required when DATA_BACKEND=s3")

    @classmethod
    def s3_folder(cls, processed: bool = False) -> str:
        """Return the object key prefix for the raw/processed folder, without a trailing slash."""
        folder = "processed" if processed else "raw"
        parts = [part.strip("/") for part in (cls.S3_PREFIX, folder) if part.strip("/")]
        return "/".join(parts)

    @classmethod
    def s3_key(cls, symbol: str, processed: bool = False) -> str:
        """Return the object key while preserving the local raw/processed layout."""
        return f"{cls.s3_folder(processed=processed)}/{symbol}.csv"


# Initialize directories on module import
Config.ensure_directories()
