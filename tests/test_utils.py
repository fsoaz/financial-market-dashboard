"""
Unit tests for utility functions.
"""

import pandas as pd

from src.utils import (
    clean_data,
    convert_dates,
    standardize_columns,
    normalize_prices,
    format_currency,
    format_percentage,
    filter_by_date_range,
    calculate_correlation_matrix,
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

    def test_year_to_date_tz_aware(self):
        """Regression (bug 3): YTD on a tz-aware date column must not raise.

        Previously pd.Timestamp(year=...) was tz-naive, so comparing it against a
        tz-aware column threw 'Invalid comparison between dtype=...UTC and Timestamp'.
        """
        dates = pd.to_datetime(
            ["2025-11-01", "2025-12-31", "2026-02-01", "2026-06-01"], utc=True
        )
        df = pd.DataFrame({"date": dates, "close": [1, 2, 3, 4]})

        result = filter_by_date_range(df, "Year to Date")

        assert len(result) == 2  # only 2026 rows
        assert (result["date"].dt.year == 2026).all()


class TestConvertDatesMixedTimezone:
    """Regression tests for the timezone load failure."""

    def test_mixed_dst_offsets_do_not_raise(self):
        """Regression (bug 1): yfinance CSVs cross a DST change, producing mixed
        -05:00/-04:00 offsets. Without utc=True, pd.to_datetime raised
        'Mixed timezones detected' and the asset was silently dropped on load.
        """
        df = pd.DataFrame({
            "date": ["2024-01-15 00:00:00-05:00", "2024-07-15 00:00:00-04:00"],
            "close": [100, 110],
        })

        result = convert_dates(df)

        assert pd.api.types.is_datetime64_any_dtype(result["date"])
        assert str(result["date"].dt.tz) == "UTC"
        assert len(result) == 2


class TestCorrelationMatrix:
    """Regression tests for correlation alignment."""

    def test_aligns_by_date_not_row_position(self):
        """Regression (bug 2): assets with different histories must be correlated
        by DATE, not by RangeIndex row position.

        A and B carry identical prices on their five shared dates but B has five
        extra leading rows, so the shared dates sit at different row positions.
        Date-aligned correlation over the overlap is exactly 1.0; the old
        position-aligned code compared unrelated dates and did not.
        """
        a = pd.DataFrame({
            "date": pd.to_datetime(
                ["2024-01-06", "2024-01-07", "2024-01-08", "2024-01-09", "2024-01-10"]
            ),
            "close": [14, 13, 15, 14, 16],
        })
        b = pd.DataFrame({
            "date": pd.to_datetime([
                "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
                "2024-01-06", "2024-01-07", "2024-01-08", "2024-01-09", "2024-01-10",
            ]),
            "close": [1, 2, 3, 4, 5, 14, 13, 15, 14, 16],
        })

        cm = calculate_correlation_matrix({"A": a, "B": b})

        assert cm.shape == (2, 2)
        assert round(cm.loc["A", "B"], 6) == 1.0

    def test_empty_input_returns_empty(self):
        """No usable assets → empty matrix, no crash."""
        assert calculate_correlation_matrix({}).empty


class TestNormalizePricesAlignment:
    """Guards the index invariant the dashboard relies on."""

    def test_index_is_valid_subset_after_dropping_nan(self):
        """Regression (bug 4): normalize_prices drops NaN rows, so the dashboard
        must align x to the surviving index (df.loc[result.index, 'date']).
        Verify the returned index is a NaN-free subset usable for that lookup.
        """
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=4, freq="D"),
            "close": [100, None, 120, 130],
        })

        result = normalize_prices(df)

        assert result.isna().sum() == 0
        assert set(result.index).issubset(set(df.index))
        assert len(df.loc[result.index, "date"]) == len(result)
