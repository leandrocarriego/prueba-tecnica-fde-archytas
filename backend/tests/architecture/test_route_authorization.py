"""Every route states who may call it.

AGENTS.md: an endpoint cannot be added without deciding who calls it. So a route
is either declared public here — deliberately, in a list somebody has to edit —
or it declares an authentication dependency.

The rule is checked twice, because the two failures are different:

* **Declared** — the dependency tree FastAPI built for the route contains
  `get_current_user`. This sees the real wiring (`require_roles(...)` depends on
  `CurrentUser`, which depends on `get_current_user`), and it covers routes
  hidden from the OpenAPI schema.
* **Enforced** — an anonymous request to the route actually comes back 401. A
  dependency that is declared but overridden, or a handler that answers before
  its dependencies run, fails here and not above.
"""

from collections.abc import Callable, Iterable

import pytest
from fastapi.routing import APIRoute
from httpx import AsyncClient

from app.config import settings
from app.main import app
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.permissions import Level, Section

API_PREFIX = f"/api/{settings.API_VERSION}"

# The only routes allowed to answer without credentials, and why.
#
# Adding an entry here is a decision: it says "anyone on the internet may call
# this". Anything not listed must authenticate.
PUBLIC_ROUTES: dict[str, str] = {
    "/health": "Docker's healthcheck runs before anyone logs in",
    f"{API_PREFIX}/health": "the same endpoint, under the API prefix",
    f"{API_PREFIX}/auth/login": "nobody holds a session before logging in",
    f"{API_PREFIX}/auth/password-reset/request": "whoever lost their password has no session",
    f"{API_PREFIX}/auth/password-reset/{{token}}": "the single-use link is the credential",
    f"{API_PREFIX}/auth/invitation/{{token}}": "whoever was invited has no access yet",
}

# Path parameters are filled with a value that is syntactically valid and does
# not exist: the point is to reach the authorisation check, not the handler.
PATH_PARAMETERS: dict[str, str] = {
    "token": "not-a-real-token",
    "user_id": "999999",
    "run_id": "999999",
    "job_run_id": "999999",
    "product_id": "999999",
    "case_id": "999999",
    "rule_id": "999999",
}


class Endpoint:
    """One method of one route, with what it declares about its callers."""

    # Methods that change something. A route using one of these has to demand
    # the level that lets its caller change it, not merely see it.
    WRITING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    def __init__(
        self,
        method: str,
        path: str,
        *,
        protected: bool,
        role_checked: bool,
        section: Section | None = None,
        level: Level | None = None,
    ) -> None:
        self.method = method
        self.path = path
        # Resolves the caller's identity (`get_current_user`, directly or
        # through `require_section`).
        self.protected = protected
        # Restricts *which* identities, on top of the above.
        self.role_checked = role_checked
        # What it restricts them to: the section asked for, and how far in.
        self.section = section
        self.level = level

    @property
    def writes(self) -> bool:
        return self.method in self.WRITING_METHODS

    @property
    def is_declared_public(self) -> bool:
        return self.path in PUBLIC_ROUTES

    @property
    def url(self) -> str:
        """The path with its parameters filled in."""
        url = self.path
        for name, value in PATH_PARAMETERS.items():
            url = url.replace(f"{{{name}}}", value)
        return url

    def __repr__(self) -> str:
        return f"{self.method} {self.path}"


def dependency_calls(dependant: object) -> set[Callable[..., object]]:
    """Return every callable in a route's dependency tree, at any depth."""
    found: set[Callable[..., object]] = set()
    for dependency in getattr(dependant, "dependencies", []):
        if dependency.call is not None:
            found.add(dependency.call)
        found |= dependency_calls(dependency)
    return found


def _demanded_by(checkers: list[Callable[..., object]]) -> tuple[Section | None, Level | None]:
    """Read the section and level a route asked for.

    `require_section` returns a closure, so what it demands is not in any
    signature: it is in the cells the closure captured. Reading them is what
    lets this file check the *level* and not just the presence of a check —
    which is the difference between "somebody thought about authorisation" and
    "the right people get in".
    """
    for checker in checkers:
        captured = [cell.cell_contents for cell in (checker.__closure__ or ())]
        section = next((value for value in captured if isinstance(value, Section)), None)
        level = next((value for value in captured if isinstance(value, Level)), None)
        if section is not None:
            return section, level
    return None, None


def _walk(routes: Iterable[object], found: list[Endpoint]) -> None:
    """Collect the API endpoints of a router tree.

    FastAPI 0.137 stopped flattening `include_router` into `app.routes`: a
    mounted router now appears as a single node that expands on demand. Both
    shapes are handled, so the check keeps working across that change instead of
    silently inspecting nothing.
    """
    for route in routes:
        expand = getattr(route, "effective_candidates", None)
        if callable(expand):
            _walk(expand(), found)
            continue
        if not isinstance(getattr(route, "original_route", route), APIRoute):
            # `/docs`, `/redoc` and `/openapi.json` are plain Starlette routes.
            continue
        calls = dependency_calls(getattr(route, "dependant", None))
        protected = get_current_user in calls
        checkers = [
            call
            for call in calls
            if getattr(call, "__qualname__", "").startswith("require_section")
        ]
        section, level = _demanded_by(checkers)
        found.extend(
            Endpoint(
                method,
                route.path,
                protected=protected,
                role_checked=bool(checkers),
                section=section,
                level=level,
            )
            for method in sorted(route.methods)
        )


