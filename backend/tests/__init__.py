"""Test suite bootstrap.

`tests/` is a package, so Python imports this file before `tests/conftest.py`.
That makes it the only place where the environment can be redirected **before**
`app.config` reads it: `Settings` is built once, at import time, and cached.

Two variables are forced rather than merely defaulted:

* ``POSTGRES_DB`` — the suite must never touch the development database. The
  name is pinned here, and `conftest` refuses to run if it does not end in
  ``_test``. Environment variables win over the repository's `.env`, so pinning
  it here also protects a developer who exports ``POSTGRES_DB`` in their shell.
* ``ENVIRONMENT`` — ``DEVELOPMENT`` would put the root logger at DEBUG and bury
  the test report under application logs.

Everything else (credentials, host, port, secret key) still comes from the
`.env` at the repository root; the fallbacks below only apply when that file is
absent, so the suite can also run on a machine that never configured one.
"""

import os
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPOSITORY_ROOT / ".env"

TEST_DATABASE = os.environ.get("TEST_POSTGRES_DB", "cordillera_test")

os.environ["POSTGRES_DB"] = TEST_DATABASE
os.environ["ENVIRONMENT"] = "TESTING"

# Used only when there is no `.env` to read them from.
ENV_FALLBACKS: dict[str, str] = {
    "SECRET_KEY": "test-secret-key",
    "POSTGRES_USER": "cordillera",
    "POSTGRES_PASSWORD": "cordillera",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5433",
}

if not ENV_FILE.exists():
    for name, value in ENV_FALLBACKS.items():
        os.environ.setdefault(name, value)
