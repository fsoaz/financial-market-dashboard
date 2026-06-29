"""
Main entry point for the Financial Market Dashboard application.

This module provides the update_market_data function for automated
data retrieval and serves as the application launcher.
"""

import logging
from typing import Optional

from src.api import (
    DataFetchError,
    fetch_all_market_data,
    fetch_stock_data,
    fetch_crypto_data,
)
from src.config import Config
from src.indicators import add_financial_indicators
from src.utils import (
    setup_logging,
    clean_data,
    save_to_csv,
    load_all_data,
)


def update_market_data(
    stocks: Optional[list[str]] = None,
    indexes: Optional[list[str]] = None,
    cryptos: Optional[list[str]] = None,
    save_processed: bool = True,
) -> dict[str, str]:
    """
    Download new market data, update local CSV files, recalculate indicators,
    and refresh cached datasets.

    This function is designed to be scheduled for automated execution.

    Args:
        stocks: List of stock symbols to fetch (default: Config.DEFAULT_STOCKS).
        indexes: List of index symbols to fetch (default: Config.DEFAULT_INDEXES).
        cryptos: List of crypto IDs to fetch (default: Config.DEFAULT_CRYPTO).
        save_processed: If True, also save processed data with indicators.

    Returns:
        Dictionary mapping symbol to status ('success' or 'failed').
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting market data update...")

    results: dict[str, str] = {}

    # Fetch all market data
    try:
        all_data = fetch_all_market_data(
            stocks=stocks,
            indexes=indexes,
            cryptos=cryptos,
        )
    except Exception as e:
        logger.error(f"Failed to fetch market data: {e}")
        return results

    # Process and save each asset's data
    for symbol, df in all_data.items():
        try:
            # Clean the data
            df_clean = clean_data(df)

            if df_clean.empty:
                logger.warning(f"No valid data for {symbol}, skipping")
                results[symbol] = "failed"
                continue

            # Save raw data
            save_to_csv(df_clean, symbol, processed=False)
            logger.info(f"Saved raw data for {symbol}")

            # Add financial indicators and save processed data
            if save_processed:
                df_processed = add_financial_indicators(df_clean)
                save_to_csv(df_processed, symbol, processed=True)
                logger.info(f"Saved processed data for {symbol}")

            results[symbol] = "success"

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            results[symbol] = "failed"

    # Summary
    success_count = sum(1 for status in results.values() if status == "success")
    total_count = len(results)

    logger.info(f"Update complete: {success_count}/{total_count} assets processed successfully")

    return results


def main() -> None:
    """
    Main function to run the data update process.
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("Financial Market Dashboard - Data Update")
    logger.info("=" * 50)

    # Run update
    results = update_market_data()

    # Print summary
    print("\n" + "=" * 50)
    print("UPDATE SUMMARY")
    print("=" * 50)

    for symbol, status in results.items():
        icon = "✅" if status == "success" else "❌"
        print(f"{icon} {symbol}: {status}")

    print("=" * 50)
    print(f"Total: {len(results)} assets")
    print(f"Success: {sum(1 for s in results.values() if s == 'success')}")
    print(f"Failed: {sum(1 for s in results.values() if s == 'failed')}")
    print("=" * 50)


if __name__ == "__main__":
    main()
