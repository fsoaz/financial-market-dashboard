"""
Unit tests for financial indicators calculations.
"""

import numpy as np
import pandas as pd
import pytest

from src.indicators import (
    calculate_daily_return,
    calculate_cumulative_return,
    calculate_volatility,
    calculate_drawdown,
    calculate_max_drawdown,
    calculate_summary_statistics,
    calculate_sma,
    calculate_ema,
    calculate_rsi,
)


class TestDailyReturn:
    """Tests for daily return calculation."""

    def test_basic_daily_return(self):
        """Test basic daily return calculation."""
        prices = pd.Series([100, 102, 98, 105])
        expected = pd.Series([np.nan, 2.0, -3.92156862745098, 7.142857142857143])
        result = calculate_daily_return(prices)

        assert result.isna().sum() == 1  # First value should be NaN
        assert round(result.iloc[1], 2) == 2.0
        assert round(result.iloc[2], 2) == -3.92

    def test_empty_series(self):
        """Test with empty series."""
        prices = pd.Series([], dtype=float)
        result = calculate_daily_return(prices)
        assert result.empty

    def test_constant_prices(self):
        """Test with constant prices (zero returns)."""
        prices = pd.Series([100, 100, 100, 100])
        result = calculate_daily_return(prices)
        assert all(result.dropna() == 0)


class TestCumulativeReturn:
    """Tests for cumulative return calculation."""

    def test_basic_cumulative_return(self):
        """Test basic cumulative return calculation."""
        prices = pd.Series([100, 110, 120, 130])
        result = calculate_cumulative_return(prices)

        assert result.iloc[0] == 0  # First value should be 0
        assert result.iloc[-1] == 30  # Last value should be 30%

    def test_empty_series(self):
        """Test with empty series."""
        prices = pd.Series([], dtype=float)
        result = calculate_cumulative_return(prices)
        assert result.empty

    def test_price_decrease(self):
        """Test with decreasing prices."""
        prices = pd.Series([100, 90, 80, 70])
        result = calculate_cumulative_return(prices)

        assert result.iloc[0] == 0
        assert result.iloc[-1] == -30  # -30% cumulative return


class TestVolatility:
    """Tests for volatility calculation."""

    def test_basic_volatility(self):
        """Test basic volatility calculation."""
        returns = pd.Series([1, -2, 3, -1, 2])
        result = calculate_volatility(returns, annualize=False)

        assert result > 0
        assert isinstance(result, float)

    def test_annualized_volatility(self):
        """Test annualized volatility is higher than daily."""
        returns = pd.Series([1, -2, 3, -1, 2])
        daily_vol = calculate_volatility(returns, annualize=False)
        annual_vol = calculate_volatility(returns, annualize=True)

        assert annual_vol > daily_vol

    def test_zero_volatility(self):
        """Test with constant returns (zero volatility)."""
        returns = pd.Series([0, 0, 0, 0])
        result = calculate_volatility(returns, annualize=False)
        assert result == 0

    def test_empty_series(self):
        """Test with empty series."""
        returns = pd.Series([], dtype=float)
        result = calculate_volatility(returns)
        assert result == 0


class TestDrawdown:
    """Tests for drawdown calculation."""

    def test_basic_drawdown(self):
        """Test basic drawdown calculation."""
        prices = pd.Series([100, 110, 100, 90, 95])
        result = calculate_drawdown(prices)

        assert result.iloc[0] == 0  # No drawdown at start
        assert result.iloc[1] == 0  # At peak, no drawdown
        assert result.iloc[3] < 0  # Below peak, negative drawdown

    def test_max_drawdown(self):
        """Test maximum drawdown calculation."""
        prices = pd.Series([100, 120, 110, 90, 100])
        max_dd = calculate_max_drawdown(prices)

        assert max_dd < 0
        assert max_dd <= result.min() if (result := calculate_drawdown(prices)).any() else True

    def test_no_drawdown(self):
        """Test with continuously rising prices."""
        prices = pd.Series([100, 110, 120, 130])
        result = calculate_drawdown(prices)

        assert all(result == 0)  # No drawdown when always at new highs

    def test_empty_series(self):
        """Test with empty series."""
        prices = pd.Series([], dtype=float)
        result = calculate_drawdown(prices)
        assert result.empty


class TestSummaryStatistics:
    """Tests for summary statistics calculation."""

    def test_basic_summary(self):
        """Test basic summary statistics."""
        df = pd.DataFrame({
            "close": [100, 110, 105, 115, 120],
        })
        stats = calculate_summary_statistics(df)

        assert "current_price" in stats
        assert "daily_return" in stats
        assert "cumulative_return" in stats
        assert "volatility_daily" in stats
        assert "volatility_annual" in stats
        assert "max_drawdown" in stats

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        stats = calculate_summary_statistics(df)
        assert stats == {}

    def test_insufficient_data(self):
        """Test with insufficient data points."""
        df = pd.DataFrame({"close": [100]})
        stats = calculate_summary_statistics(df)
        assert stats == {}


class TestMovingAverages:
    """Tests for moving average calculations."""

    def test_sma_basic(self):
        """Test basic SMA calculation."""
        prices = pd.Series([1, 2, 3, 4, 5])
        result = calculate_sma(prices, window=3)

        assert result.isna().sum() == 2  # First 2 values should be NaN
        assert result.iloc[2] == 2  # (1+2+3)/3
        assert result.iloc[4] == 4  # (3+4+5)/3

    def test_ema_basic(self):
        """Test basic EMA calculation."""
        prices = pd.Series([1, 2, 3, 4, 5])
        result = calculate_ema(prices, window=3)

        assert not result.isna().any()  # EMA has no NaN values
        assert len(result) == len(prices)


class TestRSI:
    """Tests for RSI calculation."""

    def test_rsi_range(self):
        """Test that RSI is within 0-100 range."""
        prices = pd.Series([100, 102, 98, 105, 103, 107, 104, 110])
        result = calculate_rsi(prices)

        # Skip NaN values
        valid_rsi = result.dropna()
        assert all(valid_rsi >= 0)
        assert all(valid_rsi <= 100)
