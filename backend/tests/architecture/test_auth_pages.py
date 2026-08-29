"""The two static rules that hold the authentication pages together.

Both were found by using the deployed site, and both are checked here because
the frontend has no test runner: adding one to hold a couple of rules is a
bigger change than they deserve. The checks are static, the same shape as the
rest of this package, and they fail for the right reason. If a frontend suite
ever exists, they belong there.

---

**One. Every authentication page is reachable without a session.**

The pages under `frontend/app/(auth)/` are, by definition, the ones visited by
somebody who **cannot** log in: an invitation, a recovery link, the login form
itself. Behind the route guard they redirect to a login that person cannot
pass, at the only moment they needed the link.

That is what happened. `proxy.ts` listed `/login` and `/reset-password` as
public while the links that go out by WhatsApp point at `/invitacion/<token>`
and `/recuperar/<token>`, so the first access to the platform bounced to the
login page — every time, for everybody.

**Two. A page that redeems a single-use link stops offering the action.**

The recovery page saved the password, said so, and left the form exactly where
it was — same two fields, same "Guardar la clave". Pressing it again spends
nothing and answers "el enlace no sirve", which reads as *your password was
never saved*. It was.
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


# Pages that redeem a token: their action works once, so the form must not
# survive it. `mi-cuenta` deliberately does not qualify — changing your own
# password is something you may do again tomorrow.
SINGLE_USE = re.compile(r"singleUse")


def token_pages() -> list[Path]:
    """Every `(auth)` page that takes a token in its path."""
    return sorted(page for page in AUTH_PAGES.rglob("[[]token[]]/page.tsx"))


@pytest.mark.unit
class TestASingleUseLinkStopsOfferingItself:
    """A link that is spent on use, and a screen that says so."""

    def test_there_are_token_pages_to_check(self) -> None:
        """A rename that empties the search must not quietly pass this file."""
        assert token_pages(), f"no [token]/page.tsx under {AUTH_PAGES}"

    @pytest.mark.parametrize("page", token_pages(), ids=lambda p: p.parts[-3])
    def test_it_asks_the_form_to_go_away(self, page: Path) -> None:
        """Otherwise it offers an action that can no longer succeed."""
        assert SINGLE_USE.search(page.read_text(encoding="utf-8")), (
            f"{page.parts[-3]} redeems a single-use token and does not pass `singleUse`: "
            "after saving, the form stays on screen offering to save again."
        )
