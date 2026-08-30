"""H2: every manual change is written down, and what is written cannot be rewritten.

The `Developer` already checked in `test_manual_corrections.py` that a correction
leaves a line behind. What is here is the rest of the story — the part that only
breaks when somebody is not looking:

* **RF-16 and RF-17 against the database.** A repository without an `update`
  method prevents nothing that a `psql` session cannot do anyway, so the
  `UPDATE`, the `DELETE` and the `TRUNCATE` are issued as raw SQL and the
  database is the one expected to say no.
* **`GEN-09`.** A correction whose log line fails must not leave the corrected
  value behind. It is the one place where a rollback is the right answer.
* **RF-18 and RF-19 end to end.** Who sees whose changes is authorisation, and
  authorisation is proved with three real sessions over HTTP, never with a mock.
* **RF-09 to RF-15.** Order, reason, author, the value before, the filters and
  the history of a single datum.

Note on the session: a statement the database refuses aborts the transaction,
so every test that provokes one rolls back before asking anything else. The
suite's outer transaction survives that — `session.commit()` releases a
savepoint and opens the next one — which is why the row committed before the
refused statement is still there afterwards.
"""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.service import CatalogService
from app.modules.identity.models import User
from app.modules.operations.service import OperationsService
from app.shared.corrections import CorrectionReason
from app.shared.events import AuditAction, ManualChangeRecorded
from app.shared.sections import BusinessSection
from tests.conftest import API_PREFIX
from tests.factories.catalog_factory import ProductFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

REASON = CorrectionReason.PORTAL_WAS_WRONG.value
REASON_LABEL = "El portal lo informó mal"

# The shop's clock, written out rather than imported from `app.shared.time`: the
# behaviour under test is that a date with no offset is read in Buenos Aires,
# and a test that borrowed the application's own constant would keep passing if
# that constant changed to UTC.
ARGENTINA = timezone(timedelta(hours=-3))


