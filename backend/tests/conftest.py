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
import importlib.util
import json
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from app.modules.notifications import tasks as notification_tasks
from app.modules.portal import handlers as portal_handlers
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


def _signed_category_seed() -> object:
    """The seeded rubros, read from the migration that seeds them.

    The suite builds its schema from the models and not from Alembic, so the
    **data** a migration loads would simply not be here — and 008 seeds the
    table of equivalences the client signed. Without it every test would see a
    system where nothing is classified and eighteen written forms are waiting
    in the review queue, which is not the system that gets deployed.

    It is read from the migration file rather than copied, because two copies
    of a seed are one seed and one bug: the day somebody adds a rubro there,
    this reads it without being edited.
    """
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    location = next(path.glob("0010_*.py"))
    spec = importlib.util.spec_from_file_location("category_seed_migration", location)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _seed_reference_data() -> None:
    """Load what the migrations seed, so the suite runs on the deployed system."""
    migration = _signed_category_seed()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            for name, written_forms in migration.SEED:  # type: ignore[attr-defined]
                category_id = await connection.scalar(
                    text("INSERT INTO core.category (name) VALUES (:name) RETURNING id"),
                    {"name": name},
                )
                seen: set[str] = set()
                for form in written_forms:
                    key = migration._key(form)  # type: ignore[attr-defined] # noqa: SLF001
                    if key in seen:
                        continue
                    seen.add(key)
                    rule_id = await connection.scalar(
                        text(
                            "INSERT INTO operations.resolution_rule "
                            "(kind, matcher, decision, created_by_user_id, created_by_name) "
                            "VALUES ('unknown_category', CAST(:matcher AS jsonb), "
                            "CAST(:decision AS jsonb), NULL, :author) RETURNING id"
                        ),
                        {
                            "matcher": json.dumps(
                                {"kind": "unknown_category", "category_text": form}
                            ),
                            "decision": json.dumps({"category_id": category_id}),
                            "author": "Sembrado en la puesta en marcha",
                        },
                    )
                    await connection.execute(
                        text(
                            "INSERT INTO core.category_alias "
                            "(category_id, text_normalized, text_original, rule_id, source) "
                            "VALUES (:category_id, :key, :original, :rule_id, 'SEED')"
                        ),
                        {
                            "category_id": category_id,
                            "key": key,
                            "original": form,
                            "rule_id": rule_id,
                        },
                    )
    finally:
        await engine.dispose()


async def _provision() -> None:
    await _create_database_if_missing()
    await _create_schema()
    await _seed_reference_data()


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


# --- The broker: never reached -------------------------------------------
#
# A handler that queues work returns immediately by design (`GEN-09`), and in a
# test the queue is exactly the part that must not be exercised: the suite runs
# with RabbitMQ down, like it runs with the portal down.
#
# It lives here, not beside the feature tests, because the rule belongs to the
# suite and not to one package. Kept local, it passes on the machine that
# happens to have the broker up and fails in CI, which is the worst place to
# find out — and it did: seven tests of 004 failed there for a year of commits
# because `extract_invoice_file` had no fixture at all.
#
# Which is why the one below is **autouse** and these two are not. A recorder a
# test has to remember to ask for only protects the tests whose author knew the
# task existed; the invoice files are queued from a handler nobody calls
# directly, so nobody remembered. Asking for it by name still works, and is how
# a test asserts on what would have been queued.


class Queued:
    """Records what would have been queued, instead of queueing it."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def apply_async(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)

    def delay(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append({"args": args, "kwargs": kwargs})

    @property
    def count(self) -> int:
        return len(self.calls)


@pytest.fixture
def queued_history(monkeypatch: pytest.MonkeyPatch) -> Iterator[Queued]:
    """The history visits a registered product would trigger (RF-38)."""
    recorder = Queued()
    monkeypatch.setattr(portal_handlers, "extract_product_history", recorder)
    yield recorder


@pytest.fixture(autouse=True)
def queued_invoice_files(monkeypatch: pytest.MonkeyPatch) -> Iterator[Queued]:
    """The browser visit each registered invoice would queue to fetch its file.

    Autouse, unlike its siblings. `bring_invoice_files` runs inside the
    publisher's transaction (`GEN-09`), so when the broker refuses the
    connection the handler raises and takes the whole registration down with
    it: seven integration tests of 004 fail with `OperationalError: [Errno 111]
    Connection refused` on a machine without RabbitMQ, which is every CI run.
    Nothing in the test asks for the queue, so nothing in the test would have
    asked for the fixture either.
    """
    recorder = Queued()
    monkeypatch.setattr(portal_handlers, "extract_invoice_file", recorder)
    yield recorder


@pytest.fixture
def queued_alerts(monkeypatch: pytest.MonkeyPatch) -> Iterator[Queued]:
    """The WhatsApp messages an interruption would send (RF-12)."""
    recorder = Queued()
    monkeypatch.setattr(notification_tasks, "send_whatsapp", recorder)
    yield recorder


@pytest.fixture
def queued_access_links(monkeypatch: pytest.MonkeyPatch) -> Iterator[Queued]:
    """The invitations and recovery links an access change would send.

    Recorded rather than sent, and the recording is the assertion: what a test
    checks is that the platform *decided* to send one, which is what the
    handler is responsible for. Whether Evolution API accepted it is the
    task's problem and the channel's test.
    """
    recorder = Queued()
    monkeypatch.setattr(notification_tasks, "send_access_link", recorder)
    yield recorder


@pytest.fixture(autouse=True)
def no_broker(queued_history: Queued, queued_alerts: Queued, queued_access_links: Queued) -> None:
    """No test in this suite ever reaches RabbitMQ."""
    return None


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
