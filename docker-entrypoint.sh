#!/usr/bin/env bash
set -e

echo "Fetching initial market data (this populates data/raw and data/processed)..."
python main.py

echo "Starting Streamlit dashboard..."
exec streamlit run src/dashboard.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true