async def record(
    session: AsyncSession,
    *,
    actor_user_id: int,
    section: BusinessSection,
    entity_type: str = "catalog.product_price",
    entity_id: str = "1",
    field: str | None = "price",
    action: AuditAction = AuditAction.CORRECTED,
    old_value: Any = "1000",
    new_value: Any = "1200",
    reason_code: str | None = REASON,
    reason_detail: str | None = None,
    occurred_at: datetime | None = None,
) -> None:
    """Append one line to the log through the module's only door.

    Local to this file on purpose: `conftest.py` is shared and this helper is
    not general enough to earn a place there. It goes through
    `record_manual_change` rather than through the model so the row is built
    exactly the way the handler builds it.
    """
    event = ManualChangeRecorded(
        entity_type=entity_type,
        entity_id=entity_id,
        field=field,
        action=action,
        actor_user_id=actor_user_id,
        section=section,
        old_value=old_value,
        new_value=new_value,
        reason_code=reason_code,
        reason_detail=reason_detail,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    await OperationsService(session).record_manual_change(event)
    await session.commit()


async def a_logged_correction(session: AsyncSession, *, actor_user_id: int = 1) -> int:
    """A product corrected by hand, and the id of its product. One log line."""
    product = await ProductFactory.create(session, price=1000)
    product_id = product.id
    await CatalogService(session).apply_correction(
        product_id=product_id,
        field="price",
        value="1200",
        reason_code=REASON,
        reason_detail="la factura del proveedor dice 1200",
        actor_user_id=actor_user_id,
    )
    await session.commit()
    return product_id


async def rows_in_the_log(session: AsyncSession) -> int:
    """How many entries the table actually holds, counted in SQL."""
    result = await session.execute(text("SELECT count(*) FROM operations.audit_entry"))
    return int(result.scalar_one())


class TestTheLogCannotBeRewritten:
    """RF-16 and RF-17, asked of the database rather than of the repository.

    `AuditEntryRepository` deliberately has no `update` and no `delete`, and
    `test_manual_corrections.py` already shows the `UPDATE` bouncing. What these
    tests add is the other statement, the surviving row, and the operation the
    row-level trigger cannot see — a `TRUNCATE`, refused by a second,
    statement-level trigger.
    """

    async def test_a_delete_by_direct_sql_is_refused_and_the_row_survives(
        self, session: AsyncSession
    ) -> None:
        """RF-17: a `DELETE` on the log fails, and the entry is still readable after."""
        # Arrange
        await a_logged_correction(session)
        assert await rows_in_the_log(session) == 1

        # Act
        with pytest.raises(DBAPIError) as refused:
            await session.execute(text("DELETE FROM operations.audit_entry"))

        # Assert
        await session.rollback()
        assert "append-only" in str(refused.value)
        assert await rows_in_the_log(session) == 1

    async def test_an_update_of_one_entry_is_refused_and_leaves_it_as_it_was(
        self, session: AsyncSession
    ) -> None:
        """RF-16: even a targeted `UPDATE` of a single column bounces."""
        # Arrange
        await a_logged_correction(session)

        # Act
        with pytest.raises(DBAPIError) as refused:
            await session.execute(
                text("UPDATE operations.audit_entry SET old_value = '\"0\"'::jsonb")
            )

        # Assert
        await session.rollback()
        assert "append-only" in str(refused.value)
        log = await OperationsService(session).list_audit(sections=None)
        assert log.items[0].old_value == "1000.0000"

    async def test_a_truncate_is_refused_too(self, session: AsyncSession) -> None:
        """RF-17 for the statement that empties the table instead of a row of it."""
        # Arrange
        await a_logged_correction(session)

        # Act
        with pytest.raises(DBAPIError) as refused:
            await session.execute(text("TRUNCATE operations.audit_entry"))

        # Assert
        await session.rollback()
        assert "append-only" in str(refused.value)
        assert await rows_in_the_log(session) == 1


class TestALogThatFailsTakesTheChangeWithIt:
    """`GEN-09`: the handler runs in the publisher's transaction, so it can veto.

    Not `events.clear()` to break the chain: the bus is one object for the whole
    process, and clearing it would leave every later test in the run without its
    subscriptions. What fails here is the writing, not the wiring.
    """

    @pytest.fixture
    def broken_log(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Make the one door into the log raise, wherever it is called from."""

        async def refuse(self: OperationsService, event: ManualChangeRecorded) -> None:
            raise RuntimeError("the log is unavailable")

        monkeypatch.setattr(OperationsService, "record_manual_change", refuse)

    async def test_the_corrected_value_does_not_survive_a_log_that_fails(
        self, session: AsyncSession, broken_log: None
    ) -> None:
        """A change that could not be written down did not happen (Artículo II)."""
        # Arrange — the id is read before the rollback, which expires the object
        product = await ProductFactory.create(session, price=1000)
        product_id = product.id
        await session.commit()
        service = CatalogService(session)

        # Act
        with pytest.raises(RuntimeError, match="the log is unavailable"):
            await service.apply_correction(
                product_id=product_id,
                field="price",
                value="1200",
                reason_code=REASON,
                reason_detail=None,
                actor_user_id=1,
            )
        await session.rollback()

        # Assert
        history = await CatalogService(session).price_history(product_id)
        assert history.price == Decimal("1000")

    async def test_it_leaves_no_correction_behind_either(
        self, session: AsyncSession, broken_log: None
    ) -> None:
        """The row that keeps the portal's value goes back with the edit.

        A correction row that outlived its log line would make the price screen
        say "corregido a mano" over a value nobody ever corrected.
        """
        # Arrange
        product = await ProductFactory.create(session, price=1000)
        product_id = product.id
        await session.commit()

        # Act
        with pytest.raises(RuntimeError, match="the log is unavailable"):
            await CatalogService(session).apply_correction(
                product_id=product_id,
                field="price",
                value="1200",
                reason_code=REASON,
                reason_detail=None,
                actor_user_id=1,
            )
        await session.rollback()

        # Assert
        assert (await CatalogService(session).price_history(product_id)).corrections == []
        assert await rows_in_the_log(session) == 0


class TestWhoSeesWhichChanges:
    """RF-18 and RF-19 over HTTP, with three real sessions and no mock.

    Which sections a role reaches is `identity`'s answer and it is applied
    inside the query, so the only honest way to test it is to ask the API as
    each of the three people.
    """

    @pytest.fixture
    async def three_changes(
        self,
        session: AsyncSession,
        owner: User,
        purchasing_user: User,
        sales_user: User,
        owner_client: AsyncClient,
        sales_client: AsyncClient,
    ) -> None:
        """One line per section, two of them made through the API itself.

        The owner changes a parameter (`SYSTEM`) and sales corrects a price
        (`SALES`) by calling the endpoints a person would. The purchasing line
        is appended directly because purchasing owns no editable datum yet — its
        module is a later feature — and RF-19 needs a section the other two
        cannot see.
        """
        product = await ProductFactory.create(session, price=1000)

        parameters = await owner_client.put(
            f"{API_PREFIX}/operations/parameters",
            json={"items": [{"key": "due_date.notice_days", "value": 5}]},
        )
        assert parameters.status_code == 200

        correction = await sales_client.post(
            f"{API_PREFIX}/catalog/products/{product.id}/corrections",
            json={"field": "price", "value": "1200", "reason_code": REASON},
        )
        assert correction.status_code == 200

        await record(
            session,
            actor_user_id=purchasing_user.id,
            section=BusinessSection.PURCHASING,
            entity_type="purchasing.invoice",
            entity_id="55",
            field="total",
        )

    async def test_the_owner_sees_the_changes_of_all_three(
        self,
        owner_client: AsyncClient,
        owner: User,
        purchasing_user: User,
        sales_user: User,
        three_changes: None,
    ) -> None:
        """RF-18: the owner reaches every section, so the history is everybody's."""
        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert {entry["section"] for entry in body["items"]} == {"SYSTEM", "SALES", "PURCHASING"}
        assert {entry["actor_user_id"] for entry in body["items"]} == {
            owner.id,
            purchasing_user.id,
            sales_user.id,
        }

    async def test_sales_sees_the_sales_section_and_nothing_else(
        self, sales_client: AsyncClient, sales_user: User, three_changes: None
    ) -> None:
        """RF-19: Julián reads his own section, not the parameters and not purchasing."""
        # Act
        response = await sales_client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["section"] == "SALES"
        assert body["items"][0]["actor_user_id"] == sales_user.id

    async def test_purchasing_does_not_see_the_changes_of_sales(
        self, purchasing_client: AsyncClient, purchasing_user: User, three_changes: None
    ) -> None:
        """RF-19 from the other side: Marcela reads purchasing, and only purchasing."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert [entry["section"] for entry in body["items"]] == ["PURCHASING"]
        assert body["items"][0]["actor_user_id"] == purchasing_user.id

    async def test_filtering_by_a_person_is_not_a_way_around_the_section_filter(
        self,
        sales_client: AsyncClient,
        owner_client: AsyncClient,
        owner: User,
        three_changes: None,
    ) -> None:
        """RF-14 does not undo RF-19: Julián asks for the owner's changes and gets none.

        The filter by person is the one that could turn into a detour, because
        it is the caller who names whose changes to bring. The section is not a
        filter the caller chooses — it is the authorisation, and it has to be
        applied on top of whatever else was asked for.
        """
        # Arrange — the owner's own line exists and the filter finds it for him
        by_the_owner = await owner_client.get(
            f"{API_PREFIX}/operations/audit", params={"actor_user_id": owner.id}
        )
        assert by_the_owner.json()["total"] == 1
        assert by_the_owner.json()["items"][0]["section"] == "SYSTEM"

        # Act
        response = await sales_client.get(
            f"{API_PREFIX}/operations/audit", params={"actor_user_id": owner.id}
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0, "skip": 0, "limit": 50}

    async def test_the_filter_also_covers_the_history_of_one_datum(
        self,
        sales_client: AsyncClient,
        owner_client: AsyncClient,
        session: AsyncSession,
        purchasing_user: User,
    ) -> None:
        """RF-15 does not become a way around RF-19: the section filter applies there too.

        The owner asks first, over the same route: without that control an empty
        answer would prove nothing, because a line that was never written also
        reads as `[]`.
        """
        # Arrange
        await record(
            session,
            actor_user_id=purchasing_user.id,
            section=BusinessSection.PURCHASING,
            entity_type="purchasing.invoice",
            entity_id="55",
        )
        route = f"{API_PREFIX}/operations/audit/purchasing.invoice/55"
        visible_to_the_owner = await owner_client.get(route)
        assert [entry["section"] for entry in visible_to_the_owner.json()] == ["PURCHASING"]

        # Act
        response = await sales_client.get(route)

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    async def test_an_anonymous_caller_reads_nothing(self, client: AsyncClient) -> None:
        """The history admits every session, which is not the same as admitting anyone."""
        # Act
        response = await client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        assert response.status_code == 401


class TestReadingTheHistory:
    """RF-09, RF-10, RF-12 and RF-13: what a line says and in what order."""

    async def test_it_is_read_newest_first(
        self, owner_client: AsyncClient, session: AsyncSession, owner: User
    ) -> None:
        """RF-13: the most recent change is the first row of the screen.

        The three rows are written **out of chronological order** on purpose.
        `id` is a sequence that grows with the insert, so rows written oldest
        first would come back in the same order under `ORDER BY id DESC` as
        under `ORDER BY occurred_at DESC`, and the test would keep passing if
        the date left the ordering. Only a scrambled write tells the two apart —
        and a scrambled write is the ordinary case, because `occurred_at` comes
        from the event, not from the clock of the insert.
        """
        # Arrange
        moments = [
            ("middle", datetime(2026, 8, 25, 9, 0, tzinfo=UTC)),
            ("oldest", datetime(2026, 8, 20, 9, 0, tzinfo=UTC)),
            ("newest", datetime(2026, 8, 28, 9, 0, tzinfo=UTC)),
        ]
        for label, moment in moments:
            await record(
                session,
                actor_user_id=owner.id,
                section=BusinessSection.SYSTEM,
                entity_id=label,
                occurred_at=moment,
            )

        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        assert response.status_code == 200
        assert [entry["entity_id"] for entry in response.json()["items"]] == [
            "newest",
            "middle",
            "oldest",
        ]

    async def test_a_line_says_who_changed_it_when_and_what_it_said_before(
        self, owner_client: AsyncClient, session: AsyncSession, sales_user: User
    ) -> None:
        """RF-09 and RF-10: the author, the moment, and the value that was there."""
        # Arrange
        moment = datetime(2026, 8, 27, 14, 30, tzinfo=UTC)
        await record(
            session,
            actor_user_id=sales_user.id,
            section=BusinessSection.SALES,
            old_value="1000",
            new_value="1200",
            occurred_at=moment,
        )

        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        entry = response.json()["items"][0]
        assert entry["actor_user_id"] == sales_user.id
        assert entry["actor_name"] == sales_user.name
        assert datetime.fromisoformat(entry["occurred_at"]) == moment
        assert entry["old_value"] == "1000"
        assert entry["new_value"] == "1200"

    async def test_the_reason_is_read_in_words_and_not_as_a_code(
        self, owner_client: AsyncClient, session: AsyncSession
    ) -> None:
        """RF-12: the history shows why, in the words the person picked."""
        # Arrange
        product_id = await a_logged_correction(session)

        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        entry = response.json()["items"][0]
        assert entry["entity_id"] == str(product_id)
        assert entry["reason_code"] == REASON
        assert entry["reason_label"] == REASON_LABEL
        assert entry["reason_detail"] == "la factura del proveedor dice 1200"

    async def test_an_unknown_reason_code_still_reads_as_something(
        self, owner_client: AsyncClient, session: AsyncSession, owner: User
    ) -> None:
        """RF-12 for a line the list has outlived: append-only means old codes stay."""
        # Arrange
        await record(
            session,
            actor_user_id=owner.id,
            section=BusinessSection.SYSTEM,
            reason_code="A_REASON_THAT_WAS_RETIRED",
        )

        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        assert response.json()["items"][0]["reason_label"] == "A_REASON_THAT_WAS_RETIRED"


class TestFilteringTheHistory:
    """RF-14: by person and by date range, and the timezone that decides a day."""

    @pytest.fixture
    async def two_authors_across_two_days(
        self, session: AsyncSession, owner: User, sales_user: User
    ) -> None:
        """Four lines: two people, on the two sides of a midnight in Buenos Aires."""
        for actor in (owner, sales_user):
            await record(
                session,
                actor_user_id=actor.id,
                section=BusinessSection.SYSTEM,
                entity_id=f"{actor.id}-late-on-the-29th",
                occurred_at=datetime(2026, 8, 29, 23, 30, tzinfo=ARGENTINA),
            )
            await record(
                session,
                actor_user_id=actor.id,
                section=BusinessSection.SYSTEM,
                entity_id=f"{actor.id}-early-on-the-30th",
                occurred_at=datetime(2026, 8, 30, 0, 30, tzinfo=ARGENTINA),
            )

    async def test_by_person(
        self,
        owner_client: AsyncClient,
        sales_user: User,
        two_authors_across_two_days: None,
    ) -> None:
        """RF-14: asking for one person's changes returns that person's changes."""
        # Act
        response = await owner_client.get(
            f"{API_PREFIX}/operations/audit", params={"actor_user_id": sales_user.id}
        )

        # Assert
        body = response.json()
        assert body["total"] == 2
        assert {entry["actor_user_id"] for entry in body["items"]} == {sales_user.id}

    async def test_by_person_and_date_range_together(
        self,
        owner_client: AsyncClient,
        sales_user: User,
        two_authors_across_two_days: None,
    ) -> None:
        """RF-14 as the screen offers it: one person inside one range, and only that."""
        # Act
        response = await owner_client.get(
            f"{API_PREFIX}/operations/audit",
            params={
                "actor_user_id": sales_user.id,
                "since": "2026-08-30T00:00:00",
                "until": "2026-08-30T23:59:59",
            },
        )

        # Assert
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["entity_id"] == f"{sales_user.id}-early-on-the-30th"

    async def test_a_day_starts_on_the_shops_clock_and_not_on_utc(
        self, owner_client: AsyncClient, two_authors_across_two_days: None
    ) -> None:
        """RF-14 where the timezone shows: `desde el 30` is midnight in Buenos Aires.

        The line at 23:30 of the 29th is 02:30 UTC of the 30th. Read as UTC it
        would be inside the range — three hours of the wrong day, which is the
        bug `app/shared/time.py` exists to prevent.
        """
        # Act
        response = await owner_client.get(
            f"{API_PREFIX}/operations/audit", params={"since": "2026-08-30T00:00:00"}
        )

        # Assert
        body = response.json()
        assert body["total"] == 2
        assert all("early-on-the-30th" in entry["entity_id"] for entry in body["items"])

    async def test_the_end_of_the_range_is_the_shops_clock_too(
        self, owner_client: AsyncClient, two_authors_across_two_days: None
    ) -> None:
        """The other edge: `hasta el 29` keeps the 29th and drops the 30th."""
        # Act
        response = await owner_client.get(
            f"{API_PREFIX}/operations/audit", params={"until": "2026-08-29T23:59:59"}
        )

        # Assert
        body = response.json()
        assert body["total"] == 2
        assert all("late-on-the-29th" in entry["entity_id"] for entry in body["items"])

    async def test_an_offset_the_caller_wrote_is_honoured_as_written(
        self, owner_client: AsyncClient, two_authors_across_two_days: None
    ) -> None:
        """A moment that already carries an offset is not reinterpreted."""
        # Act — 03:00Z is exactly midnight in Buenos Aires
        response = await owner_client.get(
            f"{API_PREFIX}/operations/audit", params={"since": "2026-08-30T03:00:00+00:00"}
        )

        # Assert
        body = response.json()
        assert body["total"] == 2
        assert all("early-on-the-30th" in entry["entity_id"] for entry in body["items"])

    async def test_a_range_that_matches_nothing_is_an_empty_page(
        self, owner_client: AsyncClient, two_authors_across_two_days: None
    ) -> None:
        """The empty case, which is what a screen shows when a filter is too narrow."""
        # Act
        response = await owner_client.get(
            f"{API_PREFIX}/operations/audit",
            params={"since": "2026-09-01T00:00:00", "until": "2026-09-02T00:00:00"},
        )

        # Assert
        assert response.json() == {"items": [], "total": 0, "skip": 0, "limit": 50}


class TestTheHistoryOfOneDatum:
    """RF-15: standing on a corrected datum, its history is one call away."""

    async def test_it_returns_that_datums_changes_and_no_others(
        self, owner_client: AsyncClient, session: AsyncSession, owner: User
    ) -> None:
        """The route is keyed by the publisher's own vocabulary, type and id.

        The other datum is named rather than numbered: a numeric literal could
        collide with `product_id`, which comes out of a sequence shared with
        every product any earlier test created, and the failure would look like
        a bug in the filter instead of an accident of ordering.
        """
        # Arrange
        product_id = await a_logged_correction(session, actor_user_id=owner.id)
        await record(
            session,
            actor_user_id=owner.id,
            section=BusinessSection.SALES,
            entity_type="catalog.product_price",
            entity_id="another-datum",
        )

        # Act
        response = await owner_client.get(
            f"{API_PREFIX}/operations/audit/catalog.product_price/{product_id}"
        )

        # Assert
        assert response.status_code == 200
        entries = response.json()
        assert [entry["entity_id"] for entry in entries] == [str(product_id)]
        assert entries[0]["action"] == AuditAction.CORRECTED.value
        assert entries[0]["actor_name"] == owner.name

    async def test_two_changes_to_the_same_datum_come_back_newest_first(
        self, owner_client: AsyncClient, session: AsyncSession, owner: User
    ) -> None:
        """RF-13 holds inside a datum's own history as well.

        The newer change is written first, so the expected answer is the
        opposite of the insertion order: ordering by `id` alone would return
        `["1100", "1300"]` and fail here.
        """
        # Arrange
        for day, value in ((26, "1300"), (20, "1100")):
            await record(
                session,
                actor_user_id=owner.id,
                section=BusinessSection.SALES,
                entity_id="77",
                new_value=value,
                occurred_at=datetime(2026, 8, day, 10, 0, tzinfo=UTC),
            )

        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/audit/catalog.product_price/77")

        # Assert
        assert [entry["new_value"] for entry in response.json()] == ["1300", "1100"]

    async def test_a_datum_nobody_touched_answers_an_empty_history(
        self, owner_client: AsyncClient
    ) -> None:
        """Empty rather than 404: the datum exists, its history is simply blank."""
        # Act
        response = await owner_client.get(
            f"{API_PREFIX}/operations/audit/catalog.product_price/404404"
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == []
