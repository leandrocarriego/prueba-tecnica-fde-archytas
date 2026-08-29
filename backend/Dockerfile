FROM python:3.14-slim

WORKDIR /app

# curl backs the container healthcheck (GET /health) declared in docker-compose.yml.
# postgresql-client is for `psql` from inside the container when debugging.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

# The browser the extraction reads the portal through. Article I says the portal
# is read from the rendered screen and never through its internal JSON, so this
# is not an optimisation: without it the extraction cannot run at all, and it
# fails at the first `chromium.launch()` with the run already open.
#
# `--with-deps` pulls what Chromium needs on this Debian slim base — libnss3,
# libatk-bridge2.0-0, libgbm1, libasound2 and company. It adds around 400 MB to
# an image that three services share, and that is the price of the article.
#
# On its own layer, right after the dependencies and before the source: the
# browser has no reason to be downloaded again because a handler changed.
RUN playwright install --with-deps chromium

COPY . .
RUN uv sync --locked --no-dev

EXPOSE 8000

# Overridden per service in docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
