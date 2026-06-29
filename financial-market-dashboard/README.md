# Financial Market Dashboard

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, production-ready web application for retrieving, analyzing, and visualizing financial market data from multiple sources.

## 📊 Features

### Core Features
- **Multi-Asset Support**: Stocks, Market Indexes, and Cryptocurrencies
- **Real-Time Data**: Automatic data retrieval from yfinance and CoinGecko APIs
- **Financial Indicators**: Daily/Cumulative Returns, Volatility, Drawdown Analysis
- **Interactive Charts**: Plotly-powered candlestick and line charts with zoom/pan
- **Asset Comparison**: Compare multiple assets with normalized prices and correlation analysis

### Dashboard Pages
1. **Market Overview**: KPI cards showing current price, returns, volatility, and max drawdown
2. **Price Charts**: Interactive charts with asset type and date range filters
3. **Financial Indicators**: Detailed metrics including return distribution and volatility analysis
4. **Asset Comparison**: Side-by-side comparison with correlation heatmap

### Optional Technical Indicators
- Simple Moving Average (SMA 20, 50)
- Exponential Moving Average (EMA)
- Relative Strength Index (RSI)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands

## 🛠️ Technologies

| Category | Technology |
|----------|------------|
| Language | Python 3.12+ |
| Framework | Streamlit |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly |
| API Integration | Requests, yfinance |
| Configuration | python-dotenv |
| Testing | pytest |

## 📁 Project Structure

```
financial-market-dashboard/
│
├── data/
│   ├── raw/              # Raw downloaded data
│   └── processed/        # Processed data with indicators
│
├── src/
│   ├── __init__.py       # Package initialization
│   ├── api.py            # API communication (yfinance, CoinGecko)
│   ├── indicators.py     # Financial calculations
│   ├── dashboard.py      # Streamlit UI components
│   ├── utils.py          # Utility functions
│   └── config.py         # Configuration & constants
│
├── tests/
│   ├── test_indicators.py
│   ├── test_utils.py
│   └── test_api.py
│
├── notebooks/            # Jupyter notebooks for analysis
├── assets/               # Static assets (images, etc.)
│
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore
└── README.md
```

## 🚀 Installation

### Prerequisites
- Python 3.12 or higher
- pip package manager

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/financial-market-dashboard.git
cd financial-market-dashboard
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` to customize settings (optional):

```env
# Default Assets Configuration
DEFAULT_STOCKS=PETR4.SA,VALE3.SA,AAPL,MSFT
DEFAULT_INDEXES=^BVSP,^GSPC,^IXIC,^DJI
DEFAULT_CRYPTO=bitcoin,ethereum,solana

# Cache Settings
CACHE_EXPIRY_HOURS=1

# Logging Level
LOG_LEVEL=INFO
```

## ▶️ Running the Application

### Option 1: Run the Dashboard

```bash
streamlit run src/dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Option 2: Update Market Data First

Before running the dashboard, you can fetch fresh market data:

```bash
python main.py
```

This will:
1. Download historical data for all configured assets
2. Save raw data to `data/raw/`
3. Calculate financial indicators
4. Save processed data to `data/processed/`

### Option 3: Automated Data Updates

Schedule regular data updates using cron (Linux/macOS) or Task Scheduler (Windows):

```bash
# Example: Update data daily at 6 AM
0 6 * * * cd /path/to/financial-market-dashboard && /path/to/venv/bin/python main.py
```

## 📈 Usage Guide

### Market Overview Page
- Select any asset from the dropdown
- View current price, daily return, cumulative return, volatility, and max drawdown
- See the data period and asset type

### Price Charts Page
- Filter by asset type (Stocks, Indexes, Crypto, All)
- Select specific asset
- Choose date range (1 Month to Max)
- Interact with candlestick/line charts (zoom, pan, hover)

### Financial Indicators Page
- View cumulative return trends
- Analyze drawdown patterns
- Examine return distribution histograms
- Compare volatility metrics

### Asset Comparison Page
- Select multiple assets to compare
- View normalized prices (base 100)
- Compare cumulative returns
- Analyze correlation matrix and heatmap

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_indicators.py -v
```

## 📝 API Reference

### update_market_data()

Automatically download and process market data.

```python
from main import update_market_data

results = update_market_data(
    stocks=["AAPL", "MSFT"],
    indexes=["^GSPC"],
    cryptos=["bitcoin"],
    save_processed=True
)
```

### Key Functions

| Module | Function | Description |
|--------|----------|-------------|
| `api.py` | `fetch_stock_data()` | Get stock/index data from yfinance |
| `api.py` | `fetch_crypto_data()` | Get crypto data from CoinGecko |
| `indicators.py` | `calculate_daily_return()` | Calculate percentage daily returns |
| `indicators.py` | `calculate_volatility()` | Calculate daily/annualized volatility |
| `indicators.py` | `calculate_drawdown()` | Calculate running drawdown |
| `utils.py` | `clean_data()` | Clean and preprocess DataFrame |
| `utils.py` | `normalize_prices()` | Normalize prices to base 100 |

## 🔧 Configuration

### Adding New Assets

Edit `.env` or modify `Config` class in `src/config.py`:

```python
DEFAULT_STOCKS = ["PETR4.SA", "VALE3.SA", "AAPL", "MSFT", "GOOGL"]
DEFAULT_CRYPTO = ["bitcoin", "ethereum", "solana", "cardano"]
```

### Customizing Cache Duration

```env
CACHE_EXPIRY_HOURS=24  # Cache valid for 24 hours
```

## 📊 Screenshots

> *Screenshots placeholder - Add actual screenshots when deploying*

### Market Overview
![Market Overview](assets/screenshots/overview.png)

### Price Charts
![Price Charts](assets/screenshots/charts.png)

### Asset Comparison
![Comparison](assets/screenshots/comparison.png)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📋 Future Improvements

- [ ] Portfolio performance analysis
- [ ] Alert system for price thresholds
- [ ] Export to Excel/PDF reports
- [ ] User authentication
- [ ] Database integration (PostgreSQL/MongoDB)
- [ ] Real-time WebSocket data streams
- [ ] Machine learning predictions
- [ ] Backtesting framework
- [ ] Docker containerization
- [ ] CI/CD pipeline

## ⚠️ Disclaimer

This application is for educational and informational purposes only. It is not intended as financial advice. Always do your own research before making investment decisions.

Data accuracy depends on third-party APIs (yfinance, CoinGecko). There may be delays or inaccuracies in the data provided.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- Financial Dashboard Team

## 🙏 Acknowledgments

- [yfinance](https://github.com/ranaroussi/yfinance) for stock market data
- [CoinGecko](https://www.coingecko.com/api) for cryptocurrency data
- [Streamlit](https://streamlit.io/) for the dashboard framework
- [Plotly](https://plotly.com/) for interactive visualizations

---

**Built with ❤️ using Python**
