"""
Streamlit dashboard for the Financial Market Dashboard.

This module contains all UI components and page layouts for the
interactive dashboard application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# `streamlit run src/dashboard.py` puts src/ on sys.path, not the repo root, so the
# absolute `src.*` imports below fail. Add the repo root explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.indicators import (
    add_financial_indicators,
    calculate_summary_statistics,
)
from src.utils import (
    clean_data,
    load_all_data,
    normalize_prices,
    format_currency,
    format_percentage,
    filter_by_date_range,
    get_date_range_options,
    calculate_correlation_matrix,
)

logger = logging.getLogger(__name__)


def create_kpi_card(
    title: str, value: str, delta: Optional[str] = None, delta_color: str = "normal"
) -> None:
    """
    Display a KPI metric card.

    Args:
        title: Card title.
        value: Main value to display.
        delta: Optional change indicator.
        delta_color: Color scheme for delta ('normal', 'inverse', 'off').
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric(label=title, value=value, delta=delta, delta_color=delta_color)


def create_price_chart(
    df: pd.DataFrame, symbol: str, asset_type: str
) -> go.Figure:
    """
    Create an interactive price chart with candlestick or line.

    Args:
        df: DataFrame with OHLC data.
        symbol: Asset symbol.
        asset_type: Type of asset.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure()

    # Candlestick chart for stocks/indexes with OHLC data
    if asset_type in ["stocks", "indexes"] and all(
        col in df.columns for col in ["open", "high", "low", "close"]
    ):
        fig.add_trace(
            go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name=symbol,
            )
        )
    else:
        # Line chart for crypto or when OHLC not available
        fig.add_trace(go.Scatter(x=df["date"], y=df["close"], name=symbol, mode="lines"))

    fig.update_layout(
        title=f"{symbol} Price Chart",
        xaxis_title="Date",
        yaxis_title="Price",
        hovermode="x unified",
        height=600,
        template="plotly_dark",
        xaxis_rangeslider_visible=True,
    )

    return fig


def create_cumulative_return_chart(data: dict[str, pd.DataFrame]) -> go.Figure:
    """
    Create cumulative return comparison chart.

    Args:
        data: Dictionary mapping symbol to DataFrame.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure()

    for symbol, df in data.items():
        if df.empty or "close" not in df.columns:
            continue

        cum_return = ((df["close"] - df["close"].iloc[0]) / df["close"].iloc[0]) * 100
        fig.add_trace(
            go.Scatter(x=df["date"], y=cum_return, name=symbol, mode="lines")
        )

    fig.update_layout(
        title="Cumulative Returns Comparison",
        xaxis_title="Date",
        yaxis_title="Cumulative Return (%)",
        hovermode="x unified",
        height=500,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_drawdown_chart(data: dict[str, pd.DataFrame]) -> go.Figure:
    """
    Create drawdown chart for multiple assets.

    Args:
        data: Dictionary mapping symbol to DataFrame.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure()

    for symbol, df in data.items():
        if df.empty or "close" not in df.columns:
            continue

        running_max = df["close"].cummax()
        drawdown = ((df["close"] - running_max) / running_max) * 100
        fig.add_trace(go.Scatter(x=df["date"], y=drawdown, name=symbol, mode="lines"))

    fig.update_layout(
        title="Drawdown Analysis",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        hovermode="x unified",
        height=400,
        template="plotly_dark",
    )

    return fig


def create_return_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create histogram of return distribution.

    Args:
        df: DataFrame with daily_return column.

    Returns:
        Plotly Figure object.
    """
    if "daily_return" not in df.columns:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=df["daily_return"].dropna(),
            nbinsx=50,
            name="Returns",
            marker_color="#1f77b4",
        )
    )

    fig.update_layout(
        title="Return Distribution",
        xaxis_title="Daily Return (%)",
        yaxis_title="Frequency",
        height=400,
        template="plotly_dark",
        showlegend=False,
    )

    return fig


