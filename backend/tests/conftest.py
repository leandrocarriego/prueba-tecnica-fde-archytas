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
from contextlib import asynccontextmanager
from datetime import UTC, datetime

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
from app.modules.identity import middleware as identity_middleware
from app.modules.identity.models import Session as UserSession
from app.modules.identity.models import User, UserRole
from app.modules.identity.security import generate_token, hash_token
from tests.factories.user_factory import UserFactory

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


async def open_session(session: AsyncSession, user: User) -> str:
    """Open a real session for this user and return the token that reaches it.

    A session stopped being a signed string and became a row, so a test cannot
    mint one on its own any more: it has to write what the application would
    have written. That is the point of the change and not a nuisance — a
    fixture that forged a token would keep passing after the code stopped
    honouring revocation, which is exactly what these tests exist to catch.

    What is stored is the hash; what the caller sends is the token.
    """
    token = generate_token()
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            last_seen_at=datetime.now(UTC),
        )
    )
    await session.flush()
    return token


async def authorization_header(session: AsyncSession, user: User) -> dict[str, str]:
    """The header a client sends once it holds a live session of this user."""
    return {"Authorization": f"Bearer {await open_session(session, user)}"}


def _use_test_session(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the app at the test's session: dependencies and middleware alike.

    `get_session` covers everything that runs inside a request. The middleware
    that records refusals is the exception: it opens a session of its own
    precisely because the request's was rolled back by the 403 that produced
    it, so an override of the dependency never reaches it. Without this second
    seam its rows would land outside the test's transaction — invisible to the
    test that caused them, and left behind for the next one.
    """

    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield session

    @asynccontextmanager
    async def _factory() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _session_override
    monkeypatch.setattr(identity_middleware, "SessionFactory", _factory)


@pytest.fixture
async def client(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    """An anonymous client, talking to the app in-process over the test session."""
    _use_test_session(session, monkeypatch)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as http_client:
            yield http_client
    finally:
        app.dependency_overrides.pop(get_session, None)


# --- The three roles the business has ------------------------------------
#
# Each role gets its **own** client rather than a header slapped onto the shared
# one: `client` is the anonymous caller, and a test that uses both (an owner
# creating an account, its holder then logging in) needs them to stay separate.


@pytest.fixture
async def owner(session: AsyncSession) -> User:
    """The owner: admitted everywhere."""
    return await UserFactory.create(session, role=UserRole.OWNER)


@pytest.fixture
async def purchasing_user(session: AsyncSession) -> User:
    """Whoever handles purchasing."""
    return await UserFactory.create(session, role=UserRole.PURCHASING)


@pytest.fixture
async def sales_user(session: AsyncSession) -> User:
    """Whoever handles sales."""
    return await UserFactory.create(session, role=UserRole.SALES)


async def _client_for(
    session: AsyncSession, user: User, monkeypatch: pytest.MonkeyPatch
) -> AsyncClient:
    """Build a client that calls as this user, over the test's session."""
    _use_test_session(session, monkeypatch)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL,
        headers=await authorization_header(session, user),
    )


@pytest.fixture
async def owner_client(
    session: AsyncSession, owner: User, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    """A client calling as the owner."""
    async with await _client_for(session, owner, monkeypatch) as http_client:
        yield http_client


@pytest.fixture
async def purchasing_client(
    session: AsyncSession, purchasing_user: User, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    """A client calling as whoever handles purchasing."""
    async with await _client_for(session, purchasing_user, monkeypatch) as http_client:
        yield http_client


@pytest.fixture
async def sales_client(
    session: AsyncSession, sales_user: User, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    """A client calling as whoever handles sales."""
    async with await _client_for(session, sales_user, monkeypatch) as http_client:
        yield http_client
