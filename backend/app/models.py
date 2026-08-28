"""Model registry.

Importing this module registers every mapped class with the declarative base, so
SQLAlchemy can resolve relationships and Alembic can autogenerate migrations.
Modules must never import models from each other: this file exists for the mapper,
not as a shortcut across module boundaries.

It is empty because no domain module has landed yet. Each one adds a line here
when it does, in the same commit as the migration that creates its tables —
`alembic check` runs in CI and fails on a model that no migration accounts for.
"""

__all__: list[str] = []