def create_volatility_chart(data: dict[str, pd.DataFrame]) -> go.Figure:
    """
    Create volatility comparison bar chart.

    Args:
        data: Dictionary mapping symbol to DataFrame.

    Returns:
        Plotly Figure object.
    """
    volatilities = {}

    for symbol, df in data.items():
        if df.empty or "close" not in df.columns or len(df) < 2:
            continue

        returns = df["close"].pct_change().dropna()
        annual_vol = returns.std() * (252**0.5) * 100
        volatilities[symbol] = annual_vol

    if not volatilities:
        return go.Figure()

    fig = go.Figure(
        data=[
            go.Bar(
                x=list(volatilities.keys()),
                y=list(volatilities.values()),
                marker_color="#2ca02c",
            )
        ]
    )

    fig.update_layout(
        title="Annualized Volatility Comparison",
        xaxis_title="Asset",
        yaxis_title="Volatility (%)",
        height=400,
        template="plotly_dark",
    )

    return fig


def create_normalized_price_chart(data: dict[str, pd.DataFrame]) -> go.Figure:
    """
    Create normalized price chart (base 100).

    Args:
        data: Dictionary mapping symbol to DataFrame.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure()

    for symbol, df in data.items():
        if df.empty or "close" not in df.columns:
            continue

        normalized = normalize_prices(df)
        # normalize_prices drops NaN rows; align x to the surviving index.
        fig.add_trace(
            go.Scatter(x=df.loc[normalized.index, "date"], y=normalized, name=symbol, mode="lines")
        )

    fig.update_layout(
        title="Normalized Prices (Base 100)",
        xaxis_title="Date",
        yaxis_title="Normalized Price",
        hovermode="x unified",
        height=500,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_correlation_heatmap(correlation_df: pd.DataFrame) -> go.Figure:
    """
    Create correlation heatmap.

    Args:
        correlation_df: Correlation matrix DataFrame.

    Returns:
        Plotly Figure object.
    """
    if correlation_df.empty:
        return go.Figure()

    fig = go.Figure(
        data=go.Heatmap(
            z=correlation_df.values,
            x=correlation_df.columns,
            y=correlation_df.columns,
            colorscale="RdBu",
            zmid=0,
            text=correlation_df.values.round(2),
            texttemplate="%{text}",
            textfont={"size": 10},
        )
    )

    fig.update_layout(
        title="Asset Correlation Heatmap",
        height=500,
        template="plotly_dark",
        xaxis_title="Asset",
        yaxis_title="Asset",
    )

    return fig


def render_market_overview(data: dict[str, pd.DataFrame]) -> None:
    """
    Render the Market Overview page.

    Args:
        data: Dictionary mapping symbol to DataFrame.
    """
    st.title("📊 Market Overview")
    st.markdown("Current market metrics and key performance indicators")

    if not data:
        st.warning("No data available. Please refresh the data.")
        return

    # Asset selector
    symbols = list(data.keys())
    selected_symbol = st.selectbox("Select Asset", symbols)

    if selected_symbol not in data:
        st.error(f"No data for {selected_symbol}")
        return

    df = data[selected_symbol].copy()
    df = clean_data(df)

    if df.empty:
        st.error("No valid data after cleaning")
        return

    # Calculate statistics
    stats = calculate_summary_statistics(df)

    if not stats:
        st.error("Could not calculate statistics")
        return

    # Display KPI cards
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Current Price",
            value=format_currency(stats["current_price"]),
        )

    with col2:
        daily_ret = stats["daily_return"]
        st.metric(
            label="Daily Return",
            value=format_percentage(daily_ret),
            delta=format_percentage(daily_ret),
            delta_color="inverse" if daily_ret < 0 else "normal",
        )

    with col3:
        cum_ret = stats["cumulative_return"]
        st.metric(
            label="Cumulative Return",
            value=format_percentage(cum_ret),
        )

    with col4:
        st.metric(
            label="Annual Volatility",
            value=format_percentage(stats["volatility_annual"]),
        )

    with col5:
        max_dd = stats["max_drawdown"]
        st.metric(
            label="Max Drawdown",
            value=format_percentage(max_dd),
            delta=format_percentage(max_dd),
            delta_color="inverse",
        )

    # Additional info
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.info(f"**Period:** {stats['start_date']} to {stats['end_date']}")
    with col_b:
        asset_type = df["asset_type"].iloc[0] if "asset_type" in df.columns else "Unknown"
        st.info(f"**Asset Type:** {asset_type.capitalize()}")


def render_price_charts(data: dict[str, pd.DataFrame]) -> None:
    """
    Render the Price Charts page.

    Args:
        data: Dictionary mapping symbol to DataFrame.
    """
    st.title("📈 Price Charts")
    st.markdown("Interactive price charts with customizable filters")

    if not data:
        st.warning("No data available.")
        return

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        asset_types = ["All"] + list(
            set(df["asset_type"].iloc[0] for df in data.values() if "asset_type" in df.columns)
        )
        selected_type = st.selectbox("Asset Type", asset_types)

    with col2:
        if selected_type == "All":
            symbols = list(data.keys())
        else:
            symbols = [
                s for s, df in data.items()
                if "asset_type" in df.columns and df["asset_type"].iloc[0] == selected_type
            ]
        selected_symbol = st.selectbox("Asset", symbols)

    with col3:
        date_ranges = get_date_range_options()
        selected_range = st.selectbox("Date Range", date_ranges)

    if selected_symbol not in data:
        st.error(f"No data for {selected_symbol}")
        return

    df = data[selected_symbol].copy()
    df = clean_data(df)
    df = filter_by_date_range(df, selected_range)

    if df.empty:
        st.error("No data for selected filters")
        return

    # Display chart
    asset_type = df["asset_type"].iloc[0] if "asset_type" in df.columns else "stocks"
    fig = create_price_chart(df, selected_symbol, asset_type)
    st.plotly_chart(fig, use_container_width=True)

    # Show data table
    with st.expander("View Raw Data"):
        st.dataframe(df.tail(100))


def render_financial_indicators(data: dict[str, pd.DataFrame]) -> None:
    """
    Render the Financial Indicators page.

    Args:
        data: Dictionary mapping symbol to DataFrame.
    """
    st.title("📉 Financial Indicators")
    st.markdown("Detailed financial metrics and analysis")

    if not data:
        st.warning("No data available.")
        return

    selected_symbol = st.selectbox("Select Asset", list(data.keys()))

    if selected_symbol not in data:
        st.error(f"No data for {selected_symbol}")
        return

    df = data[selected_symbol].copy()
    df = clean_data(df)
    df = add_financial_indicators(df)

    if df.empty:
        st.error("No valid data")
        return

    # Layout
    tab1, tab2, tab3, tab4 = st.tabs([
        "Cumulative Return",
        "Drawdown",
        "Return Distribution",
        "Volatility"
    ])

    with tab1:
        fig = create_cumulative_return_chart({selected_symbol: df})
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = create_drawdown_chart({selected_symbol: df})
        st.plotly_chart(fig, use_container_width=True)

        # Show max drawdown value
        max_dd = df["drawdown"].min() if "drawdown" in df.columns else 0
        st.metric("Maximum Drawdown", format_percentage(max_dd))

    with tab3:
        fig = create_return_distribution_chart(df)
        st.plotly_chart(fig, use_container_width=True)

        # Statistics
        if "daily_return" in df.columns:
            returns = df["daily_return"].dropna()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Mean Daily Return", format_percentage(returns.mean()))
            with col2:
                st.metric("Std Dev", format_percentage(returns.std()))
            with col3:
                st.metric("Skewness", f"{returns.skew():.2f}")

    with tab4:
        # Volatility chart
        fig = create_volatility_chart({selected_symbol: df})
        st.plotly_chart(fig, use_container_width=True)

        # Metrics
        if "close" in df.columns and len(df) > 1:
            returns = df["close"].pct_change().dropna()
            daily_vol = returns.std() * 100
            annual_vol = returns.std() * (252**0.5) * 100

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Daily Volatility", format_percentage(daily_vol))
            with col2:
                st.metric("Annualized Volatility", format_percentage(annual_vol))


def render_asset_comparison(data: dict[str, pd.DataFrame]) -> None:
    """
    Render the Asset Comparison page.

    Args:
        data: Dictionary mapping symbol to DataFrame.
    """
    st.title("⚖️ Asset Comparison")
    st.markdown("Compare multiple assets side by side")

    if not data:
        st.warning("No data available.")
        return

    # Multi-select for assets
    selected_assets = st.multiselect(
        "Select Assets to Compare",
        list(data.keys()),
        default=list(data.keys())[:3] if len(data) >= 3 else list(data.keys()),
    )

    if not selected_assets:
        st.info("Select at least one asset")
        return

    # Filter data
    filtered_data = {s: clean_data(data[s].copy()) for s in selected_assets if s in data}

    if not filtered_data:
        st.error("No valid data for selected assets")
        return

    # Tabs for different comparison views
    tab1, tab2, tab3, tab4 = st.tabs([
        "Normalized Prices",
        "Cumulative Returns",
        "Volatility",
        "Correlation"
    ])

    with tab1:
        fig = create_normalized_price_chart(filtered_data)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = create_cumulative_return_chart(filtered_data)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        fig = create_volatility_chart(filtered_data)
        st.plotly_chart(fig, use_container_width=True)

        # Summary table
        st.subheader("Volatility Summary")
        vol_data = []
        for symbol, df in filtered_data.items():
            if "close" in df.columns and len(df) > 1:
                returns = df["close"].pct_change().dropna()
                annual_vol = returns.std() * (252**0.5) * 100
                vol_data.append({
                    "Asset": symbol,
                    "Annual Volatility (%)": round(annual_vol, 2)
                })
        if vol_data:
            st.dataframe(pd.DataFrame(vol_data), hide_index=True)

    with tab4:
        corr_matrix = calculate_correlation_matrix(filtered_data)
        if not corr_matrix.empty:
            fig = create_correlation_heatmap(corr_matrix)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Correlation Matrix")
            st.dataframe(corr_matrix.round(3))


def render_dashboard() -> None:
    """
    Main dashboard rendering function.
    Orchestrates page navigation and data loading.
    """
    # Page configuration
    st.set_page_config(
        page_title="Financial Market Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Sidebar
    with st.sidebar:
        st.title("📊 FMD")
        st.markdown("Financial Market Dashboard")
        st.divider()

        # Navigation
        page = st.radio(
            "Navigation",
            ["Market Overview", "Price Charts", "Financial Indicators", "Asset Comparison"],
            label_visibility="collapsed",
        )

        st.divider()

        # Data refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.session_state["refresh_data"] = True

        st.divider()
        st.markdown("""
        ### About
        Built with Python, Streamlit, and Plotly
        
        **Data Sources:**
        - yfinance (Stocks & Indexes)
        - CoinGecko (Crypto)
        """)

    # Load data
    @st.cache_data(ttl=3600)
    def load_market_data():
        """Load all market data with caching."""
        return load_all_data(processed=True)

    # Check for refresh
    if st.session_state.get("refresh_data", False):
        st.cache_data.clear()
        st.session_state["refresh_data"] = False

    data = load_market_data()

    # Route to appropriate page
    if page == "Market Overview":
        render_market_overview(data)
    elif page == "Price Charts":
        render_price_charts(data)
    elif page == "Financial Indicators":
        render_financial_indicators(data)
    elif page == "Asset Comparison":
        render_asset_comparison(data)


if __name__ == "__main__":
    render_dashboard()
