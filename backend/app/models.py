"""Model registry.

Importing this module registers every mapped class with the declarative base, so
SQLAlchemy can resolve relationships and Alembic can autogenerate migrations.
Modules must never import models from each other: this file exists for the mapper,
not as a shortcut across module boundaries.

Every module adds its line here in the same commit as the migration that creates
its tables — `alembic check` runs in CI and fails on a model that no migration
accounts for.
"""

from app.modules.catalog.models import (
    CatalogSetting,
    Correction,
    PricePoint,
    PriceSource,
    Product,
    ProductPrice,
    ProductStatus,
)
from app.modules.identity.models import (
    AccessEvent,
    AccessEventKind,
    AccessSetting,
    CredentialToken,
    Session,
    SessionRevocation,
    TokenPurpose,
    User,
    UserPassword,
    UserRole,
)
from app.modules.ingestion.models import (
    PriceHistoryRow,
    PriceRow,
    ResolutionRuleProjection,
    RowStatus,
)
from app.modules.operations.models import AuditEntry, JobRun, JobStatus, Parameter
from app.modules.portal.models import PortalDocument
from app.modules.triage.models import CaseStatus, ExceptionCase, ResolutionRule

__all__: list[str] = [
    "AccessEvent",
    "AccessEventKind",
    "AccessSetting",
    "AuditEntry",
    "CaseStatus",
    "CatalogSetting",
    "Correction",
    "CredentialToken",
    "ExceptionCase",
    "JobRun",
    "JobStatus",
    "Parameter",
    "PriceHistoryRow",
    "PricePoint",
    "PriceRow",
    "PriceSource",
    "PortalDocument",
    "Product",
    "ProductPrice",
    "ProductStatus",
    "ResolutionRule",
    "ResolutionRuleProjection",
    "RowStatus",
    "Session",
    "SessionRevocation",
    "TokenPurpose",
    "User",
    "UserPassword",
    "UserRole",
]
