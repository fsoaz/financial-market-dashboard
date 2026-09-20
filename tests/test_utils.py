"""
Unit tests for utility functions.
"""

import pandas as pd
import pytest

from src.utils import (
    calculate_correlation_matrix,
    clean_data,
    convert_dates,
    filter_by_date_range,
    format_currency,
    format_percentage,
    load_all_data,
    normalize_prices,
    standardize_columns,
)


class TestCleanData:
    """Tests for data cleaning function."""

    def test_remove_all_nan_rows(self):
        """Test removal of rows with all NaN values."""
        df = pd.DataFrame(
            {
                "a": [1, None, 3],
                "b": [4, None, 6],
            }
        )
        result = clean_data(df)
        assert len(result) == 2  # Row with all NaN should be removed

    def test_handle_missing_values(self):
        """Test handling of missing values."""
        df = pd.DataFrame(
            {
                "a": [1, None, 3],
                "b": [4, 5, None],
            }
        )
        result = clean_data(df)
        assert not result.isna().any().any()  # No NaN values should remain

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = clean_data(df)
        assert result.empty

    def test_deduplicate_date_and_symbol_keeping_latest_observation(self):
        """Duplicate date/symbol pairs should keep the last observation."""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
                "symbol": ["AAPL", "AAPL", "AAPL"],
                "close": [100.0, 101.0, 105.0],
            }
        )

        result = clean_data(df)

        assert len(result) == 2
        assert result.iloc[0]["close"] == pytest.approx(101.0)


class TestConvertDates:
    """Tests for date conversion function."""

    def test_convert_date_column(self):
        """Test date column conversion."""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02"],
                "value": [1, 2],
            }
        )
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
        df = pd.DataFrame(
            {
                "ColumnName": [1, 2],
                "Another Column": [3, 4],
            }
        )
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

    def test_preserves_history_after_normalization(self):
        """Normalization should keep the original ordering and relative trend."""
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "close": [100.0, 110.0, 121.0],
            }
        )

        result = normalize_prices(df)

        assert list(result.index) == list(df.index)
        assert result.iloc[0] == pytest.approx(100.0)
        assert result.iloc[1] == pytest.approx(110.0)
        assert result.iloc[2] == pytest.approx(121.0)


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
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=60, freq="D"),
                "value": range(60),
            }
        )
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
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=30, freq="D"),
                "value": range(30),
            }
        )
        result = filter_by_date_range(df, "Max")
        assert len(result) == 30

    def test_year_to_date_tz_aware(self):
        """Regression (bug 3): YTD on a tz-aware date column must not raise.

        Previously pd.Timestamp(year=...) was tz-naive, so comparing it against a
        tz-aware column threw 'Invalid comparison between dtype=...UTC and Timestamp'.
        """
        dates = pd.to_datetime(["2025-11-01", "2025-12-31", "2026-02-01", "2026-06-01"], utc=True)
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
        df = pd.DataFrame(
            {
                "date": ["2024-01-15 00:00:00-05:00", "2024-07-15 00:00:00-04:00"],
                "close": [100, 110],
            }
        )

        result = convert_dates(df)

        assert pd.api.types.is_datetime64_any_dtype(result["date"])
        assert str(result["date"].dt.tz) == "UTC"
        assert len(result) == 2


