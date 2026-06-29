"""
Unit tests for utility functions.
"""

import pandas as pd
import pytest

from src.utils import (
    clean_data,
    convert_dates,
    standardize_columns,
    normalize_prices,
    format_currency,
    format_percentage,
    filter_by_date_range,
)


class TestCleanData:
    """Tests for data cleaning function."""

    def test_remove_all_nan_rows(self):
        """Test removal of rows with all NaN values."""
        df = pd.DataFrame({
            "a": [1, None, 3],
            "b": [4, None, 6],
        })
        result = clean_data(df)
        assert len(result) == 2  # Row with all NaN should be removed

    def test_handle_missing_values(self):
        """Test handling of missing values."""
        df = pd.DataFrame({
            "a": [1, None, 3],
            "b": [4, 5, None],
        })
        result = clean_data(df)
        assert not result.isna().any().any()  # No NaN values should remain

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = clean_data(df)
        assert result.empty


class TestConvertDates:
    """Tests for date conversion function."""

    def test_convert_date_column(self):
        """Test date column conversion."""
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02"],
            "value": [1, 2],
        })
        result = convert_dates(df)
        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    def test_missing_date_column(self):
        """Test when date column doesn't exist."""
        df = pd.DataFrame({"value": [1, 2]})
        result = convert_dates(df, date_column="nonexistent")
        assert result.equals(df)

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = convert_dates(df)
        assert result.empty


class TestStandardizeColumns:
    """Tests for column standardization."""

    def test_lowercase_conversion(self):
        """Test conversion to lowercase."""
        df = pd.DataFrame({
            "ColumnName": [1, 2],
            "Another Column": [3, 4],
        })
        result = standardize_columns(df)
        assert list(result.columns) == ["columnname", "another_column"]

    def test_space_replacement(self):
        """Test replacement of spaces with underscores."""
        df = pd.DataFrame({"Column Name": [1, 2]})
        result = standardize_columns(df)
        assert "column_name" in result.columns

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = standardize_columns(df)
        assert result.empty


class TestNormalizePrices:
    """Tests for price normalization."""

    def test_basic_normalization(self):
        """Test basic price normalization."""
        df = pd.DataFrame({"close": [100, 110, 120, 130]})
        result = normalize_prices(df)

        assert result.iloc[0] == 100  # First value should be 100
        assert result.iloc[-1] == 130  # Last value should be 130

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = normalize_prices(df)
        assert result.empty

    def test_zero_first_price(self):
        """Test when first price is zero."""
        df = pd.DataFrame({"close": [0, 100, 200]})
        result = normalize_prices(df)
        assert result.empty


class TestFormatCurrency:
    """Tests for currency formatting."""

    def test_basic_formatting(self):
        """Test basic currency formatting."""
        result = format_currency(1234.56)
        assert "$" in result

    def test_large_numbers(self):
        """Test formatting of large numbers."""
        result = format_currency(1500000)
        assert "M" in result  # Should show millions

    def test_billions(self):
        """Test formatting of billions."""
        result = format_currency(1500000000)
        assert "B" in result  # Should show billions


class TestFormatPercentage:
    """Tests for percentage formatting."""

    def test_positive_value(self):
        """Test positive percentage."""
        result = format_percentage(5.25)
        assert "+" in result
        assert "%" in result

    def test_negative_value(self):
        """Test negative percentage."""
        result = format_percentage(-3.75)
        assert "+" not in result
        assert "-" in result
        assert "%" in result

    def test_zero_value(self):
        """Test zero percentage."""
        result = format_percentage(0)
        assert "%" in result


class TestFilterByDateRange:
    """Tests for date range filtering."""

    def test_filter_one_month(self):
        """Test filtering by 1 month."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=60, freq="D"),
            "value": range(60),
        })
        result = filter_by_date_range(df, "1 Month")
        assert len(result) < 60
        assert len(result) <= 32  # Approximately 1 month

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = filter_by_date_range(df, "1 Month")
        assert result.empty

    def test_max_range(self):
        """Test 'Max' range returns all data."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "value": range(30),
        })
        result = filter_by_date_range(df, "Max")
        assert len(result) == 30