def endpoints() -> list[Endpoint]:
    """Every endpoint the application serves, including the ones hidden from the schema."""
    found: list[Endpoint] = []
    _walk(app.routes, found)
    return sorted(found, key=lambda endpoint: (endpoint.path, endpoint.method))


ENDPOINTS = endpoints()


@pytest.mark.unit
class TestRoutesDeclareAuthorization:
    """The wiring: no endpoint gets access by accident."""

    def test_the_application_has_routes(self) -> None:
        """Guard against a check that passes because it inspected nothing."""
        assert ENDPOINTS

    @pytest.mark.parametrize("endpoint", ENDPOINTS, ids=repr)
    def test_endpoint_declares_its_authorization(self, endpoint: Endpoint) -> None:
        """Either the route is listed as public, or it authenticates its caller."""
        assert endpoint.is_declared_public or endpoint.protected, (
            f"{endpoint} answers without checking who is calling. Add an authentication "
            "or role dependency, or declare the route in PUBLIC_ROUTES with the reason "
            "it is public."
        )

    def test_public_routes_are_all_real_routes(self) -> None:
        """A stale entry would exempt nothing, or worse, the wrong path."""
        # Arrange
        served = {endpoint.path for endpoint in ENDPOINTS}

        # Assert
        assert set(PUBLIC_ROUTES) <= served

    def test_public_routes_are_actually_public(self) -> None:
        """The list says these need no credentials, so they must not require any."""
        # Act
        contradictions = [
            repr(endpoint)
            for endpoint in ENDPOINTS
            if endpoint.is_declared_public and endpoint.protected
        ]

        # Assert
        assert not contradictions, (
            f"Listed as public but authenticating their caller: {contradictions}. "
            "Remove them from PUBLIC_ROUTES."
        )

    @pytest.mark.parametrize(
        "endpoint",
        [endpoint for endpoint in ENDPOINTS if endpoint.writes and endpoint.role_checked],
        ids=repr,
    )
    def test_a_route_that_writes_demands_the_level_to_write(self, endpoint: Endpoint) -> None:
        """Declaring a section is not enough: a change needs the level to change.

        This is the second half of the authorisation rule. Gating a `POST` with
        the level that only lets somebody *look* would hand every reader a
        write, and nothing else in the suite would notice: the route answers
        200 to exactly the people it was supposed to refuse.
        """
        assert endpoint.level is Level.WRITE, (
            f"{endpoint} changes something but only demands {endpoint.level!r} on "
            f"{endpoint.section!r}. Pass Level.WRITE to require_section."
        )

    def test_user_administration_carries_a_role_check(self) -> None:
        """Authentication is not authorisation.

        `get_current_user` alone would let anyone with a session hand out
        accounts and change roles, so every write under `/users` must also
        declare which roles may do it.
        """
        # Act
        unrestricted = [
            repr(endpoint)
            for endpoint in ENDPOINTS
            if endpoint.path.startswith(f"{API_PREFIX}/users")
            and endpoint.method in {"POST", "PATCH", "PUT", "DELETE"}
            and not endpoint.role_checked
        ]

        # Assert
        assert not unrestricted, f"Administration routes without a role check: {unrestricted}"


@pytest.mark.integration
@pytest.mark.database
class TestRoutesEnforceAuthorization:
    """The behaviour: what an anonymous caller actually gets back."""

    @pytest.mark.parametrize(
        "endpoint",
        [endpoint for endpoint in ENDPOINTS if not endpoint.is_declared_public],
        ids=repr,
    )
    async def test_protected_endpoint_rejects_an_anonymous_caller(
        self, endpoint: Endpoint, client: AsyncClient
    ) -> None:
        """No token, no answer: 401 before the handler ever runs."""
        # Act
        response = await client.request(endpoint.method, endpoint.url, json={})

        # Assert
        assert response.status_code == 401, (
            f"{endpoint} answered {response.status_code} to a request with no credentials."
        )

    @pytest.mark.parametrize(
        "endpoint",
        [endpoint for endpoint in ENDPOINTS if endpoint.is_declared_public],
        ids=repr,
    )
    async def test_public_endpoint_admits_an_anonymous_caller(
        self, endpoint: Endpoint, client: AsyncClient
    ) -> None:
        """A public route may reject the *payload*, never the caller.

        The body sent here is empty, so 422 is a perfectly good answer: it
        proves the request got past authentication.
        """
        # Act
        response = await client.request(endpoint.method, endpoint.url, json={})

        # Assert
        assert response.status_code != 401, f"{endpoint} is listed as public but asked for a token."
