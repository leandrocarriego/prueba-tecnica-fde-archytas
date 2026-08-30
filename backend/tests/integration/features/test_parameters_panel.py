"""H1 over HTTP: the owner turns the knobs of the system, and nobody else reaches them.

Task 8 of `docs/specs/003-system-control/tasks.md`, covering RF-01 to RF-08.

The `Developer`'s own `TestParameters` — in `test_operations_feature.py` — already
exercises the service seam: that a change is stored, that a bad one is refused,
that a decimal keeps its cents. What is here is the other half, and it is
deliberately not the same half:

* the **exact edges** of every range, driven from `app.shared.parameters` so a
  parameter added to the catalog tomorrow joins the grid without anybody
  remembering to come back here;
* the **authorisation of the two routes**, exercised with a real token per role
  rather than by trusting the decorator;
* the **starting values the client signed**, read through the API on a database
  where the table is still empty, which is the only way RF-04 is a fact and not
  a comment;
* the **road a parameter takes to the module that obeys it**, for the one
  parameter of the panel whose consumer is on the other side of a module
  boundary (`access.session_idle_minutes` → `identity`, over
  `BusinessParameterChanged`). RF-07 says "without any further intervention",
  and a projection nobody feeds is exactly how that promise breaks in silence.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app
from app.modules.identity.models import Session as UserSession
from app.modules.identity.models import User
from app.modules.identity.service import IdentityService
from app.modules.operations.models import JobRun, JobStatus, Parameter
from app.modules.operations.service import PRICE_UPDATE_TASK, OperationsService
from app.shared.parameters import (
    BY_KEY,
    PARAMETERS,
    ParameterKind,
    ParameterSpec,
    initial_value,
    spec_for,
)
from tests.conftest import API_PREFIX, open_session

PANEL = f"{API_PREFIX}/operations/parameters"
AUDIT = f"{API_PREFIX}/operations/audit"

INTERVAL = "price_update.interval_hours"
THRESHOLD = "price_update.highlight_threshold_pct"
DIGEST_TIME = "daily_digest.time"
NOTICE_DAYS = "due_date.notice_days"
IDLE_MINUTES = "access.session_idle_minutes"

# What the platform does on its first day, in the numbers the acceptance
# criterion of RF-04 spells out. Written here instead of read from the catalog
# on purpose: a test that asked the catalog what the catalog says would keep
# passing on the day somebody changed a number the client signed.
STARTING_VALUES: dict[str, Any] = {
    "price_update.interval_hours": 12,
    "price_update.highlight_threshold_pct": "10",
    "access.session_idle_minutes": 60,
    "due_date.notice_days": 3,
    "purchase_order.stalled_days": 15,
    "receipt.notice_days": 3,
    "daily_digest.time": "08:00",
}

# Keys that are not parameters. Four of them look like a credential, which is
# the case the closed catalog exists for (Artículo VII): a secret must not be
# able to enter the platform's configuration over the API.
UNKNOWN_KEYS = (
    "portal.password",
    "PORTAL_PASSWORD",
    "sigprov.credentials.token",
    "secret_key",
    "price_update.interval",
)

# The parameters whose range is a pair of numbers, and the ones whose range is
# the clock. Split from the catalog rather than listed, so the grids below
# follow whatever the catalog declares.
NUMERIC = tuple(spec for spec in PARAMETERS if spec.kind is not ParameterKind.TIME_OF_DAY)
BOUNDED = tuple(spec for spec in NUMERIC if spec.minimum is not None and spec.maximum is not None)
CLOCKS = tuple(spec for spec in PARAMETERS if spec.kind is ParameterKind.TIME_OF_DAY)

# The idle window the platform starts with, and the shortest one the panel
# admits. Both are read from the catalog rather than written down: what RF-07
# promises is that the value the owner chooses governs, and a number typed here
# would stop following the catalog the day somebody moved it.
IDLE_WINDOW_MINUTES = int(initial_value(IDLE_MINUTES))
SHORTEST_IDLE_WINDOW = int(str(spec_for(IDLE_MINUTES).minimum))


def a_change(key: str, value: Any) -> dict[str, Any]:
    """The body `PUT /operations/parameters` takes to change one parameter."""
    return {"items": [{"key": key, "value": value}]}


def by_key(panel: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The panel's answer, indexed by the key each parameter is known by."""
    return {parameter["key"]: parameter for parameter in panel}


def as_written(spec: ParameterSpec, number: Decimal) -> Any:
    """The number in the shape a JSON body carries it for this parameter.

    An integer travels as an integer and a decimal as text, which is how the
    screen sends it and how the value comes back out of JSONB.
    """
    return int(number) if spec.kind is ParameterKind.INTEGER else str(number)


