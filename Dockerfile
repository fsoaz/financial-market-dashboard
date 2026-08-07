FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies first (separate layer, cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# .env.example ships no secrets (yfinance/CoinGecko free tier, unauthenticated);
# copy it as the default .env so Config's os.getenv() calls have sane defaults
# even if the user doesn't mount their own .env.
RUN cp .env.example .env

# Run as non-root
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
