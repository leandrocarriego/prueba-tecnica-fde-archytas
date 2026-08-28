FROM python:3.14-slim

WORKDIR /app

# curl backs the container healthcheck (GET /health) declared in docker-compose.yml.
# postgresql-client is for `psql` from inside the container when debugging.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# TODO (Playwright): this image cannot run the SIGProv extraction yet. The
# dependency is declared in pyproject.toml, but the browser is not in the image.
# Before the first deploy, after the install below:
#     RUN uv run playwright install --with-deps chromium
# (`--with-deps` pulls libnss3, libatk-bridge2.0-0, libgbm1, libasound2, ... on
# this Debian slim base, and adds ~400MB.)
# Until that lands, the extraction runs from the host (`make playwright-install`).

RUN pip install --no-cache-dir uv

# Install into the system prefix instead of a project .venv, so `uvicorn` and
# `celery` are on PATH and docker-compose can keep overriding the command.
ENV UV_PROJECT_ENVIRONMENT=/usr/local

# `--locked` is what makes the build reproducible (Artículo IX): it installs the
# resolution recorded in uv.lock and FAILS if the lock drifted from
# pyproject.toml, instead of quietly resolving something else. Dependencies are
# installed before the source is copied so a code change does not invalidate
# their layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY . .
RUN uv sync --locked --no-dev

EXPOSE 8000

# Overridden per service in docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
