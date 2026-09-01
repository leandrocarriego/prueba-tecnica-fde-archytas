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

    **Retried by default, because most of these are bad timing.** The portal
    account is shared with the client's own staff and its session drops, so an
    extraction that failed once very often succeeds a few minutes later.
    """


class PortalShapeError(ExtractionError):
    """The page is not shaped the way this platform reads it.

    A screen without the columns the parser names is **not** bad timing: it will
    fail the same way in five minutes and in five hours, so it is reported at
    once instead of being retried. Retrying a defect only repeats it, and while
    the retries run the extraction stays `RUNNING` — which blocks the next one
    and shows the owner a «Corriendo ahora» that will never end.

    That is not a hypothesis: the sales section was published with `Cod. Venta`
    and `Cant.` while its parser asked for `Codigo` and `Cantidad`, and every
    run since the platform was deployed either wedged or was eventually
    swept away with «its worker never came back» — a sentence that names the
    symptom and hides the cause.
    """