class TestLoadAllData:
    """Tests for loading the available asset files."""

    def test_returns_assets_in_deterministic_order(self, tmp_path, monkeypatch):
        """Asset order should not depend on filesystem directory-entry order."""
        from src.config import Config

        for symbol in ["bitcoin", "AAPL", "^BVSP"]:
            pd.DataFrame({"date": ["2024-01-01"], "close": [100]}).to_csv(
                tmp_path / f"{symbol}.csv", index=False
            )

        monkeypatch.setattr(Config, "PROCESSED_DIR", tmp_path)

        result = load_all_data(processed=True)

        assert list(result) == ["^BVSP", "AAPL", "bitcoin"]

    @staticmethod
    def _fake_boto3(pages, seen_paginate=None):
        """Build a minimal boto3 stand-in whose paginator yields the given pages."""

        class Body:
            def __init__(self, key):
                self.key = key

            def read(self):
                symbol = self.key.rsplit("/", 1)[-1][:-4]
                return f"date,symbol,close\n2024-01-01,{symbol},100\n".encode()

        class Paginator:
            def paginate(self, **kwargs):
                if seen_paginate is not None:
                    seen_paginate.append(kwargs)
                return iter(pages)

        class S3:
            def get_paginator(self, operation):
                assert operation == "list_objects_v2"
                return Paginator()

            def get_object(self, **kwargs):
                return {"Body": Body(kwargs["Key"])}

        class Boto3:
            @staticmethod
            def client(name):
                assert name == "s3"
                return S3()

        return Boto3

    @staticmethod
    def _use_s3_backend(monkeypatch, boto3_stub):
        from src.config import Config

        monkeypatch.setitem(__import__("sys").modules, "boto3", boto3_stub)
        monkeypatch.setattr(Config, "DATA_BACKEND", "s3")
        monkeypatch.setattr(Config, "S3_BUCKET", "test-bucket")
        monkeypatch.setattr(Config, "S3_PREFIX", "market-data")

    def test_loads_csv_from_s3_backend(self, monkeypatch):
        seen = []
        pages = [{"Contents": [{"Key": "market-data/processed/AAPL.csv"}]}]
        self._use_s3_backend(monkeypatch, self._fake_boto3(pages, seen))

        result = load_all_data(processed=True)

        assert list(result) == ["AAPL"]
        assert result["AAPL"]["close"].tolist() == [100]
        # The prefix must be the folder, not a key ending in ".csv", or the
        # listing matches nothing and every asset silently disappears.
        assert seen == [{"Bucket": "test-bucket", "Prefix": "market-data/processed/"}]

    def test_reads_every_page_of_a_truncated_listing(self, monkeypatch):
        """Assets past the first 1000-key page must not be dropped."""
        pages = [
            {"Contents": [{"Key": "market-data/processed/MSFT.csv"}]},
            {"Contents": [{"Key": "market-data/processed/bitcoin.csv"}]},
            {"Contents": [{"Key": "market-data/processed/AAPL.csv"}]},
        ]
        self._use_s3_backend(monkeypatch, self._fake_boto3(pages))

        result = load_all_data(processed=True)

        # Sorted across page boundaries, not merely within each page.
        assert list(result) == ["AAPL", "bitcoin", "MSFT"]

    def test_ignores_non_csv_and_empty_pages(self, monkeypatch):
        """A page with no Contents key, and non-CSV objects, are both skipped."""
        pages = [
            {},
            {"Contents": [{"Key": "market-data/processed/README.txt"}]},
            {"Contents": [{"Key": "market-data/processed/AAPL.csv"}]},
        ]
        self._use_s3_backend(monkeypatch, self._fake_boto3(pages))

        assert list(load_all_data(processed=True)) == ["AAPL"]


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
        a = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    ["2024-01-06", "2024-01-07", "2024-01-08", "2024-01-09", "2024-01-10"]
                ),
                "close": [14, 13, 15, 14, 16],
            }
        )
        b = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    [
                        "2024-01-01",
                        "2024-01-02",
                        "2024-01-03",
                        "2024-01-04",
                        "2024-01-05",
                        "2024-01-06",
                        "2024-01-07",
                        "2024-01-08",
                        "2024-01-09",
                        "2024-01-10",
                    ]
                ),
                "close": [1, 2, 3, 4, 5, 14, 13, 15, 14, 16],
            }
        )

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
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=4, freq="D"),
                "close": [100, None, 120, 130],
            }
        )

        result = normalize_prices(df)

        assert result.isna().sum() == 0
        assert set(result.index).issubset(set(df.index))
        assert len(df.loc[result.index, "date"]) == len(result)
