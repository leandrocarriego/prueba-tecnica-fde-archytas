"""Model registry.

Importing this module registers every mapped class with the declarative base, so
SQLAlchemy can resolve relationships and Alembic can autogenerate migrations.
Modules must never import models from each other: this file exists for the mapper,
not as a shortcut across module boundaries.
"""

from app.modules.identity.models import PasswordResetToken, User, UserPassword
from app.modules.operations.models import JobRun, Parameter

__all__ = [
    "JobRun",
    "Parameter",
    "PasswordResetToken",
    "User",
    "UserPassword",
]