def edges(*, outside: bool) -> list[Any]:
    """One case per bound of every bounded parameter of the catalog (RF-06).

    `outside=False` gives the minimum and the maximum, which have to be
    accepted; `outside=True` gives one step past each, which has to be refused.
    Built from `PARAMETERS` so the grid covers a parameter nobody has written
    yet.

    The guard is the point of building it here: a numeric parameter that
    arrived without bounds cannot be refused for being out of them, and would
    drop out of this grid without a word.
    """
    assert {spec.key for spec in NUMERIC} == {spec.key for spec in BOUNDED}, (
        "a numeric parameter with no bounds silently leaves the grid below"
    )
    step = Decimal(1)
    cases: list[Any] = []
    for spec in BOUNDED:
        for name, bound, drift in (
            ("minimum", spec.minimum, -step),
            ("maximum", spec.maximum, step),
        ):
            number = Decimal(str(bound)) + (drift if outside else Decimal(0))
            cases.append(pytest.param(spec, as_written(spec, number), id=f"{spec.key}-{name}"))
    return cases


def clocks() -> list[Any]:
    """One case per parameter whose range is the clock instead of a pair.

    Driven from the catalog for the same reason `edges()` is: a second
    `TIME_OF_DAY` parameter would otherwise enter the panel with none of the
    checks below ever looking at it.
    """
    assert CLOCKS, "the catalog declares no TIME_OF_DAY parameter and this grid would be empty"
    return [pytest.param(spec, id=spec.key) for spec in CLOCKS]


