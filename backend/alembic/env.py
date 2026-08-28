"""Alembic environment for the Cordillera platform.

The application runs SQLAlchemy 2.0 in async mode over asyncpg, so migrations
run through an async engine and hand a synchronous connection to Alembic via
`connection.run_sync(...)`.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

# Importing the model registry binds every mapped class to `Base.metadata`, which
# is what autogenerate diffs against. Without it Alembic would only see whichever
# models happened to be imported already, and would propose dropping the rest.
# Modules never import each other's models: this registry exists for the mapper,
# not as a shortcut across module boundaries.
import app.models  # noqa: F401
from app.config import settings
from app.database import Base

config = context.config

# The database URL comes from the application settings, never from alembic.ini:
# one source of truth, and no credentials committed to the repository.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# The extraction pipeline is partitioned across these schemas (raw -> staging -> core,
# plus operations for jobs, exceptions, parameters and audit). Identity tables stay in
# the default `public` schema.
PIPELINE_SCHEMAS = ("raw", "staging", "core", "operations")

# Schemas Alembic is allowed to see. Anything else (extension-owned objects,
# information_schema, ...) is ignored so autogenerate never proposes dropping
# objects this project does not manage.
MANAGED_SCHEMAS = frozenset({None, "public", *PIPELINE_SCHEMAS})


def include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    """Restrict reflection to the schemas this project owns.

    `include_schemas=True` makes autogenerate reflect *every* schema in the
    database, so without this filter a stray schema would show up as a pile of
    spurious `drop_table` operations.
    """
    if type_ == "schema":
        return name in MANAGED_SCHEMAS
    return True


def create_pipeline_schemas(connection: Connection) -> None:
    """Create the pipeline schemas if they are missing.

    This runs BEFORE the migration context is configured, and that ordering is
    the point. As soon as the context is configured Alembic reads (and creates)
    its version table, and the very first statement of a migration touches a
    schema-qualified table. On a brand-new database those schemas do not exist
    yet, so PostgreSQL raises `InvalidSchemaNameError` before any migration gets
    the chance to create them - a chicken-and-egg that only shows up on a
    from-scratch `alembic upgrade head`.

    Creating them here is idempotent (`CREATE SCHEMA IF NOT EXISTS`) and safe to
    repeat on every run. The initial migration also creates them, so a database
    provisioned by other means ends up in the same state.
    """
    for schema in PIPELINE_SCHEMAS:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))


def run_migrations_offline() -> None:
    """Emit the migrations as SQL, without connecting to a database."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=include_name,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        # Same reasoning as `create_pipeline_schemas`, expressed as SQL at the top
        # of the generated script.
        for schema in PIPELINE_SCHEMAS:
            context.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure Alembic against a synchronous connection and run the migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Open the async engine and drive the migrations through `run_sync`."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            # Committed on its own so the schemas are already there when the
            # migration transaction opens, whatever that transaction does next.
            await connection.run_sync(create_pipeline_schemas)
            await connection.commit()
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
