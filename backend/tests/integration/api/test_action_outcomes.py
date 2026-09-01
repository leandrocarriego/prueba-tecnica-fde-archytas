"""RF-22: an action that failed says so, and says why.

The single screen of loads and corrections (RF-20) is a launcher — the result
of an action is shown where the action is actually done. What can be checked
from here is the half the screen depends on: that a manual action which cannot
be applied comes back as a **refusal with a readable reason**, not as a silent
success and not as a 500.

That is the risk RF-22 is written against. All five refusals below are raised
deep inside a service, and any one of them could have arrived as an unhandled
exception — a stack trace, a generic "Internal Server Error", and a person
looking at a screen that never told them their correction did not happen.

The envelope itself belongs to `test_error_envelope.py`; this file reads the
message out of it and asks whether it explains anything. The happy path is here
too, so what is being tested is the difference between the two answers and not
just the sad one.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Correction, Product
from app.modules.catalog.service import CatalogService
from app.modules.identity.models import User
from app.modules.operations import service as operations_service
from app.modules.triage.models import ExceptionCase
from app.modules.triage.service import UNREADABLE_ROW, TriageService
from app.shared.corrections import CorrectionReason
from app.shared.parameters import spec_for
from app.shared.sections import BusinessSection
from tests.conftest import API_PREFIX
from tests.factories.catalog_factory import ProductFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

CATALOG = f"{API_PREFIX}/catalog"
PARAMETERS = f"{API_PREFIX}/operations/parameters"
UPDATES = f"{API_PREFIX}/price-updates"
TRIAGE = f"{API_PREFIX}/triage"

REASON = CorrectionReason.PORTAL_WAS_WRONG.value
INTERVAL = "price_update.interval_hours"
IDLE = "access.session_idle_minutes"

# An id no fixture creates, for the two routes that have to answer "that is not
# here" instead of inventing something to act on.
ABSENT = 999_999

# The moment the correction below was made, stamped rather than left to the
# clock, and picked to sit on the far side of midnight in UTC: 01:30 of the 13th
# in UTC is 22:30 of the **12th** standing in the shop. The refusal says
# «12/08/2026», so a date that ever stops being read on the business clock fails
# here instead of quietly telling somebody who works in the evening that their
# colleague corrected the price tomorrow.
CORRECTED_AT = datetime(2026, 8, 13, 1, 30, tzinfo=UTC)

# What the person reads, word for word, when a standing correction does not let
# their amount through. Pinned whole and not by keyword on purpose: «operación
# rechazada» would pass a 409 and pass any assertion looking for the word
# «corrección», and would leave them exactly where the silent success left
# them — knowing something happened and not what to do about it (RF-22).
REFUSAL = (
    "El precio de este producto está corregido a mano desde el 12/08/2026 y dice 1200, "
    "así que no se guardó el importe que cargaste y el caso sigue en la cola. "
    "Si ese es el precio correcto, cargá ese mismo importe y el caso se cierra sin tocar "
    "la corrección. Si no lo es, hay que cambiar la corrección, con un motivo, en la ficha "
    "del producto, y volver a cargarlo acá."
)


def failure(response: Response) -> dict[str, Any]:
    """The error the API answered, having checked it can be read out loud.

    Only what RF-22 needs: a type the screen can branch on and a message with
    words in it. The exhaustive check of the envelope's shape is
    `test_error_envelope.py`, and a second copy of it here would be two files
    to edit the day the shape moves.
    """
    error = response.json()["error"]
    assert isinstance(error["message"], str) and error["message"].strip(), (
        "the action failed with an empty message: whoever ran it is told nothing at all (RF-22)."
    )
    return error


@pytest.fixture
async def product(session: AsyncSession) -> Product:
    """A product as the daily list left it: brought from the portal, priced.

    Local to this file on purpose — the suite's shared fixtures are being
    edited by other work in parallel, and this one is three lines.
    """
    return await ProductFactory.create(
        session, description="Bulón hexagonal M8", price=Decimal("1500.00")
    )


async def a_pending_row(
    session: AsyncSession,
    product: Product,
    *,
    corrected_to: str,
    by: User,
    corrected_at: datetime = CORRECTED_AT,
) -> int:
    """A row nobody could read, waiting, over a price somebody already corrected.

    Everything is committed before it is handed over, the way the run that
    opened the case committed it hours before anybody looked at the queue.
    Without that, a resolution that gets rolled back would take its own case
    down with it and there would be nothing left to ask about.

    The moment of the correction is written on the row instead of left to
    `datetime.now()`: the refusal reads a date out loud, and a date that moves
    with the day the suite happens to run cannot be pinned word for word.
    """
    await CatalogService(session).apply_correction(
        product_id=product.id,
        field="price",
        value=corrected_to,
        reason_code=REASON,
        reason_detail=None,
        actor_user_id=by.id,
    )
    correction = await session.scalar(select(Correction).order_by(Correction.id.desc()))
    assert correction is not None
    correction.corrected_at = corrected_at
    await TriageService(session).open_case(
        kind=UNREADABLE_ROW,
        section=BusinessSection.PURCHASING,
        reason="La fila no se pudo leer",
        payload={"product_code": product.code, "excerpt": f"{product.code};;;"},
        key=product.code,
    )
    case_id = await session.scalar(select(ExceptionCase.id).order_by(ExceptionCase.id.desc()))
    assert case_id is not None
    await session.commit()
    return case_id


@pytest.fixture
def dispatched(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[int]]:
    """The extraction `POST /price-updates` ends with, recorded instead of queued.

    The suite's autouse `no_broker` covers the handlers that queue work; this
    dispatch is called straight from `OperationsService`, so it needs its own
    seam or the request reaches for RabbitMQ, which the suite runs without.
    """
    calls: list[int] = []
    monkeypatch.setattr(operations_service, "dispatch_price_extraction", calls.append)
    yield calls


class TestACorrectionThatCannotBeApplied:
    """The two ways a correction is refused before it changes anything."""

    async def test_a_reason_outside_the_list_is_refused_saying_so(
        self, sales_client: AsyncClient, product: Product
    ) -> None:
        """RF-11 and RF-22: no reason, no correction — and the screen is told why.

        The code is well-formed, so the schema lets it through and the refusal
        comes from the service. It has to arrive as a 422 that names the reason
        rather than as an unhandled `ValueError` off the enum.
        """
        # Arrange
        payload = {
            "field": "description",
            "value": "Bulón hexagonal M8 zincado",
            "reason_code": "PORQUE_ME_PARECE",
        }

        # Act
        response = await sales_client.post(
            f"{CATALOG}/products/{product.id}/corrections", json=payload
        )

        # Assert
        assert response.status_code == 422
        error = failure(response)
        assert error["type"] == "ValidationError"
        assert "motivo" in error["message"].lower(), (
            f"the refusal does not say the reason is what is missing: {error['message']!r}"
        )
        assert error["details"]["reason_code"] == "PORQUE_ME_PARECE"

    async def test_the_value_is_left_alone_when_the_reason_is_refused(
        self, sales_client: AsyncClient, product: Product
    ) -> None:
        """Failed is failed: a refusal that half-applied would be the worst answer.

        The status is asserted before the value is read back. Without it the
        test also passes on a 401 or a 500 — the description would not have
        moved either, and the name of this test would stop being true.
        """
        # Arrange
        original = product.description

        # Act
        response = await sales_client.post(
            f"{CATALOG}/products/{product.id}/corrections",
            json={
                "field": "description",
                "value": "Bulón hexagonal M8 zincado",
                "reason_code": "PORQUE_ME_PARECE",
            },
        )

        # Assert
        assert response.status_code == 422
        listing = (
            await sales_client.get(f"{API_PREFIX}/prices", params={"q": product.code})
        ).json()
        assert listing["items"][0]["description"] == original

    async def test_correcting_a_product_that_does_not_exist_is_a_404(
        self, sales_client: AsyncClient
    ) -> None:
        """The field and the reason are valid, so the refusal is about the product."""
        # Arrange
        payload = {
            "field": "description",
            "value": "Un producto que no está",
            "reason_code": REASON,
        }

        # Act
        response = await sales_client.post(f"{CATALOG}/products/{ABSENT}/corrections", json=payload)

        # Assert
        assert response.status_code == 404
        error = failure(response)
        assert error["type"] == "NotFoundError"
        assert error["details"]["product_id"] == ABSENT


class TestUndoingSomethingThatIsNotThere:
    """RF-22: nothing to undo is a readable refusal, not a crash."""

    async def test_undoing_a_correction_that_does_not_exist_is_a_404(
        self, owner_client: AsyncClient
    ) -> None:
        """An id no row carries, refused by type and by the id that was sent.

        Not RF-33: a datum loaded entirely by hand is a different arrangement
        — it opens no correction at all — and `test_correction_reversal.py`
        is where that one is checked.
        """
        # Act
        response = await owner_client.delete(f"{CATALOG}/corrections/{ABSENT}")

        # Assert
        assert response.status_code == 404
        error = failure(response)
        assert error["type"] == "NotFoundError"
        assert error["details"]["correction_id"] == ABSENT


class TestAParameterOutsideItsRange:
    """RF-06 and RF-22 together: refused, and the message carries the range."""

    async def test_the_refusal_says_between_which_values_it_has_to_be(
        self, owner_client: AsyncClient
    ) -> None:
        """A rejection without the bounds leaves the owner guessing the next value.

        The bounds are read from the catalog rather than typed here: what is
        being checked is that the message and the rule that produced it come
        from the same declaration, so moving a bound cannot leave a sentence
        describing the old one.

        The whole `range_text` is asserted and not the two numbers apart,
        because for this parameter «1» is a substring of «168»: a message that
        lost the lower bound would satisfy the looser check.
        """
        # Arrange
        spec = spec_for(INTERVAL)

        # Act
        response = await owner_client.put(
            PARAMETERS, json={"items": [{"key": INTERVAL, "value": 0}]}
        )

        # Assert
        assert response.status_code == 422
        error = failure(response)
        assert error["type"] == "ValidationError"
        assert spec.range_text in error["message"], (
            f"the refusal does not carry the range «{spec.range_text}»: {error['message']!r}"
        )
        assert error["details"]["key"] == INTERVAL

    async def test_nothing_is_stored_when_the_value_is_refused(
        self, owner_client: AsyncClient
    ) -> None:
        """A refusal is not a half-applied change: the old value still governs.

        The single-item case, which the panel's own suite also covers
        (`test_parameters_panel.py::test_a_refused_value_leaves_the_parameter_where_it_was`).
        The batch below is the one nobody else asks.
        """
        # Arrange
        spec = spec_for(INTERVAL)

        # Act
        response = await owner_client.put(
            PARAMETERS, json={"items": [{"key": INTERVAL, "value": 0}]}
        )

        # Assert
        assert response.status_code == 422
        parameters = (await owner_client.get(PARAMETERS)).json()
        interval = next(item for item in parameters if item["key"] == INTERVAL)
        assert interval["value"] == spec.stored_initial
        assert interval["changed_at"] is None

    async def test_one_value_out_of_range_takes_the_whole_batch_with_it(
        self, owner_client: AsyncClient
    ) -> None:
        """The set is written in one transaction or not at all.

        A good value beside a bad one, which is how the panel is actually used:
        the owner edits what they came to edit and sends everything back. The
        existing batch test refuses on a key the catalog does not know, so it
        never reaches the range check — a value refused *after* its neighbour
        was already accepted would leave the panel half applied and no test
        would say so.
        """
        # Arrange
        interval = spec_for(INTERVAL)
        idle = spec_for(IDLE)

        # Act
        response = await owner_client.put(
            PARAMETERS,
            json={"items": [{"key": IDLE, "value": 30}, {"key": INTERVAL, "value": 0}]},
        )

        # Assert
        assert response.status_code == 422
        stored = {item["key"]: item for item in (await owner_client.get(PARAMETERS)).json()}
        assert stored[IDLE]["value"] == idle.stored_initial, (
            "the good value of the batch was written and the bad one was refused: "
            "the panel landed half applied."
        )
        assert stored[IDLE]["changed_at"] is None
        assert stored[INTERVAL]["value"] == interval.stored_initial
        assert stored[INTERVAL]["changed_at"] is None


class TestAskingForSomethingThatIsAlreadyRunning:
    """The one refusal that is not the caller's mistake, and still has to be said."""

    async def test_a_second_price_update_is_refused_with_the_run_in_flight(
        self, purchasing_client: AsyncClient, dispatched: list[int]
    ) -> None:
        """A 409, and the id of the run to follow — so the screen says *why* not.

        "Ya se está actualizando" is a different message from "no se pudo", and
        an action that failed for a reason the person can act on is exactly
        what RF-22 is asking the platform to tell them.
        """
        # Arrange
        first = (await purchasing_client.post(UPDATES)).json()

        # Act
        response = await purchasing_client.post(UPDATES)

        # Assert
        assert response.status_code == 409
        error = failure(response)
        assert error["type"] == "ConflictError"
        assert error["details"]["job_run_id"] == first["job_run_id"]
        # Refused means not started: the second call queued nothing.
        assert dispatched == [first["job_run_id"]]