async def unused_for(session: AsyncSession, user: User, minutes: int) -> None:
    """Backdate this person's live session, as if they had walked away.

    Idleness is measured from `last_seen_at`, so this is the only way a test
    can ask what happens after an idle window without waiting for one. The row
    is loaded through the same session the request will use, so what the
    application reads is what was written here.
    """
    live = await session.scalar(
        select(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .order_by(UserSession.id.desc())
    )
    assert live is not None, "the client fixture should have opened a session for this user"
    live.last_seen_at = datetime.now(UTC) - timedelta(minutes=minutes)
    await session.flush()


@pytest.fixture
async def an_update_six_hours_ago(session: AsyncSession) -> JobRun:
    """The last price list came in six hours ago, and nothing is running now.

    Local to this file on purpose: `conftest.py` is shared and other agents are
    working on it. It is the arrangement RF-07 needs — a past run the interval
    is measured from — and nothing else in the suite asks for it yet.
    """
    moment = datetime.now(UTC) - timedelta(hours=6)
    run = JobRun(
        task_name=PRICE_UPDATE_TASK,
        status=JobStatus.SUCCEEDED,
        started_at=moment,
        finished_at=moment,
        attempts=1,
    )
    session.add(run)
    await session.flush()
    return run


@pytest.fixture
async def a_screen_left_open(session: AsyncSession, sales_user: User) -> str:
    """Somebody else's session, unused for one minute less than the window.

    Local to this file, like `an_update_six_hours_ago`, and somebody else's on
    purpose. A session that makes a request is refreshed by that request, so
    the owner's own session is the one session that cannot be watched across
    the change the owner is making: it is alive after the `PUT` because the
    `PUT` touched it, whatever the window says. This one is opened and then
    left alone, which is what a screen somebody walked away from actually is.

    One minute inside the window rather than an arbitrary age, so the
    arrangement itself follows the catalog: it is alive under the value the
    client signed and dead under the shortest one the panel admits.
    """
    assert SHORTEST_IDLE_WINDOW < IDLE_WINDOW_MINUTES - 1, (
        "the shortest window the panel admits has to be shorter than the age arranged here, "
        "or the change below could not be what closes this session"
    )
    token = await open_session(session, sales_user)
    await unused_for(session, sales_user, minutes=IDLE_WINDOW_MINUTES - 1)
    return token


@pytest.mark.unit
class TestTheCatalogCanBeChecked:
    """What RF-06 needs from the catalog before any request is made.

    A parameter with no bounds cannot be refused for being out of them, and
    would drop out of the grid below without a word. This is the test that
    would notice.
    """

    def test_every_numeric_parameter_declares_the_range_it_is_checked_against(self) -> None:
        """A number the owner may set is a number with a floor and a ceiling."""
        # Assert
        assert {spec.key for spec in NUMERIC} == {spec.key for spec in BOUNDED}

    def test_the_starting_values_under_test_are_the_whole_catalog(self) -> None:
        """RF-04 is about *every* parameter, so the table below cannot lag behind."""
        # Assert
        assert set(STARTING_VALUES) == {spec.key for spec in PARAMETERS}


@pytest.mark.integration
@pytest.mark.database
class TestAFreshInstallation:
    """RF-01 and RF-04: nothing stored, and every parameter still has a value."""

    async def test_the_panel_lists_the_whole_catalog_with_no_row_behind_it(
        self, owner_client: AsyncClient, session: AsyncSession
    ) -> None:
        """The screen is drawn from the catalog, not from the table (RF-01)."""
        # Arrange
        stored = await session.scalar(select(func.count()).select_from(Parameter))

        # Act
        response = await owner_client.get(PANEL)

        # Assert
        assert stored == 0
        assert response.status_code == 200
        assert set(by_key(response.json())) == {spec.key for spec in PARAMETERS}

    async def test_the_numbers_the_client_signed_are_what_day_one_answers(
        self, owner_client: AsyncClient
    ) -> None:
        """RF-04 in its own words: 3 days' notice, stalled at 15 days, 60 idle minutes."""
        # Act
        panel = by_key((await owner_client.get(PANEL)).json())

        # Assert
        assert panel["due_date.notice_days"]["value"] == 3
        assert panel["purchase_order.stalled_days"]["value"] == 15
        assert panel["access.session_idle_minutes"]["value"] == 60
        assert {key: panel[key]["value"] for key in STARTING_VALUES} == STARTING_VALUES

    async def test_nothing_reports_a_decision_nobody_took(self, owner_client: AsyncClient) -> None:
        """`changed_at` is what tells a starting point apart from a decision."""
        # Act
        panel = (await owner_client.get(PANEL)).json()

        # Assert
        assert all(parameter["changed_at"] is None for parameter in panel)
        assert all(parameter["value"] == parameter["initial"] for parameter in panel)

    async def test_the_panel_carries_the_range_each_parameter_is_held_to(
        self, owner_client: AsyncClient
    ) -> None:
        """RF-06 is announced before it is enforced: the screen shows the bounds.

        Every bounded parameter, not one of them: the screen cannot offer a
        range it was never told, and a serialisation that dropped the pair for
        the other six would leave the owner guessing.
        """
        # Act
        panel = by_key((await owner_client.get(PANEL)).json())

        # Assert
        served = {key: (row["minimum"], row["maximum"]) for key, row in panel.items()}
        declared = {spec.key: (str(spec.minimum), str(spec.maximum)) for spec in BOUNDED}
        assert {key: served[key] for key in declared} == declared
        # One range written out rather than compared with the catalog, so the
        # day somebody widens the interval the test says so.
        assert panel[INTERVAL]["minimum"] == "1"
        assert panel[INTERVAL]["maximum"] == "168"
        # A parameter that is a time of day has no numeric bounds, and says so
        # rather than inventing a pair.
        assert panel[DIGEST_TIME]["minimum"] is None
        assert panel[DIGEST_TIME]["maximum"] is None


@pytest.mark.integration
@pytest.mark.database
class TestTheEdgesOfEveryRange:
    """RF-06, one case per bound of every parameter the catalog declares."""

    @pytest.mark.parametrize(("spec", "value"), edges(outside=False))
    async def test_a_bound_is_a_value_the_owner_may_choose(
        self, owner_client: AsyncClient, spec: ParameterSpec, value: Any
    ) -> None:
        """The minimum and the maximum are inside the range, not outside it.

        Read back rather than believed: the answer to a `PUT` is built from
        what the request coerced, and a decimal that travels to JSONB as text
        could come back a different value from the one that was reported. The
        second call is the only one that has been through the database.
        """
        # Act
        response = await owner_client.put(PANEL, json=a_change(spec.key, value))

        # Assert
        assert response.status_code == 200
        written = response.json()[0]
        assert written["key"] == spec.key
        assert written["value"] == value
        assert written["changed_at"] is not None
        panel = by_key((await owner_client.get(PANEL)).json())
        assert panel[spec.key]["value"] == value

    @pytest.mark.parametrize(("spec", "value"), edges(outside=True))
    async def test_one_step_past_a_bound_is_refused_naming_the_range(
        self, owner_client: AsyncClient, spec: ParameterSpec, value: Any
    ) -> None:
        """RF-06: refused, and the message says between which values it has to be."""
        # Act
        response = await owner_client.put(PANEL, json=a_change(spec.key, value))

        # Assert
        assert response.status_code == 422
        error = response.json()["error"]
        assert str(spec.minimum) in error["message"]
        assert str(spec.maximum) in error["message"]
        # In Spanish, and naming the parameter the owner is looking at (RF-05).
        assert spec.label in error["message"]
        assert error["details"]["key"] == spec.key

    async def test_a_refused_value_leaves_the_parameter_where_it_was(
        self, owner_client: AsyncClient
    ) -> None:
        """A refusal is not a half-applied change: the old rule still governs."""
        # Act
        response = await owner_client.put(PANEL, json=a_change(INTERVAL, 0))

        # Assert
        assert response.status_code == 422
        panel = by_key((await owner_client.get(PANEL)).json())
        assert panel[INTERVAL]["value"] == 12
        assert panel[INTERVAL]["changed_at"] is None

    async def test_a_word_where_a_number_goes_is_refused(self, owner_client: AsyncClient) -> None:
        """Not every bad value is out of range: some are not values at all."""
        # Act
        response = await owner_client.put(PANEL, json=a_change(THRESHOLD, "mucho"))

        # Assert
        assert response.status_code == 422
        assert response.json()["error"]["details"]["key"] == THRESHOLD

    async def test_a_fraction_where_a_whole_number_goes_is_refused(
        self, owner_client: AsyncClient
    ) -> None:
        """Half an hour of interval is not an interval this parameter can hold."""
        # Act
        response = await owner_client.put(PANEL, json=a_change(INTERVAL, 12.5))

        # Assert
        assert response.status_code == 422
        assert response.json()["error"]["details"]["key"] == INTERVAL

    @pytest.mark.parametrize("key", [THRESHOLD, INTERVAL])
    @pytest.mark.parametrize("value", ["nan", "snan", "-nan", "inf", "-Infinity"])
    async def test_a_value_that_is_not_a_number_is_refused_like_any_other(
        self, owner_client: AsyncClient, key: str, value: str
    ) -> None:
        """No spelling of "not a number" is in any range, and no infinity either.

        Both kinds of number, because the refusal is one for both: a `nan` on a
        whole-number parameter used to be turned away by the integer check and
        only reached this one on a decimal.
        """
        # Act
        response = await owner_client.put(PANEL, json=a_change(key, value))

        # Assert
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["details"]["key"] == key
        # The refusal has to be *this* one and not the range message: an
        # infinity is also past every bound, so a guard narrowed to `nan` alone
        # would still answer 422 here and leave the crash it fixed uncovered.
        assert error["message"] == f"«{spec_for(key).label}» tiene que ser un número."


@pytest.mark.integration
@pytest.mark.database
class TestTheParametersWhoseRangeIsTheClock:
    """A time of day has no pair of bounds: its range is the clock (RF-06).

    `daily_digest.time` is the only one today, and the grid comes from the
    catalog anyway, so a second one joins these cases the day it is declared
    instead of entering the panel unchecked.
    """

    @pytest.mark.parametrize("spec", clocks())
    @pytest.mark.parametrize(
        ("sent", "stored"),
        [("00:00", "00:00"), ("23:59", "23:59"), ("8:05", "08:05"), (" 07:30 ", "07:30")],
    )
    async def test_a_time_the_clock_has_is_accepted(
        self, owner_client: AsyncClient, spec: ParameterSpec, sent: str, stored: str
    ) -> None:
        """Both ends of the day are valid times, and a lazy one is read as written.

        The normalisation is read back from the panel too: what the owner sees
        tomorrow is the row, not the answer this request happened to build.
        """
        # Act
        response = await owner_client.put(PANEL, json=a_change(spec.key, sent))

        # Assert
        assert response.status_code == 200
        assert response.json()[0]["value"] == stored
        panel = by_key((await owner_client.get(PANEL)).json())
        assert panel[spec.key]["value"] == stored

    @pytest.mark.parametrize("spec", clocks())
    @pytest.mark.parametrize(
        "value", ["24:00", "12:60", "8", "08:0", "-1:00", "ocho", "08:00:00", "", "0800"]
    )
    async def test_a_time_the_clock_does_not_have_is_refused_with_its_format(
        self, owner_client: AsyncClient, spec: ParameterSpec, value: str
    ) -> None:
        """RF-06 for a parameter with no numeric bounds: the message says the shape."""
        # Act
        response = await owner_client.put(PANEL, json=a_change(spec.key, value))

        # Assert
        assert response.status_code == 422
        message = response.json()["error"]["message"]
        assert "HH:MM" in message
        assert "00:00" in message
        assert "23:59" in message


@pytest.mark.integration
@pytest.mark.database
class TestTheCatalogIsClosed:
    """A key nobody declared is not a parameter, and cannot become one (RF-06).

    This is also the mechanism Artículo VII leans on: the platform's secrets
    live in the environment, and the reason a credential cannot be smuggled in
    as a parameter is that the list of parameters is fixed in code.
    """

    @pytest.mark.parametrize("key", UNKNOWN_KEYS)
    async def test_a_key_outside_the_catalog_is_refused(
        self, owner_client: AsyncClient, key: str
    ) -> None:
        """Refused for what it is — not a parameter — and the answer says which key."""
        # Act
        response = await owner_client.put(PANEL, json=a_change(key, "hunter2"))

        # Assert
        assert response.status_code == 422
        assert response.json()["error"]["details"]["key"] == key

    async def test_a_credential_never_reaches_the_table(
        self, owner_client: AsyncClient, session: AsyncSession
    ) -> None:
        """Artículo VII: nothing that looks like a secret gets stored on the way in."""
        # Act
        response = await owner_client.put(PANEL, json=a_change("portal.password", "hunter2"))

        # Assert
        assert response.status_code == 422
        rows = (await session.execute(select(Parameter))).scalars().all()
        assert rows == []
        assert "portal.password" not in by_key((await owner_client.get(PANEL)).json())

    async def test_the_refusal_says_which_keys_do_exist(self, owner_client: AsyncClient) -> None:
        """A closed list is only usable if the refusal names what the list holds."""
        # Act
        response = await owner_client.put(PANEL, json=a_change("portal.password", "hunter2"))

        # Assert
        assert response.json()["error"]["details"]["known"] == sorted(
            spec.key for spec in PARAMETERS
        )

    async def test_a_good_key_beside_an_unknown_one_is_not_written_either(
        self, owner_client: AsyncClient
    ) -> None:
        """The whole set is refused, so the panel never lands half applied."""
        # Act
        response = await owner_client.put(
            PANEL,
            json={
                "items": [
                    {"key": INTERVAL, "value": 24},
                    {"key": "portal.password", "value": "hunter2"},
                ]
            },
        )

        # Assert
        assert response.status_code == 422
        panel = by_key((await owner_client.get(PANEL)).json())
        assert panel[INTERVAL]["value"] == 12


@pytest.mark.integration
@pytest.mark.database
class TestWhoReachesThePanel:
    """RF-03: the parameters are the owner's, to read and to write."""

    @pytest.mark.parametrize("caller", ["purchasing", "sales"])
    @pytest.mark.parametrize(("method", "body"), [("GET", None), ("PUT", a_change(INTERVAL, 24))])
    async def test_neither_operational_role_reaches_the_panel(
        self,
        purchasing_client: AsyncClient,
        sales_client: AsyncClient,
        caller: str,
        method: str,
        body: dict[str, Any] | None,
    ) -> None:
        """Not a smaller panel: no panel at all, on the read route and on the write one.

        Both clients are asked for and one is picked, rather than resolved by
        name at run time: an async fixture cannot be set up from inside a test
        that is already running on the loop.
        """
        # Arrange
        client = {"purchasing": purchasing_client, "sales": sales_client}[caller]

        # Act
        response = await client.request(method, PANEL, json=body)

        # Assert
        assert response.status_code == 403

    async def test_a_refused_role_changes_nothing(
        self, sales_client: AsyncClient, owner_client: AsyncClient
    ) -> None:
        """The refusal is the whole story: the value the owner reads is untouched."""
        # Act
        response = await sales_client.put(PANEL, json=a_change(INTERVAL, 24))

        # Assert
        assert response.status_code == 403
        panel = by_key((await owner_client.get(PANEL)).json())
        assert panel[INTERVAL]["value"] == 12

    async def test_the_owner_reads_the_panel(self, owner_client: AsyncClient) -> None:
        """The other half of RF-03: the door is closed to everybody but one."""
        # Act
        response = await owner_client.get(PANEL)

        # Assert
        assert response.status_code == 200
        assert len(response.json()) == len(PARAMETERS)

    async def test_the_owner_writes_the_panel(self, owner_client: AsyncClient) -> None:
        """RF-02: the owner changes a parameter and it is stored."""
        # Act
        response = await owner_client.put(PANEL, json=a_change(INTERVAL, 24))

        # Assert
        assert response.status_code == 200
        panel = by_key((await owner_client.get(PANEL)).json())
        assert panel[INTERVAL]["value"] == 24
        assert panel[INTERVAL]["changed_at"] is not None


@pytest.mark.integration
@pytest.mark.database
class TestWhatTheScreenCanTellApart:
    """RF-05 and the knobs that do not move anything yet.

    Some of these parameters are still waiting for the feature that will read
    them. The screen shows them anyway — the owner fixes them from day one —
    and marks them, because a panel that hid the difference would be lying.
    The half that can be verified from here is that the API says which is which.
    """

    async def test_every_parameter_says_what_changes_if_it_moves(
        self, owner_client: AsyncClient
    ) -> None:
        """RF-05: a sentence, in Spanish, beside each one — and its own.

        Compared with the catalog rather than checked for being non-empty: the
        promise is that the owner reads the sentence of *that* parameter, so
        two labels swapped between rows has to fail here. That the catalog's
        own sentences are not blank is `tests/unit/shared/test_parameters.py`.
        """
        # Act
        panel = (await owner_client.get(PANEL)).json()

        # Assert
        assert {row["key"]: (row["label"], row["effect"]) for row in panel} == {
            spec.key: (spec.label, spec.effect) for spec in PARAMETERS
        }

    async def test_the_panel_marks_the_parameters_that_have_no_effect_yet(
        self, owner_client: AsyncClient
    ) -> None:
        """One of each class, named: one that is read today and one that is not."""
        # Act
        panel = by_key((await owner_client.get(PANEL)).json())

        # Assert
        assert panel[INTERVAL]["has_effect"] is True
        assert panel[INTERVAL]["consumed_by"] == "catalog"
        assert panel[NOTICE_DAYS]["has_effect"] is False
        assert panel[NOTICE_DAYS]["consumed_by"] == ""

    async def test_the_two_classes_agree_with_each_other_everywhere(
        self, owner_client: AsyncClient
    ) -> None:
        """`has_effect` is not a second opinion: it is whether anybody consumes it."""
        # Act
        panel = (await owner_client.get(PANEL)).json()

        # Assert
        assert all(parameter["has_effect"] is bool(parameter["consumed_by"]) for parameter in panel)
        assert any(parameter["has_effect"] for parameter in panel)
        assert any(not parameter["has_effect"] for parameter in panel)


@pytest.mark.integration
@pytest.mark.database
class TestAChangeTakesEffectOnItsOwn:
    """RF-07: the new value governs without anybody doing anything else.

    Two of the three parameters that have a consumer today are read by
    `catalog`, inside the same request path. The third, the idle timeout, is
    read by `identity` — another module — and therefore only ever arrives by
    event. That is the crossing that can break silently, so it is tested here
    end to end rather than by checking that the row was written.
    """

    @pytest.mark.usefixtures("an_update_six_hours_ago")
    async def test_the_starting_interval_is_what_decides_before_any_change(
        self, session: AsyncSession
    ) -> None:
        """Six hours after the last list, twelve hours' interval says: not yet."""
        # Arrange
        service = OperationsService(session)

        # Act
        due = await service.due_for_update()

        # Assert
        assert due is False

    @pytest.mark.usefixtures("an_update_six_hours_ago")
    async def test_changing_the_interval_changes_the_next_decision(
        self, owner_client: AsyncClient, session: AsyncSession
    ) -> None:
        """RF-07: an hour's interval, and the same six-hour-old run is now overdue.

        No restart, no redeploy, no second call: the only thing that happened
        between the two answers is the `PUT`.
        """
        # Arrange
        service = OperationsService(session)

        # Act
        response = await owner_client.put(PANEL, json=a_change(INTERVAL, 1))

        # Assert
        assert response.status_code == 200
        assert await service.due_for_update() is True

    @pytest.mark.usefixtures("an_update_six_hours_ago")
    async def test_a_longer_interval_keeps_the_next_query_away(
        self, owner_client: AsyncClient, session: AsyncSession
    ) -> None:
        """The parameter moves the decision in both directions, not only one."""
        # Arrange
        service = OperationsService(session)

        # Act
        await owner_client.put(PANEL, json=a_change(INTERVAL, 168))

        # Assert
        assert await service.due_for_update() is False

    async def test_the_idle_timeout_reaches_the_module_that_enforces_it(
        self, owner_client: AsyncClient, session: AsyncSession
    ) -> None:
        """The value crosses into `identity`'s own copy, which is the only road it has.

        `operations` owns the parameter and `identity` obeys it, and no module
        imports another (Artículo IV): the projection is fed by
        `BusinessParameterChanged` or by nothing at all.
        """
        # Arrange
        before = await IdentityService(session).users.get_setting(IDLE_MINUTES)

        # Act
        response = await owner_client.put(PANEL, json=a_change(IDLE_MINUTES, 5))

        # Assert
        assert response.status_code == 200
        assert before is None
        projected = await IdentityService(session).users.get_setting(IDLE_MINUTES)
        assert projected is not None
        assert projected.value == 5

    async def test_a_shorter_idle_timeout_closes_a_session_that_was_still_open(
        self, owner_client: AsyncClient, owner: User, session: AsyncSession
    ) -> None:
        """RF-07 where it is hardest: the change governs the next request itself.

        Five minutes of tolerance and a session unused for ten, and the same
        client that saved the parameter is no longer admitted. Nothing was
        restarted between the two calls.
        """
        # Arrange
        assert (await owner_client.put(PANEL, json=a_change(IDLE_MINUTES, 5))).status_code == 200
        await unused_for(session, owner, minutes=10)

        # Act
        response = await owner_client.get(PANEL)

        # Assert
        assert response.status_code == 401

    async def test_the_starting_window_still_admits_a_screen_left_open(
        self, a_screen_left_open: str, session: AsyncSession
    ) -> None:
        """The control of the pair: before any change, that session resolves.

        Same arrangement as the test below and nothing changed, which is what
        makes the difference there attributable to the `PUT` and not to the
        backdating. It is also RF-04 from this side: with no row in the table,
        the window in force is the catalog's, and one minute inside it is
        inside it.
        """
        # Arrange
        identity = IdentityService(session)

        # Act
        resolved = await identity.resolve_session(a_screen_left_open)

        # Assert
        assert resolved is not None

    async def test_shortening_the_window_from_the_panel_closes_that_screen(
        self, owner_client: AsyncClient, a_screen_left_open: str, session: AsyncSession
    ) -> None:
        """RF-07 down the whole road, for the parameter that has to cross a module.

        `PUT /operations/parameters` → `BusinessParameterChanged` →
        `project_access_setting` → `apply_setting` → the projection
        `IdentityService` reads before its own default. Every link is between
        the two answers, and nothing else is: the session was admitted by the
        test above under this same arrangement, and the only thing that happens
        here is the owner saving the panel. No restart, no second call, no
        rearranging of the session in between.

        The projection is asserted on the way past rather than trusted, so a
        failure says which link broke: an event nobody subscribed to leaves it
        empty, and a handler that stored the key under another name leaves it
        holding nothing useful.
        """
        # Arrange
        identity = IdentityService(session)
        assert await identity.users.get_setting(IDLE_MINUTES) is None

        # Act
        response = await owner_client.put(PANEL, json=a_change(IDLE_MINUTES, SHORTEST_IDLE_WINDOW))

        # Assert
        assert response.status_code == 200
        projected = await identity.users.get_setting(IDLE_MINUTES)
        assert projected is not None
        assert projected.value == SHORTEST_IDLE_WINDOW
        assert await identity.resolve_session(a_screen_left_open) is None

    async def test_the_signed_hour_leaves_that_same_session_open(
        self, owner_client: AsyncClient, owner: User, session: AsyncSession
    ) -> None:
        """RF-04's own number as the control: at 60 minutes, ten idle ones are nothing.

        Same arrangement as the test above and a different parameter value, so
        what closed the session there was the parameter and not the backdating.
        """
        # Arrange
        assert (await owner_client.put(PANEL, json=a_change(IDLE_MINUTES, 60))).status_code == 200
        await unused_for(session, owner, minutes=10)

        # Act
        response = await owner_client.get(PANEL)

        # Assert
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.database
class TestAChangeLeavesItsTrail:
    """RF-08: the old value, the new one, who changed it and when."""

    async def test_the_log_carries_the_four_facts(
        self, owner_client: AsyncClient, owner: User
    ) -> None:
        """Everything the owner needs to explain a number that stopped making sense."""
        # Arrange
        before = datetime.now(UTC)

        # Act
        await owner_client.put(PANEL, json=a_change(INTERVAL, 24))

        # Assert
        history = (await owner_client.get(AUDIT)).json()
        assert history["total"] == 1
        entry = history["items"][0]
        assert entry["entity_id"] == INTERVAL
        assert entry["old_value"] == 12
        assert entry["new_value"] == 24
        assert entry["actor_user_id"] == owner.id
        assert entry["actor_name"] == owner.name
        assert entry["section"] == "SYSTEM"
        assert datetime.fromisoformat(entry["occurred_at"]) >= before

    async def test_the_old_value_of_the_first_change_is_the_starting_one(
        self, owner_client: AsyncClient
    ) -> None:
        """A parameter with no row still had a value, and that is what it replaced."""
        # Act
        await owner_client.put(PANEL, json=a_change(NOTICE_DAYS, 10))

        # Assert
        entry = (await owner_client.get(AUDIT)).json()["items"][0]
        assert entry["old_value"] == 3
        assert entry["new_value"] == 10

    async def test_a_second_change_records_the_value_it_actually_replaced(
        self, owner_client: AsyncClient
    ) -> None:
        """Newest first (RF-13), and the second line replaces the first's value, not the initial."""
        # Arrange
        await owner_client.put(PANEL, json=a_change(INTERVAL, 24))

        # Act
        await owner_client.put(PANEL, json=a_change(INTERVAL, 6))

        # Assert
        history = (await owner_client.get(AUDIT)).json()
        assert history["total"] == 2
        assert [entry["old_value"] for entry in history["items"]] == [24, 12]
        assert [entry["new_value"] for entry in history["items"]] == [6, 24]

    async def test_changing_two_parameters_at_once_leaves_two_lines(
        self, owner_client: AsyncClient
    ) -> None:
        """The screen saves the whole set, and the log keeps them apart."""
        # Act
        response = await owner_client.put(
            PANEL,
            json={
                "items": [
                    {"key": INTERVAL, "value": 24},
                    {"key": NOTICE_DAYS, "value": 7},
                ]
            },
        )

        # Assert
        assert response.status_code == 200
        history = (await owner_client.get(AUDIT)).json()
        assert history["total"] == 2
        assert {entry["entity_id"] for entry in history["items"]} == {INTERVAL, NOTICE_DAYS}

    async def test_saving_the_value_that_was_already_there_is_written_down_too(
        self, owner_client: AsyncClient
    ) -> None:
        """The screen saves the whole set, so a parameter nobody moved is sent back.

        What the platform does today is record it: a line whose old value and
        new value are the same, which is what the owner will read in the
        history. The spec does not rule on this case either way — it describes
        the log of *changes* — so this test states the behaviour rather than
        endorsing it, and the question is escalated to the Solution-Designer.
        If the answer is that a saved-but-unchanged parameter should leave no
        line, this test is the one that has to change with the code.
        """
        # Arrange
        await owner_client.put(PANEL, json=a_change(INTERVAL, 24))

        # Act
        response = await owner_client.put(PANEL, json=a_change(INTERVAL, 24))

        # Assert
        assert response.status_code == 200
        panel = by_key((await owner_client.get(PANEL)).json())
        assert panel[INTERVAL]["value"] == 24
        history = (await owner_client.get(AUDIT)).json()
        assert history["total"] == 2
        assert history["items"][0]["old_value"] == history["items"][0]["new_value"] == 24

    async def test_a_refused_change_leaves_no_line_at_all(self, owner_client: AsyncClient) -> None:
        """Nothing happened, so there is nothing to explain later."""
        # Act
        response = await owner_client.put(PANEL, json=a_change(INTERVAL, 0))

        # Assert
        assert response.status_code == 422
        assert (await owner_client.get(AUDIT)).json()["total"] == 0


# --- what a migrated database starts with ---------------------------------
#
# Every test above runs on a schema `conftest.py` built with
# `Base.metadata.create_all()`: alembic is never invoked, so the parameter
# tables begin empty and the starting values can only come from the catalog.
# A real installation is not in that state — it is in whatever the migration
# chain left it — and nothing in this suite has ever looked there.
#
# What follows reads the migrations as text, in the style of
# `tests/architecture/`, and asks the one question the rest of the file cannot:
# after `alembic upgrade head`, is a parameter left holding a value the catalog
# contradicts? Running the chain for real would answer it too, at the cost of a
# throwaway database and a subprocess to point alembic at it, for a fact the
# source already states.

MIGRATIONS = Path(app.__file__).resolve().parents[1] / "alembic" / "versions"

# The two tables a parameter's value can be left in. `operations.parameter`
# holds the decisions the owner took, and is what the panel reads. The other is
# `identity`'s own copy of the access parameters, and is what
# `IdentityService._setting` reads before falling back to the catalog — so a
# stale row there is not a stale display, it is what the platform obeys.
PARAMETER_TABLES = ("parameter", "access_settings")

WRITES_INTO = {
    table: re.compile(rf"INSERT\s+INTO\s+\S*\b{table}\b", re.IGNORECASE)
    for table in PARAMETER_TABLES
}
CLEARS_FROM = {
    table: re.compile(rf"DELETE\s+FROM\s+\S*\b{table}\b", re.IGNORECASE)
    for table in PARAMETER_TABLES
}

# A seeded parameter as the migrations write one: a quoted key and, beside it,
# the JSON document that gets cast to jsonb — `"480"` for a number, `'"10"'`
# for a string. Both spellings are read through `json.loads`, which is the same
# reading PostgreSQL gives them.
A_SEEDED_PAIR = re.compile(
    r"""["'](?P<key>[a-z][\w]*(?:\.[a-z][\w]*)+)["']\s*,\s*"""
    r"""(?P<value>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')"""
)


def migrations() -> list[Path]:
    """Every migration of the chain, in the order alembic applies them."""
    return sorted(MIGRATIONS.glob("[0-9]*.py"))


def upgrade_of(path: Path) -> str:
    """The half of a migration that `alembic upgrade head` runs.

    Everything above `def downgrade(`: the module constants the seeds are
    declared in, and the body of `upgrade()`. A downgrade that writes an old
    value back is restoring a former state on purpose, and is not what a
    running installation is left holding.
    """
    return path.read_text(encoding="utf-8").split("def downgrade(")[0]


def seeded_in(source: str) -> dict[str, Any]:
    """The catalog parameters this migration writes a literal value for."""
    seeds: dict[str, Any] = {}
    for match in A_SEEDED_PAIR.finditer(source):
        key = match.group("key")
        if key not in BY_KEY:
            continue
        try:
            seeds[key] = json.loads(match.group("value")[1:-1])
        except json.JSONDecodeError:
            continue
    return seeds


def surviving_seeds() -> dict[tuple[str, str], tuple[Any, str]]:
    """What the chain leaves in the parameter tables, by table and key.

    Each migration is applied to the picture the previous ones left: one that
    deletes from a table clears the keys it names, one that inserts into a
    table seeds them. Attributing a migration's literal pairs to every
    parameter table it writes is an approximation, and an exact one over this
    chain — the migrations that seed write the same tuple to each table they
    touch.
    """
    surviving: dict[tuple[str, str], tuple[Any, str]] = {}
    for path in migrations():
        source = upgrade_of(path)
        seeds = seeded_in(source)
        for table in PARAMETER_TABLES:
            if CLEARS_FROM[table].search(source):
                for key in seeds:
                    surviving.pop((table, key), None)
            if WRITES_INTO[table].search(source):
                for key, value in seeds.items():
                    surviving[(table, key)] = (value, path.name)
    return surviving


@pytest.mark.unit
class TestAMigratedDatabaseStartsWhereTheCatalogSays:
    """RF-04 on the database an installation actually has, not the one tests build."""

    def test_there_are_migrations_to_read(self) -> None:
        """A moved directory must not quietly turn this class into nothing."""
        # Assert
        assert migrations(), f"no migrations under {MIGRATIONS}"

    def test_the_reader_understands_both_shapes_a_seed_is_written_in(self) -> None:
        """A regex that matched nothing would make the check below say nothing.

        The two shapes are the two a parameter is seeded in: an integer, and a
        string that reaches jsonb quoted. Reading either one wrong is how this
        file would go quiet without failing.
        """
        # Act
        seeds = {
            key: value
            for path in migrations()
            for key, value in seeded_in(upgrade_of(path)).items()
        }

        # Assert
        assert seeds[INTERVAL] == 12
        assert seeds[THRESHOLD] == "10"

    def test_no_parameter_is_left_holding_a_value_the_catalog_contradicts(self) -> None:
        """What the platform obeys after `alembic upgrade head` is what the panel shows."""
        # Act
        surviving = surviving_seeds()

        # Assert
        disagreements = [
            f"{table}.{key} = {value!r}, seeded by {origin}, while the catalog says "
            f"{BY_KEY[key].stored_initial!r}"
            for (table, key), (value, origin) in sorted(surviving.items())
            if value != BY_KEY[key].stored_initial
        ]
        assert not disagreements, (
            "a migrated database starts with a value the panel does not show: "
            + "; ".join(disagreements)
        )
