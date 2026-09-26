"""Tests for dashboard figures and the four rendered pages."""

from contextlib import nullcontext
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src import dashboard


@pytest.fixture
def prices():
    close = [100.0, 110.0, 105.0, 115.0, 112.0, 120.0, 118.0, 125.0, 121.0, 130.0]
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(close)),
            "symbol": ["AAPL"] * len(close),
            "asset_type": ["stocks"] * len(close),
            "open": [value - 1 for value in close],
            "high": [value + 2 for value in close],
            "low": [value - 2 for value in close],
            "close": close,
            "volume": [1000] * len(close),
        }
    )


@pytest.fixture
def ui(monkeypatch):
    st = MagicMock()
    st.columns.side_effect = lambda count: [
        nullcontext() for _ in range(count if isinstance(count, int) else len(count))
    ]
    st.tabs.side_effect = lambda labels: [nullcontext() for _ in labels]
    st.expander.return_value = nullcontext()
    st.selectbox.side_effect = lambda label, options: options[0]
    st.multiselect.side_effect = lambda label, options, default: default
    st.cache_data.side_effect = lambda **kwargs: lambda function: function
    st.session_state = {}
    monkeypatch.setattr(dashboard, "st", st)
    return st


def test_price_chart_uses_candles_for_stocks_and_lines_for_crypto(prices):
    candles = dashboard.create_price_chart(prices, "AAPL", "stocks")
    crypto = dashboard.create_price_chart(prices, "bitcoin", "crypto")

    assert candles.data[0].type == "candlestick"
    assert list(candles.data[0].close) == prices["close"].tolist()
    assert crypto.data[0].type == "scatter"
    assert list(crypto.data[0].y) == prices["close"].tolist()


def test_return_drawdown_and_distribution_charts(prices):
    data = {"AAPL": prices, "empty": pd.DataFrame()}
    cumulative = dashboard.create_cumulative_return_chart(data)
    drawdown = dashboard.create_drawdown_chart(data)
    returns = dashboard.create_return_distribution_chart(dashboard.add_financial_indicators(prices))

    assert len(cumulative.data) == 1
    assert cumulative.data[0].y[-1] == pytest.approx(30.0)
    assert drawdown.data[0].y[2] == pytest.approx((105 / 110 - 1) * 100)
    assert returns.data[0].type == "histogram"
    assert len(returns.data[0].x) == len(prices) - 1


def test_volatility_normalization_and_correlation_charts(prices):
    second = prices.copy()
    second["symbol"] = "MSFT"
    second["close"] = [200.0, 190.0, 205.0, 195.0, 210.0, 200.0, 220.0, 210.0, 225.0, 215.0]
    data = {"AAPL": prices, "MSFT": second}

    volatility = dashboard.create_volatility_chart(data)
    normalized = dashboard.create_normalized_price_chart(data)
    correlation = dashboard.calculate_correlation_matrix(data)
    heatmap = dashboard.create_correlation_heatmap(correlation)

    assert volatility.data[0].type == "bar"
    assert all(value > 0 for value in volatility.data[0].y)
    assert list(normalized.data[0].y)[0] == pytest.approx(100.0)
    assert list(normalized.data[1].y)[0] == pytest.approx(100.0)
    assert heatmap.data[0].type == "heatmap"
    assert heatmap.data[0].z[0][0] == pytest.approx(1.0)


def test_empty_chart_inputs_produce_empty_figures(prices):
    assert not dashboard.create_return_distribution_chart(prices).data
    assert not dashboard.create_volatility_chart({"AAPL": prices.iloc[:1]}).data
    assert not dashboard.create_correlation_heatmap(pd.DataFrame()).data
    assert not dashboard.create_cumulative_return_chart({"AAPL": pd.DataFrame()}).data
    assert not dashboard.create_drawdown_chart({"AAPL": pd.DataFrame()}).data


def test_kpi_card_displays_metric(ui):
    dashboard.create_kpi_card("Current Price", "$100", delta="+2%")
    ui.metric.assert_called_once_with(
        label="Current Price", value="$100", delta="+2%", delta_color="normal"
    )


def test_market_overview_displays_metrics(ui, prices):
    dashboard.render_market_overview({"AAPL": prices})

    labels = [call.kwargs["label"] for call in ui.metric.call_args_list]
    assert labels == [
        "Current Price",
        "Daily Return",
        "Cumulative Return",
        "Annual Volatility",
        "Max Drawdown",
    ]
    assert ui.metric.call_args_list[0].kwargs["value"] == "$130.00"
    assert ui.info.call_count == 2


def test_price_page_displays_chart_and_filtered_data(ui, prices):
    dashboard.render_price_charts({"AAPL": prices})

    figure = ui.plotly_chart.call_args.args[0]
    assert figure.data[0].type == "candlestick"
    assert len(ui.dataframe.call_args.args[0]) == len(prices)
    assert not ui.error.called


def test_indicator_page_displays_four_charts_and_metrics(ui, prices):
    dashboard.render_financial_indicators({"AAPL": prices})

    assert ui.plotly_chart.call_count == 4
    labels = [call.args[0] for call in ui.metric.call_args_list]
    assert "Maximum Drawdown" in labels
    assert "Annualized Volatility" in labels
    assert "Mean Daily Return" in labels


def test_comparison_page_displays_assets_and_correlation(ui, prices):
    second = prices.copy()
    second["symbol"] = "MSFT"
    second["close"] = second["close"] * 1.1

    dashboard.render_asset_comparison({"AAPL": prices, "MSFT": second})

    assert ui.plotly_chart.call_count == 4
    assert ui.dataframe.call_count == 2
    assert ui.subheader.call_args_list[-1].args[0] == "Correlation Matrix"


@pytest.mark.parametrize(
    "page, renderer",
    [
        ("Market Overview", "render_market_overview"),
        ("Price Charts", "render_price_charts"),
        ("Financial Indicators", "render_financial_indicators"),
        ("Asset Comparison", "render_asset_comparison"),
    ],
)
def test_dashboard_routes_to_selected_page(ui, monkeypatch, page, renderer):
    ui.radio.return_value = page
    monkeypatch.setattr(dashboard, "load_all_data", lambda processed: {"AAPL": pd.DataFrame()})
    page_renderer = MagicMock()
    monkeypatch.setattr(dashboard, renderer, page_renderer)

    dashboard.render_dashboard()

    page_renderer.assert_called_once()
    assert "AAPL" in page_renderer.call_args.args[0]
    ui.set_page_config.assert_called_once()


def test_dashboard_refresh_clears_cached_data(ui, monkeypatch):
    ui.radio.return_value = "Market Overview"
    ui.button.return_value = True
    monkeypatch.setattr(dashboard, "load_all_data", lambda processed: {})
    monkeypatch.setattr(dashboard, "render_market_overview", lambda data: None)

    dashboard.render_dashboard()

    ui.cache_data.clear.assert_called_once()
    assert ui.session_state["refresh_data"] is False


@pytest.mark.parametrize(
    "renderer",
    [
        dashboard.render_market_overview,
        dashboard.render_price_charts,
        dashboard.render_financial_indicators,
        dashboard.render_asset_comparison,
    ],
)
def test_pages_warn_when_data_is_empty(ui, renderer):
    renderer({})
    ui.warning.assert_called_once()
