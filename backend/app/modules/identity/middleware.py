"""Recording the refusals nobody else can record.

A 403 is raised by a dependency, before the handler runs — and the exception
that carries it aborts the transaction that would have stored the row. So the
one place that can write it down is *after* the response exists, which is what
a middleware is.

It lives inside `identity` and not in `main.py` on purpose. The test that
guards module boundaries only walks `app/modules/`, so putting this logic in
the composition root would be legal and would still make `main.py` the first
place in the project with domain logic outside a module. `main.py` registers
it; the knowledge of what an access event is stays here. It is the same shape
as `dependencies.py` — composition that lives in the module and is mounted
from outside — for the same reason.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status

from app.database import SessionFactory
from app.logging import get_logger
from app.modules.identity.service import IdentityService

logger = get_logger(__name__)

NextCall = Callable[[Request], Awaitable[Response]]

# What a refusal is recorded as when the dependency did not say more. It can
# happen if something other than `require_section` answers 403.
UNSPECIFIED = "FORBIDDEN"


async def record_refusals(request: Request, call_next: NextCall) -> Response:
    """Write down every request that was answered with a 403.

    Uses a session of its own, not the request's: by the time this runs, the
    request's transaction has been rolled back by the exception that produced
    the refusal. Writing here is the only way the row survives.

    A failure to record must never turn a 403 into a 500: the caller already
    got the right answer, and losing the line is worth less than breaking the
    response.
    """
    response = await call_next(request)
    if response.status_code != status.HTTP_403_FORBIDDEN:
        return response

    user_id = getattr(request.state, "current_user_id", None)
    reason = getattr(request.state, "denied_reason", UNSPECIFIED)
    resource = f"{request.method} {request.url.path}"

    try:
        async with SessionFactory() as session:
            await IdentityService(session).record_denied_access(
                user_id=user_id, resource=resource, reason=reason
            )
    except Exception:  # noqa: BLE001 - a lost log line must not break a reply
        logger.exception("Could not record a refused request", extra={"resource": resource})
    return response
