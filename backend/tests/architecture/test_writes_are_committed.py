"""A route that writes has to commit, and nothing else will do it for it.

`app/database.py::get_session` yields a session and closes it:

    async with SessionFactory() as session:
        yield session

There is no commit in there, and closing an `AsyncSession` discards whatever
transaction is open. So a service method reached from a `POST`, `PUT`, `PATCH`
or `DELETE` that only ever `flush()`es answers **200 and persists nothing**. The
route looks like it worked, the caller gets an id back, and the database never
hears about it.

Why the suite cannot see this on its own, and therefore why this file exists.
`tests/conftest.py` wraps each test in an outer transaction and hands the HTTP
client *the test's own session* through a `get_session` override — its docstring
says so, and says why: "the services commit on their own". Under that override a
request's writes are visible to the test that made them **whether or not
anything committed**, because there is only one session and it is never closed
mid-test. Every integration test in the repository would pass over a route that
loses its data.

That assumption — services commit on their own — is load-bearing for the whole
isolation strategy, and until now nothing checked it. Two routes had already
stopped honouring it: correcting a value by hand and undoing that correction,
which is to say both write routes of feature 003.

So this is a static check, like `test_module_boundaries.py`: it reads the
routers, finds the service method behind each writing route, and asks whether
that method commits. It cannot run the code, which is the point — the defect it
looks for is invisible at runtime under the test harness.
"""

import re
from pathlib import Path

import pytest

import app

MODULES = Path(app.__file__).resolve().parent / "modules"

# `@router.post(`, `@corrections_router.delete(` — any router object, any of the
# four verbs that change something. `get` is deliberately absent: a read has
# nothing to commit.
WRITING_ROUTE = re.compile(r"^@\w+\.(?P<verb>post|put|patch|delete)\(", re.MULTILINE)
# The handler that decorator belongs to, and everything up to the next one at
# column zero — near enough its body for reading the calls it makes.
HANDLER = re.compile(r"^async def (?P<name>\w+)\(", re.MULTILINE)
# `service.apply_correction(`, `svc.resolve_case(` — the call itself. The
# receiver is not checked: a handler holds one service, and a false positive
# here costs a lookup that finds nothing.
A_CALL = re.compile(r"\b\w+\.(?P<method>[a-z]\w*)\(")

COMMITS = re.compile(r"\.commit\(\)")
# Whether the method changes anything at all. Not every writing **verb** writes:
# `POST` is also how a body-carrying question is asked, and `preview_alias` in
# `purchases` counts the invoices an assignment *would* resolve without touching
# one. Demanding a commit there would be the rule being wrong, not the code.
#
# So the shapes that put something into the session: a flush, an `add`/`insert`/
# `upsert`/`delete`/`set_`/`touch_` on a repository, or publishing an event —
# which runs its handlers inside this transaction and is exactly how a manual
# change reaches the log.
WRITES = re.compile(
    r"\.flush\(\)|\.(?:add|insert|upsert|delete|set|touch|save|remove|mark)\w*\(|events\.publish\("
)


def method_bodies(source: str) -> dict[str, str]:
    """Every `async def` of a module's service, by name.

    Sliced by indentation rather than parsed: a method ends where the next one
    at the same level starts. Good enough to answer whether the word `commit`
    appears inside it, which is the only question asked here.
    """
    found: dict[str, str] = {}
    starts = [
        (match.start(), match["name"])
        for match in re.finditer(r"^    (?:async )?def (?P<name>\w+)\(", source, re.MULTILINE)
    ]
    for index, (at, name) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(source)
        found[name] = source[at:end]
    return found


def reaches(
    what: re.Pattern[str],
    name: str,
    bodies: dict[str, str],
    seen: frozenset[str] = frozenset(),
) -> bool:
    """Whether that method does it, itself or through what it calls.

    One name may not be the whole answer: a method that hands the work to
    another of its own class writes, or commits, just as honestly. `seen` is
    what keeps a pair of methods that call each other from becoming a stack
    overflow instead of a test failure.
    """
    body = bodies.get(name)
    if body is None or name in seen:
        return False
    if what.search(body):
        return True
    return any(
        reaches(what, called["method"], bodies, seen | {name})
        for called in A_CALL.finditer(body)
        if called["method"] != name
    )


def writing_routes() -> list[tuple[str, str, str]]:
    """Every writing route in the application, as (module, verb, handler)."""
    routes = []
    for module in sorted(MODULES.iterdir()):
        source_file = module / "routes.py"
        if not source_file.is_file():
            continue
        source = source_file.read_text(encoding="utf-8")
        for route in WRITING_ROUTE.finditer(source):
            handler = HANDLER.search(source, route.end())
            if handler is not None:
                routes.append((module.name, route["verb"], handler["name"]))
    return routes


@pytest.mark.unit
class TestEveryWriteIsCommitted:
    """The invariant `tests/conftest.py` assumes and nothing used to verify."""

    def test_there_are_writing_routes_to_check(self) -> None:
        """A parse that finds nothing would make this whole file green and idle.

        The application has writing routes in several modules; if this ever
        returns nothing, the shape of the routers moved and the rule below
        stopped applying rather than started passing.
        """
        # Arrange / Act
        routes = writing_routes()

        # Assert
        assert len(routes) > 5, (
            "no writing routes were found in app/modules/*/routes.py. This file "
            "reads `@router.post(` and the `async def` under it: the routers are "
            "written some other way now, and the rule is checking nothing."
        )

    @pytest.mark.parametrize(
        ("module", "verb", "handler"),
        writing_routes(),
        ids=lambda value: str(value),
    )
    def test_the_service_behind_it_commits(self, module: str, verb: str, handler: str) -> None:
        """What a writing route calls has to close its transaction.

        Nothing downstream will: `get_session` closes the session without
        committing, and the event bus does not commit either — a handler runs
        inside the publisher's transaction on purpose (`GEN-09`).
        """
        # Arrange
        source = (MODULES / module / "routes.py").read_text(encoding="utf-8")
        service_file = MODULES / module / "service.py"
        if not service_file.is_file():
            pytest.skip(f"{module} has no service.py")
        bodies = method_bodies(service_file.read_text(encoding="utf-8"))

        at = source.index(f"async def {handler}(")
        following = HANDLER.search(source, at + 1)
        body = source[at : following.start() if following else len(source)]

        # Act — the service methods this handler reaches for, if any are ours
        called = [
            name for name in {match["method"] for match in A_CALL.finditer(body)} if name in bodies
        ]

        # Assert
        if not called:
            pytest.skip(f"{handler} calls no method of {module}'s service")
        writing = [name for name in called if reaches(WRITES, name, bodies)]
        if not writing:
            pytest.skip(f"{handler} writes nothing: a question asked with a body")
        assert any(reaches(COMMITS, name, bodies) for name in writing), (
            f"{verb.upper()} handled by {module}.routes.{handler} reaches "
            f"{', '.join(sorted(writing))} in {module}/service.py, which writes and "
            "never commits. `get_session` closes the session without committing, so "
            "this route answers 200 and persists nothing. No integration test can "
            "see it: the HTTP client shares the test's session, so the write is "
            "visible to whoever made it either way (tests/conftest.py)."
        )
