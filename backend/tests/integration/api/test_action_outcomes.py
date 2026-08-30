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
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Product
from app.modules.operations import service as operations_service
from app.shared.corrections import CorrectionReason
from app.shared.parameters import spec_for
from tests.conftest import API_PREFIX
from tests.factories.catalog_factory import ProductFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

CATALOG = f"{API_PREFIX}/catalog"
PARAMETERS = f"{API_PREFIX}/operations/parameters"
UPDATES = f"{API_PREFIX}/price-updates"

REASON = CorrectionReason.PORTAL_WAS_WRONG.value
INTERVAL = "price_update.interval_hours"
IDLE = "access.session_idle_minutes"

# An id no fixture creates, for the two routes that have to answer "that is not
# here" instead of inventing something to act on.
ABSENT = 999_999


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
