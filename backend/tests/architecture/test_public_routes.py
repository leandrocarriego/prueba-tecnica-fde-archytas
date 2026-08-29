"""Every authentication page is reachable without a session.

The pages under `frontend/app/(auth)/` are, by definition, the ones visited by
somebody who **cannot** log in: an invitation, a recovery link, the login form
itself. Behind the route guard they redirect to a login that person cannot
pass, at the only moment they needed the link.

That is what happened. `proxy.ts` listed `/login` and `/reset-password` as
public while the links that go out by WhatsApp point at `/invitacion/<token>`
and `/recuperar/<token>`, so the first access to the platform bounced to the
login page — every time, for everybody.

Why a Python test for a TypeScript file: the frontend has no test runner, and
adding one to hold a two-line list is a bigger change than the rule deserves.
The check is static — the same shape as the other tests in this package — and
it fails for the right reason, which is what makes it worth having. If a
frontend suite ever exists, this belongs there.
"""

import re
from pathlib import Path

import pytest

import app

REPOSITORY_ROOT = Path(app.__file__).resolve().parents[2]
AUTH_PAGES = REPOSITORY_ROOT / "frontend" / "app" / "(auth)"
PROXY = REPOSITORY_ROOT / "frontend" / "proxy.ts"

# `const publicPaths = [ ... ]`, and the matcher's negative lookahead.
PUBLIC_PATHS = re.compile(r"const publicPaths\s*=\s*\[(.*?)\]", re.DOTALL)
MATCHER = re.compile(r"'/\(\(\?!([^)]*)\)\.\*\)'")


def auth_routes() -> list[str]:
    """The first path segment of every page under `(auth)`."""
    return sorted({page.relative_to(AUTH_PAGES).parts[0] for page in AUTH_PAGES.rglob("page.tsx")})


@pytest.fixture(scope="module")
def proxy_source() -> str:
    return PROXY.read_text(encoding="utf-8")


@pytest.mark.unit
class TestAuthenticationPagesArePublic:
    """The route guard and the pages it guards, kept in step."""

    def test_there_are_auth_pages_to_check(self) -> None:
        """A rename that empties the directory must not quietly pass this file."""
        assert auth_routes(), f"no page.tsx under {AUTH_PAGES}"

    @pytest.mark.parametrize("route", auth_routes())
    def test_the_guard_lets_it_through(self, route: str, proxy_source: str) -> None:
        """It is in `publicPaths`, so the guard returns before asking for a token."""
        listed = PUBLIC_PATHS.search(proxy_source)
        assert listed is not None, "publicPaths not found in proxy.ts"
        assert f"'/{route}'" in listed.group(1), (
            f"/{route} is an authentication page and publicPaths does not list it: "
            "whoever opens its link is bounced to a login they cannot pass yet."
        )

    @pytest.mark.parametrize("route", auth_routes())
    def test_the_matcher_does_not_run_on_it(self, route: str, proxy_source: str) -> None:
        """And the matcher skips it, so the guard never runs at all."""
        excluded = MATCHER.search(proxy_source)
        assert excluded is not None, "matcher not found in proxy.ts"
        assert route in excluded.group(1).split("|"), (
            f"/{route} is an authentication page and the matcher still runs on it."
        )
