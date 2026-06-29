"""
Unit tests for API data processing.
"""

import pandas as pd

from src.api import validate_response


class TestValidateResponse:
    """Tests for API response validation."""

    def test_valid_response(self):
        """Test validation with all required columns present."""
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "close": [100],
            "open": [99],
        })
        result = validate_response(df, ["date", "close"])
        assert result is True

    def test_missing_columns(self):
        """Test validation with missing columns."""
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "close": [100],
        })
        result = validate_response(df, ["date", "close", "volume"])
        assert result is False

    def test_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        df = pd.DataFrame()
        result = validate_response(df, ["date", "close"])
        assert result is False

    def test_extra_columns_allowed(self):
        """Test that extra columns don't cause failure."""
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "close": [100],
            "extra": [1],
        })
        result = validate_response(df, ["date", "close"])
        assert result is True