class TestAnActionThatIsApplied:
    """The other half of RF-22, so the tests are not all about failing."""

    async def test_a_correction_comes_back_applied_with_what_it_replaced(
        self, sales_client: AsyncClient, product: Product
    ) -> None:
        """Applied, and the answer carries enough for the screen to say so.

        The correction's own id, the value now in force, and what the portal
        had said — which is what tells a success apart from a refusal without
        a second request to go and look.
        """
        # Arrange
        original = product.description
        payload = {
            "field": "description",
            "value": "Bulón hexagonal M8 zincado",
            "reason_code": REASON,
            "reason_detail": "Vino cortado desde el portal",
        }

        # Act
        response = await sales_client.post(
            f"{CATALOG}/products/{product.id}/corrections", json=payload
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["correction_id"] is not None
        assert body["status"] == "ACTIVE"
        assert body["value"] == payload["value"]
        assert body["portal_value"] == original


class TestALoadAStandingCorrectionDoesNotLetThrough:
    """The refusal RF-22 was written for, in the one place it used to be missing.

    Resolving a case whose amount a correction holds back is the action that,
    until this class existed, came back **200 and «Caso resuelto»** over a price
    that was never written and never logged. It is the exact shape RF-22 names —
    somebody looking at a screen that never told them their load did not
    happen — and it reached them through the browser, which is why it is asked
    here over HTTP and not only against the service.

    Three things are checked here, and the last is the one the service test
    cannot reach: the sentence, the payload the card builds its way out of, and
    that the case is still in the queue afterwards. The rollback in the middle
    of that one is doing what `get_session` does in production and what this
    harness does not: it closes the request's session and drops what nobody
    committed (`tests/architecture/test_writes_are_committed.py` tells that
    story in full).

    Then the two ways out the sentence names, walked end to end, because a
    refusal that leaves the case unclosable is the same silent loss wearing a
    409: the person would be told to do something, do it, and find the row still
    there every morning for ever. Emptying it is `PRICES` in writing and
    changing the correction is `PRODUCT_CATALOG` in writing, so the second walk
    takes two clients — which is the point, and is why the card says whose door
    it is.

    The last test is the same action **without** a correction underneath. It is
    here so the file measures the difference between the two answers rather than
    only the unhappy one: a guard written a line too wide would turn the review
    queue into a screen that refuses every price, and every other test in this
    class would still pass.
    """

    async def test_the_refusal_is_the_sentence_the_person_reads(
        self, purchasing_client: AsyncClient, session: AsyncSession, product: Product, owner: User
    ) -> None:
        """RF-22: the amount does not land, and whoever typed it is told why.

        Word for word, and that is the test. This screen used to answer 200 and
        «Caso resuelto» over an amount it never wrote, so the bar the sentence
        has to clear is not "an error came back" — it is that the person can
        tell what happened, when it was decided, what the price says instead,
        and what they would have to do to move it.

        The date doubles as the shop-clock check: the correction is stamped at
        01:30 UTC of the 13th, and what a person in Buenos Aires reads is the
        12th.
        """
        # Arrange
        case_id = await a_pending_row(session, product, corrected_to="1200", by=owner)

        # Act
        response = await purchasing_client.post(
            f"{TRIAGE}/cases/{case_id}/resolution",
            json={"decision": {"product_code": product.code, "price": "1500"}, "remember": True},
        )

        # Assert
        assert response.status_code == 409
        error = failure(response)
        assert error["type"] == "ConflictError"
        assert error["message"] == REFUSAL

    async def test_the_refusal_carries_what_the_card_needs_to_offer_a_way_out(
        self, purchasing_client: AsyncClient, session: AsyncSession, product: Product, owner: User
    ) -> None:
        """The whole payload, key by key, because each one is somebody's way out.

        `correction_id` is what tells this refusal apart from every other one
        that names a product, and it is what the card hangs its links on;
        `product_id` is where those links go; `corrected_by_name` is what the
        decision of 2026-08-31 asked for in so many words — «hay una corrección
        de Julián» — resolved from `corrected_by_user_id` by the route, because
        `catalog` says the id and stops rather than take the import the Artículo
        IV forbids; `rejected_value` is what makes the refusal explain itself to
        whoever meets it in a log instead of on a screen.

        Asserted as one equality rather than key by key: a `details` that
        quietly drops one of these leaves the card with a dead link and nothing
        on the page saying so, and an equality is the only shape that notices.
        """
        # Arrange
        case_id = await a_pending_row(session, product, corrected_to="1200", by=owner)
        correction_id = await session.scalar(select(Correction.id).order_by(Correction.id.desc()))

        # Act
        response = await purchasing_client.post(
            f"{TRIAGE}/cases/{case_id}/resolution",
            json={"decision": {"product_code": product.code, "price": "1500"}, "remember": True},
        )

        # Assert
        assert response.status_code == 409
        assert failure(response)["details"] == {
            "product_id": product.id,
            "product_code": product.code,
            "field": "price",
            "correction_id": correction_id,
            "corrected_value": "1200",
            "corrected_at": CORRECTED_AT.isoformat(),
            "corrected_by_user_id": owner.id,
            "corrected_by_name": owner.name,
            "rejected_value": "1500",
        }

    async def test_the_case_is_still_pending_after_the_refusal(
        self, purchasing_client: AsyncClient, session: AsyncSession, product: Product, owner: User
    ) -> None:
        """A case that was not resolved stays in the queue for whoever comes back.

        This is what makes the refusal worth anything: telling somebody the
        price was not saved while quietly emptying their case would swap one
        silent loss for another.
        """
        # Arrange
        case_id = await a_pending_row(session, product, corrected_to="1200", by=owner)

        # Act
        refused = await purchasing_client.post(
            f"{TRIAGE}/cases/{case_id}/resolution",
            json={"decision": {"product_code": product.code, "price": "1500"}, "remember": True},
        )
        await session.rollback()

        # Assert
        assert refused.status_code == 409
        queue = (await purchasing_client.get(f"{TRIAGE}/cases")).json()
        assert [case["id"] for case in queue["items"]] == [case_id]
        assert queue["items"][0]["status"] == "PENDING"
        # Narrowed to this kind: the installation ships with equivalences
        # already seeded as rules, so the whole list was never going to be empty.
        rules = await purchasing_client.get(f"{TRIAGE}/rules", params={"kind": UNREADABLE_ROW})
        assert rules.json() == []

    async def test_confirming_the_amount_in_force_empties_the_case(
        self, purchasing_client: AsyncClient, session: AsyncSession, product: Product, owner: User
    ) -> None:
        """The first way out the refusal names, taken word for word.

        The person reads «Si ese es el precio correcto, cargá ese mismo
        importe», types 1200, and the case leaves the queue. Nothing is
        overwritten — the correction is exactly where it was and the price still
        says 1200 — because there was nothing to overwrite: the amount they
        confirmed is the amount in force.

        Without this the refusal would be a wall. `TriageService.resolve` is the
        only road to `RESOLVED`, and it goes through the write that refuses, so
        a row whose price a correction holds would sit in the queue for ever,
        counted every morning, no matter what anybody did about it.
        """
        # Arrange
        case_id = await a_pending_row(session, product, corrected_to="1200", by=owner)
        correction_id = await session.scalar(select(Correction.id).order_by(Correction.id.desc()))

        # Act
        response = await purchasing_client.post(
            f"{TRIAGE}/cases/{case_id}/resolution",
            json={"decision": {"product_code": product.code, "price": "1200"}, "remember": False},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "RESOLVED"
        assert (await purchasing_client.get(f"{TRIAGE}/cases")).json()["items"] == []
        history = (await purchasing_client.get(f"{API_PREFIX}/prices/{product.id}/history")).json()
        assert Decimal(history["price"]) == Decimal("1200")
        assert [correction["correction_id"] for correction in history["corrections"]] == [
            correction_id
        ]

    async def test_changing_the_correction_lets_the_refused_amount_through(
        self,
        purchasing_client: AsyncClient,
        owner_client: AsyncClient,
        session: AsyncSession,
        owner: User,
    ) -> None:
        """The other way out, and the one the refusal used to promise falsely.

        The whole round trip, through the API, with the two roles the two doors
        belong to: purchasing loads 1500 and is refused, the owner changes the
        correction to 1500 «con un motivo, en la ficha del producto», purchasing
        loads 1500 again and the case leaves the queue.

        Before the equality above existed this ended in the same 409 the second
        time — a **replaced** correction is still a correction in force, so the
        old sentence sent people through a door that came back to where they
        started. That is why the walk is asserted from end to end and not the
        two halves separately: what was broken was the joint.

        The 403 in the middle is the reason the sentence says «hay que cambiar
        la corrección» and never «podés cambiarla»: whoever empties this queue
        is exactly who may not touch a correction. A message written the other
        way would be telling the person who reads it to do the one thing the
        API will not let them do, and the screen is what has to say whose door
        it is.

        Its own product and its own case, built here rather than from the
        module-level fixture, because the correction has to be made through the
        API for the round trip to mean anything and the fixture's is stamped by
        hand for the date in the sentence.
        """
        # Arrange
        mine = await ProductFactory.create(session, code="ROUND-TRIP", price=1000)
        # Read out before the act: the rollback in the middle expires every
        # loaded object, and reading an id off one afterwards is a lazy load
        # firing outside the async context — a `MissingGreenlet` where a test
        # was only trying to build a URL.
        product_id, code = mine.id, mine.code
        await CatalogService(session).apply_correction(
            product_id=product_id,
            field="price",
            value="1200",
            reason_code=REASON,
            reason_detail=None,
            actor_user_id=owner.id,
        )
        await TriageService(session).open_case(
            kind=UNREADABLE_ROW,
            section=BusinessSection.PURCHASING,
            reason="La fila no se pudo leer",
            payload={"product_code": code, "excerpt": f"{code};;;"},
            key=code,
        )
        case_id = await session.scalar(select(ExceptionCase.id).order_by(ExceptionCase.id.desc()))
        await session.commit()
        load = {"decision": {"product_code": code, "price": "1500"}, "remember": False}

        # Act
        correction = {"field": "price", "value": "1500", "reason_code": REASON}
        refused = await purchasing_client.post(f"{TRIAGE}/cases/{case_id}/resolution", json=load)
        await session.rollback()
        forbidden = await purchasing_client.post(
            f"{CATALOG}/products/{product_id}/corrections", json=correction
        )
        changed = await owner_client.post(
            f"{CATALOG}/products/{product_id}/corrections", json=correction
        )
        accepted = await purchasing_client.post(f"{TRIAGE}/cases/{case_id}/resolution", json=load)

        # Assert
        assert refused.status_code == 409
        assert forbidden.status_code == 403
        assert changed.status_code == 200
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "RESOLVED"
        assert (await purchasing_client.get(f"{TRIAGE}/cases")).json()["items"] == []

    async def test_the_same_load_goes_through_when_nothing_stands_on_the_price(
        self, purchasing_client: AsyncClient, session: AsyncSession, product: Product
    ) -> None:
        """RF-29 still works: the refusal is a door with a condition, not a wall.

        The same case, the same screen, the same amount typed by the same
        person — only without a correction underneath. Without this test the
        cheapest way to make every assertion above pass would be to refuse
        every price that comes out of the queue, and the queue would stop being
        emptiable by the one action it exists for.
        """
        # Arrange
        await TriageService(session).open_case(
            kind=UNREADABLE_ROW,
            section=BusinessSection.PURCHASING,
            reason="La fila no se pudo leer",
            payload={"product_code": product.code, "excerpt": f"{product.code};;;"},
            key=product.code,
        )
        case_id = await session.scalar(select(ExceptionCase.id).order_by(ExceptionCase.id.desc()))
        await session.commit()

        # Act
        response = await purchasing_client.post(
            f"{TRIAGE}/cases/{case_id}/resolution",
            json={"decision": {"product_code": product.code, "price": "1800"}, "remember": False},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "RESOLVED"
        history = await purchasing_client.get(f"{API_PREFIX}/prices/{product.id}/history")
        assert Decimal(history.json()["price"]) == Decimal("1800")
