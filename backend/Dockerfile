FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
# curl is required by the container healthcheck (GET /health) declared in
# docker-compose.yml.
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# TODO (Playwright): this image cannot run the SIGProv extraction yet.
# Missing, in order:
#   1. `playwright` and `asyncpg` in pyproject.toml (psycopg2-binary is the sync
#      driver and is no longer what the app uses).
#   2. After the dependency install below, browsers plus their system libs:
#          RUN playwright install --with-deps chromium
#      (`--with-deps` pulls libnss3, libatk-bridge2.0-0, libgbm1, libasound2, ...
#      on this Debian slim base).
# Until that lands, the extraction is run from the host (`make playwright-install`).

# Install uv
RUN pip install uv

# Copy pyproject.toml and lock file if exists
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies with uv
RUN uv pip install --system -e .

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
