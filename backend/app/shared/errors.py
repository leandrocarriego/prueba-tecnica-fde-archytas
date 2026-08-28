"""Domain errors.

These are transport-agnostic: `app.main` maps them to status codes when it
builds the application. Raising an `HTTPException` from a service is a boundary
violation and is rejected in review.
"""


class DomainError(Exception):
    """Base class for every expected, business-level failure."""

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    """The requested entity does not exist."""


class ConflictError(DomainError):
    """The operation conflicts with the current state (duplicate, race)."""


class ValidationError(DomainError):
    """The input is well-formed but not acceptable for this operation."""


class AuthenticationError(DomainError):
    """The caller could not be identified."""


class PermissionDeniedError(DomainError):
    """The caller is known but not allowed to perform this operation."""


class ExtractionError(DomainError):
    """The portal could not be read as expected.

    This is a technical failure of the extraction, not a data problem. Data that
    cannot be interpreted is quarantined instead of raised.
    """
