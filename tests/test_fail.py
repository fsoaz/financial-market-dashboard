"""Intentionally failing regression tests to demonstrate a known gap."""

import pandas as pd

from src.utils import clean_data


class TestCleanDataKnownGap:
    """Expected to fail until duplicate handling is aligned with the desired behavior."""

    def test_duplicate_rows_should_be_preserved_when_they_are_valid_observations(self):
        """This is intentionally failing: current cleaning removes valid duplicate rows."""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
                "symbol": ["AAPL", "AAPL", "AAPL"],
                "close": [100.0, 101.0, 105.0],
            }
        )

        result = clean_data(df)

        assert len(result) == 3
        assert result.iloc[1]["close"] == 101.0
