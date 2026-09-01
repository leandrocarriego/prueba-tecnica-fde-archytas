"""Composition root.

The only place that knows every module. It builds the FastAPI application,
registers each module's routers explicitly, and translates the domain errors of
`app.shared.errors` into HTTP status codes so that no service ever has to raise
an `HTTPException`.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Importing the registry binds every mapped class to `Base.metadata` so
# SQLAlchemy can resolve relationships. It is not a shortcut across module
# boundaries: nothing here reads another module's models.
from app import models  # noqa: F401
from app.config import settings
from app.database import engine
from app.logging import get_logger, setup_logging
from app.modules.catalog.routes import (
    catalog_dashboard_router,
    categories_router,
    corrections_router,
    products_router,
)
from app.modules.catalog.routes import router as catalog_router
from app.modules.identity.middleware import record_refusals
from app.modules.identity.routes import access_log_router, auth_router, users_router
from app.modules.messaging.routes import router as messages_router
from app.modules.notifications.routes import router as alerts_router
from app.modules.operations.routes import health_router, price_updates_router
from app.modules.operations.routes import router as operations_router
from app.modules.purchases.routes import (
    aliases_router,
    calendar_router,
    incidents_router,
    invoices_router,
    orders_router,
    payments_router,
    purchases_dashboard_router,
    receipts_router,
    review_router,
    suppliers_router,
)
from app.modules.sales.routes import dashboard_router as sales_dashboard_router
from app.modules.sales.routes import router as sales_router
from app.modules.triage.routes import router as triage_router
from app.shared.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    ExtractionError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.shared.events import discover_handlers
from app.shared.live import bus

setup_logging()
logger = get_logger(__name__)

API_PREFIX = f"/api/{settings.API_VERSION}"

# The contract between the domain and HTTP. `DomainError` is the catch-all, and
# `_status_for` walks the class hierarchy, so a future subclass inherits the
# status of its parent instead of silently falling back to 400.
DOMAIN_ERROR_STATUS: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    ExtractionError: status.HTTP_502_BAD_GATEWAY,
    DomainError: status.HTTP_400_BAD_REQUEST,
}

# One entry per tag actually mounted below. A domain module adds its own when
# it lands, together with its routers.
TAGS_METADATA: list[dict[str, str]] = [
    {"name": "Health", "description": "Liveness of the service and its dependencies."},
    {"name": "Auth", "description": "Logging in, the caller's own account, password recovery."},
    {"name": "Users", "description": "Accounts and roles. The owner's surface."},
    {"name": "Operations", "description": "Background runs and the business parameters."},
    {"name": "Prices", "description": "The supplier's price list and how each price evolved."},
    {
        "name": "Corrections",
        "description": "Correcting a value by hand, and undoing a correction.",
    },
    {
        "name": "Price updates",
        "description": "The state of the price update, asking for one, and its settings.",
    },
    {
        "name": "Categories",
        "description": "The rubros of the catalog and the written forms that resolve to them.",
    },
    {
        "name": "Invoices",
        "description": "Purchase invoices, what their documents said, and what is held.",
    },
    {
        "name": "Suppliers",
        "description": "The register of suppliers and the ways their names arrive written.",
    },
    {"name": "Payments", "description": "What was paid on each invoice, and what is still owed."},
    {
        "name": "Receipts",
        "description": "Reception receipts and the invoices that fell due without one.",
    },
    {"name": "Calendar", "description": "The due dates, on the day they fall."},
    {"name": "Purchase orders", "description": "What was ordered, and what has not moved."},
    {"name": "Alerts", "description": "Who the platform tells what, and on which number."},
    {"name": "Messages", "description": "The inbox of the portal, with a state and an owner."},
    {"name": "Sales", "description": "The sales records, and the ones no indicator may add."},
    {
        "name": "Dashboard",
        "description": "How the business is doing, and what each number left out.",
    },
    {
        "name": "Triage",
        "description": "What the pipeline set aside, and the rules learned from it.",
    },
]


def _status_for(error: DomainError) -> int:
    """Return the status code declared for this error, or for its closest parent."""
    for candidate in type(error).__mro__:
        if candidate in DOMAIN_ERROR_STATUS:
            return DOMAIN_ERROR_STATUS[candidate]
    return status.HTTP_400_BAD_REQUEST


def _error_body(error_type: str, message: str, details: object) -> dict[str, object]:
    """Build the one error envelope every failure of this API uses."""
    return {
        "error": {
            "type": error_type,
            "message": message,
            # `details` carries whatever the raiser attached (ids, keys), so it
            # is encoded rather than trusted to be JSON-serialisable already.
            "details": jsonable_encoder(details),
        }
    }


async def handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    """Map a domain error to its HTTP status code."""
    if not isinstance(exc, DomainError):  # pragma: no cover - registered per error type
        raise exc
    status_code = _status_for(exc)
    logger.warning(
        "Domain error",
        extra={
            "path": request.url.path,
            "error_type": type(exc).__name__,
            "status_code": status_code,
        },
    )
    return JSONResponse(
        status_code=status_code,
        content=_error_body(type(exc).__name__, exc.message, exc.details),
    )


async def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    """Wrap FastAPI's own errors in the same envelope.

    The authentication dependencies raise `HTTPException` because they are HTTP
    machinery, not domain logic. Clients should still see one error shape.
    """
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover - defensive
        raise exc
    try:
        error_type = HTTPStatus(exc.status_code).phrase
    except ValueError:
        error_type = "HTTPError"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(error_type, str(exc.detail), {}),
        headers=exc.headers,
    )


async def handle_request_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Report a malformed request in the same envelope as everything else."""
    if not isinstance(exc, RequestValidationError):  # pragma: no cover - defensive
        raise exc
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_body(
            "RequestValidationError",
            "The request payload is not valid",
            {"errors": exc.errors()},
        ),
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Log the boundaries of the process and release the connection pool.

    No `create_all` here on purpose: the schema belongs to Alembic. Creating
    tables from the application would let the models and the migrations drift
    apart, and the first environment to notice would be production.
    """
    logger.info("Starting %s (%s) on %s", settings.PROJECT_NAME, settings.ENVIRONMENT, API_PREFIX)
    # One listening connection per worker, opened here because it belongs to the
    # process and not to a module — the same reason the routers are mounted
    # here (`GEN-04`). If it cannot be opened the app still serves: the calendar
    # stops updating on its own and nothing else changes.
    await bus.start()
    yield
    await bus.stop()
    await engine.dispose()
    logger.info("Shutdown complete")


def register_event_handlers() -> None:
    """Import every module's `handlers.py` so its subscriptions exist.

    Modules do not import each other: what one publishes, another reacts to
    through `app.shared.events`. A subscription that is never imported is a
    reaction that silently does not happen, so discovery runs here, in the
    composition root, and is logged.
    """
    registered = discover_handlers()
    logger.info("Event handlers registered: %s", ", ".join(registered) or "none")


def register_routers(application: FastAPI) -> None:
    """Mount every router. Adding a module means adding a line here."""
    application.include_router(health_router, prefix=API_PREFIX)

    # Docker's healthcheck runs inside the container and has no reason to know
    # the API version, so health answers at the root as well. Hidden from the
    # schema: it is the same endpoint, and documenting it twice would only
    # collide on operation ids.
    application.include_router(health_router, include_in_schema=False)

    application.include_router(auth_router, prefix=API_PREFIX)
    application.include_router(users_router, prefix=API_PREFIX)
    application.include_router(access_log_router, prefix=API_PREFIX)
    application.include_router(operations_router, prefix=API_PREFIX)
    application.include_router(price_updates_router, prefix=API_PREFIX)
    application.include_router(catalog_router, prefix=API_PREFIX)
    application.include_router(corrections_router, prefix=API_PREFIX)
    application.include_router(categories_router, prefix=API_PREFIX)
    application.include_router(products_router, prefix=API_PREFIX)
    application.include_router(triage_router, prefix=API_PREFIX)
    application.include_router(invoices_router, prefix=API_PREFIX)
    application.include_router(suppliers_router, prefix=API_PREFIX)
    application.include_router(review_router, prefix=API_PREFIX)
    application.include_router(aliases_router, prefix=API_PREFIX)
    application.include_router(payments_router, prefix=API_PREFIX)
    application.include_router(receipts_router, prefix=API_PREFIX)
    application.include_router(incidents_router, prefix=API_PREFIX)
    application.include_router(calendar_router, prefix=API_PREFIX)
    application.include_router(orders_router, prefix=API_PREFIX)
    application.include_router(messages_router, prefix=API_PREFIX)
    application.include_router(alerts_router, prefix=API_PREFIX)
    application.include_router(sales_router, prefix=API_PREFIX)
    application.include_router(sales_dashboard_router, prefix=API_PREFIX)
    application.include_router(catalog_dashboard_router, prefix=API_PREFIX)
    application.include_router(purchases_dashboard_router, prefix=API_PREFIX)


def register_exception_handlers(application: FastAPI) -> None:
    """Wire the domain errors, and FastAPI's own, to the shared error envelope."""
    for error_type in DOMAIN_ERROR_STATUS:
        application.add_exception_handler(error_type, handle_domain_error)
    application.add_exception_handler(StarletteHTTPException, handle_http_exception)
    application.add_exception_handler(RequestValidationError, handle_request_validation_error)


def create_app() -> FastAPI:
    """Build the application: middleware, routers and error handling."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Plataforma de Ferretería Industrial Cordillera.",
        version=settings.API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    # Every 403 leaves a line for the owner (RF-14). Registered here because
    # `main.py` is the composition root; written in `identity`, because what an
    # access event is belongs to that module.
    application.middleware("http")(record_refusals)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_event_handlers()
    register_routers(application)
    register_exception_handlers(application)
    return application


app = create_app()
