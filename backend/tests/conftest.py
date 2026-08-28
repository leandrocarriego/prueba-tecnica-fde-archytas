"""Shared fixtures for the whole suite.

Isolation strategy
------------------
Data access is async (SQLAlchemy 2.0 + asyncpg), and the services commit on
their own. So the suite does **not** recreate the schema per test: it wraps each
test in an outer transaction that is always rolled back.

    engine  ->  connection  ->  outer transaction (rolled back)
                                    `- AsyncSession(join_transaction_mode="create_savepoint")

The session joins the connection's transaction as a SAVEPOINT, which means a
`session.commit()` inside a service releases the savepoint but never reaches
the database's real commit. When the test ends, the outer transaction is rolled
back and the database is exactly as it was. It is the fastest option (no DDL per
test) and the only one that keeps committing services under test.

The HTTP client shares that same session through a `get_session` override, so
what a request writes is visible to the test that made it, and vanishes with it.

Database
--------
The schema is built once per run, on a database of its own (`cordillera_test`,
created if missing). The suite refuses to start against anything whose name does
not end in `_test`.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# Importing `app.main` also imports the model registry, so `Base.metadata` knows
# every table before the schema is created below.
from app.database import Base, get_session
from app.main import app

BASE_URL = "http://testserver"
API_PREFIX = f"/api/{settings.API_VERSION}"

# The one-way extraction pipeline plus the operational schema. None of them holds
# a table yet: they are created so the first schema-qualified model to land does
# not fail with InvalidSchemaName.
PIPELINE_SCHEMAS: tuple[str, ...] = ("raw", "staging", "core", "operations")

# Connecting to `postgres` to issue CREATE DATABASE: a database cannot be
# created from inside itself.
MAINTENANCE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
)

if not settings.POSTGRES_DB.endswith("_test"):
    raise RuntimeError(
        f"The suite would run against {settings.POSTGRES_DB!r}. "
        "Tests only run against a database whose name ends in '_test'."
    )


# --- Schema provisioning -------------------------------------------------


async def _create_database_if_missing() -> None:
    """Create the test database unless the server already has it."""
    engine = create_async_engine(MAINTENANCE_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": settings.POSTGRES_DB},
            )
            if not exists:
                await connection.execute(text(f'CREATE DATABASE "{settings.POSTGRES_DB}"'))
    finally:
        await engine.dispose()


async def _create_schema() -> None:
    """Rebuild the schema from the models, from scratch.

    Deliberately not Alembic: the migrations own the *production* schema, and
    running them here would make every test run depend on a migration history
    that a feature branch may still be editing.
    """
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            for schema in PIPELINE_SCHEMAS:
                await connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


async def _provision() -> None:
    await _create_database_if_missing()
    await _create_schema()


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> Iterator[None]:
    """Prepare the test database once per run.

    Synchronous on purpose: it owns its event loop through `asyncio.run` instead
    of borrowing the per-test loop that pytest-asyncio creates, so nothing here
    can leak a connection into a test.
    """
    asyncio.run(_provision())
    yield


# --- Database fixtures ---------------------------------------------------


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """A per-test engine with no pool.

    Each test runs in its own event loop, and an asyncpg connection belongs to
    the loop that opened it. `NullPool` means no connection ever outlives the
    loop it was created on.
    """
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        yield test_engine
    finally:
        await test_engine.dispose()


@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """An open connection with a transaction that is always rolled back."""
    async with engine.connect() as open_connection:
        transaction = await open_connection.begin()
        try:
            yield open_connection
        finally:
            await transaction.rollback()


@pytest.fixture
async def session(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """The session every test and every request share.

    `join_transaction_mode="create_savepoint"` is what lets the code under test
    commit without escaping the test's transaction.
    """
    async with AsyncSession(
        bind=connection,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    ) as open_session:
        yield open_session


# --- HTTP client ---------------------------------------------------------


@pytest.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """An anonymous client, talking to the app in-process over the test session.

    There is no authenticated variant yet: issuing a token needs `identity`,
    which has not landed. Its fixtures — the users, their roles and their
    clients — come back in the same commit as the module.
    """

    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as http_client:
            yield http_client
    finally:
        app.dependency_overrides.pop(get_session, None)
