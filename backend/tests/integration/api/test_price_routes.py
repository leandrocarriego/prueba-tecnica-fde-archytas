"""The eleven routes of the price update, over HTTP.

Two things are checked for each: **who** may call it — the spec is explicit,
and asking the portal for a list is not a read any role can do — and that what
comes back is what the screen needs.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.operations import service as operations_service
from app.modules.portal import handlers as portal_handlers
from app.modules.portal.service import PortalService
from tests.conftest import API_PREFIX
from tests.factories.portal_factory import FakePortal, broken_list_bytes

pytestmark = [pytest.mark.integration, pytest.mark.database]

PRICES = f"{API_PREFIX}/prices"
UPDATES = f"{API_PREFIX}/price-updates"
TRIAGE = f"{API_PREFIX}/triage"


class Recorder:
    """Stands in for anything that would reach the broker."""

    def __init__(self) -> None:
        self.calls: list[Any] = []

    def apply_async(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)

    def __call__(self, *args: Any) -> None:
        self.calls.append(args)


@pytest.fixture(autouse=True)
def no_broker(monkeypatch: pytest.MonkeyPatch) -> Iterator[Recorder]:
    """The suite runs with RabbitMQ down, like it runs with the portal down."""
    recorder = Recorder()
    monkeypatch.setattr(portal_handlers, "extract_product_history", recorder)
    monkeypatch.setattr(operations_service, "dispatch_price_extraction", recorder)
    yield recorder


@pytest.fixture
async def a_list_was_extracted(session: AsyncSession) -> None:
    """A first list, then one that brings a broken row and an unknown product."""
    await PortalService(session, reader_factory=FakePortal()).extract_price_list()
    await PortalService(
        session, reader_factory=FakePortal(price_list=broken_list_bytes())
    ).extract_price_list()


class TestThePricesScreen:
    """RF-04: code, description and the price in force."""

    async def test_sales_can_read_the_prices(
        self, sales_client: AsyncClient, a_list_was_extracted: None
    ) -> None:
        """These are the supplier's prices, not the company's margins."""
        # Act
        response = await sales_client.get(PRICES)

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 100
        first = body["items"][0]
        assert {"code", "description", "price"} <= set(first)

    async def test_it_can_be_filtered_down_to_the_rises_worth_looking_at(
        self, purchasing_client: AsyncClient, a_list_was_extracted: None
    ) -> None:
        """RF-25: the screen filters on the flag rather than recomputing it."""
        # Act
        response = await purchasing_client.get(PRICES, params={"highlighted": True})

        # Assert
        assert response.status_code == 200
        assert all(item["is_highlighted"] for item in response.json()["items"])

    async def test_it_can_be_searched(
        self, sales_client: AsyncClient, a_list_was_extracted: None
    ) -> None:
        """A hundred products is already too many to scroll."""
        # Act
        response = await sales_client.get(PRICES, params={"q": "COR-0001"})

        # Assert
        assert response.status_code == 200
        assert response.json()["total"] == 1


class TestTheProductPage:
    """RF-23 and RF-24: how a price moved, and against last month."""

    async def test_it_returns_the_points_of_the_product(
        self, sales_client: AsyncClient, session: AsyncSession, a_list_was_extracted: None
    ) -> None:
        """Every authenticated role can look at it."""
        # Arrange
        listing = (await sales_client.get(PRICES, params={"q": "COR-0001"})).json()
        product_id = listing["items"][0]["product_id"]

        # Act
        response = await sales_client.get(f"{PRICES}/{product_id}/history")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == "COR-0001"
        assert len(body["points"]) >= 1

    async def test_a_product_that_does_not_exist_is_a_404(self, sales_client: AsyncClient) -> None:
        """And it comes back in the same error envelope as everything else."""
        # Act
        response = await sales_client.get(f"{PRICES}/999999/history")

        # Assert
        assert response.status_code == 404
        assert response.json()["error"]["type"] == "NotFoundError"


class TestAskingForAnUpdateOverHttp:
    """RF-14 and RF-15, with the roles the spec names."""

    async def test_purchasing_can_ask_for_one(self, purchasing_client: AsyncClient) -> None:
        """Marcela needs the list now to check an invoice now."""
        # Act
        response = await purchasing_client.post(UPDATES)

        # Assert
        assert response.status_code == 202
        assert response.json()["job_run_id"] > 0

    async def test_sales_cannot(self, sales_client: AsyncClient) -> None:
        """Asking is knocking on a third party's door, and that is not a read."""
        # Act
        response = await sales_client.post(UPDATES)

        # Assert
        assert response.status_code == 403

    async def test_a_second_request_answers_409_with_the_run_in_flight(
        self, purchasing_client: AsyncClient
    ) -> None:
        """RF-15: it says which one is running, so the screen can follow it."""
        # Arrange
        first = (await purchasing_client.post(UPDATES)).json()

        # Act
        response = await purchasing_client.post(UPDATES)

        # Assert
        assert response.status_code == 409
        assert response.json()["error"]["details"]["job_run_id"] == first["job_run_id"]

    async def test_the_run_can_be_followed_by_its_id(self, purchasing_client: AsyncClient) -> None:
        """RF-16: whoever asked finds out how it ended, however it ended."""
        # Arrange
        requested = (await purchasing_client.post(UPDATES)).json()

        # Act
        response = await purchasing_client.get(f"{UPDATES}/{requested['job_run_id']}")

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "RUNNING"

    async def test_every_role_can_see_whether_the_update_is_alive(
        self, sales_client: AsyncClient
    ) -> None:
        """RF-09 and RF-11 are on the prices screen, which sales also opens."""
        # Act
        response = await sales_client.get(f"{UPDATES}/status")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["interval_hours"] == 12
        assert body["is_stalled"] is False


class TestTheSettings:
    """H4: only the owner decides how often and what a big rise is."""

    async def test_the_owner_reads_them(self, owner_client: AsyncClient) -> None:
        """RF-20: the starting values, until somebody changes them."""
        # Act
        response = await owner_client.get(f"{UPDATES}/settings")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"interval_hours": 12, "highlight_threshold_pct": "10"}

    async def test_the_owner_changes_them(self, owner_client: AsyncClient) -> None:
        """RF-18 and RF-19."""
        # Act
        response = await owner_client.put(
            f"{UPDATES}/settings",
            json={"interval_hours": 8, "highlight_threshold_pct": 12},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["interval_hours"] == 8

    async def test_purchasing_cannot(self, purchasing_client: AsyncClient) -> None:
        """These values decide how the platform behaves: they are the owner's."""
        # Act
        response = await purchasing_client.put(
            f"{UPDATES}/settings",
            json={"interval_hours": 8, "highlight_threshold_pct": 12},
        )

        # Assert
        assert response.status_code == 403

    async def test_an_impossible_frequency_is_rejected(self, owner_client: AsyncClient) -> None:
        """Querying a third party's portal every minute is not a setting."""
        # Act
        response = await owner_client.put(
            f"{UPDATES}/settings",
            json={"interval_hours": 0, "highlight_threshold_pct": 12},
        )

        # Assert
        assert response.status_code == 422


class TestTheReviewScreen:
    """H7 and H8 over HTTP: the queue belongs to purchasing and to the owner."""

    async def test_purchasing_sees_what_was_set_aside(
        self, purchasing_client: AsyncClient, a_list_was_extracted: None
    ) -> None:
        """RF-26: each case with the reason it was set aside."""
        # Act
        response = await purchasing_client.get(f"{TRIAGE}/cases")

        # Assert
        assert response.status_code == 200
        body = response.json()
        # Six rows nobody can read, one product nobody knows, and the two
        # products whose rows lost their code and so never came: `COR-0050`,
        # whose code cell is empty, and `COR-0066`, whose code repeats the row
        # above it.
        assert body["total"] == 9
        assert all(item["reason"] for item in body["items"])

    async def test_sales_does_not(self, sales_client: AsyncClient) -> None:
        """It is Marcela's screen, and the owner's."""
        # Act
        response = await sales_client.get(f"{TRIAGE}/cases")

        # Assert
        assert response.status_code == 403

    async def test_a_case_is_resolved_and_leaves_the_queue(
        self, purchasing_client: AsyncClient, a_list_was_extracted: None
    ) -> None:
        """RF-29 to RF-33, through the endpoint the screen calls."""
        # Arrange
        cases = (await purchasing_client.get(f"{TRIAGE}/cases")).json()["items"]
        case = next(item for item in cases if item["kind"] == "unknown_product")

        # Act
        response = await purchasing_client.post(
            f"{TRIAGE}/cases/{case['id']}/resolution",
            json={"decision": {"action": "incorporate"}},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "RESOLVED"
        remaining = (await purchasing_client.get(f"{TRIAGE}/cases")).json()["total"]
        assert remaining == 8

    async def test_the_decision_shows_up_as_a_rule(
        self,
        purchasing_client: AsyncClient,
        purchasing_user: User,
        a_list_was_extracted: None,
    ) -> None:
        """RF-36: with who took it and when."""
        # Arrange
        cases = (await purchasing_client.get(f"{TRIAGE}/cases")).json()["items"]
        case = next(item for item in cases if item["kind"] == "unknown_product")
        await purchasing_client.post(
            f"{TRIAGE}/cases/{case['id']}/resolution",
            json={"decision": {"action": "incorporate"}},
        )

        # Act
        response = await purchasing_client.get(f"{TRIAGE}/rules")

        # Assert
        assert response.status_code == 200
        rules = response.json()
        assert len(rules) == 1
        assert rules[0]["created_by_user_id"] == purchasing_user.id
        # "Quién la tomó" has to be readable by the person looking at the
        # screen: a number is not an answer to that question (RF-36).
        assert rules[0]["created_by_name"] == purchasing_user.name

    async def test_a_rule_can_be_left_without_effect(
        self, purchasing_client: AsyncClient, a_list_was_extracted: None
    ) -> None:
        """RF-37: and what it was resolving comes back."""
        # Arrange
        cases = (await purchasing_client.get(f"{TRIAGE}/cases")).json()["items"]
        case = next(item for item in cases if item["kind"] == "unknown_product")
        await purchasing_client.post(
            f"{TRIAGE}/cases/{case['id']}/resolution",
            json={"decision": {"action": "incorporate"}},
        )
        rule_id = (await purchasing_client.get(f"{TRIAGE}/rules")).json()[0]["id"]

        # Act
        response = await purchasing_client.delete(f"{TRIAGE}/rules/{rule_id}")

        # Assert
        assert response.status_code == 204
        assert (await purchasing_client.get(f"{TRIAGE}/rules")).json() == []

    async def test_sales_cannot_revoke_a_rule(self, sales_client: AsyncClient) -> None:
        """The screen is not sales', and neither is undoing what it taught."""
        # Act
        response = await sales_client.delete(f"{TRIAGE}/rules/1")

        # Assert
        assert response.status_code == 403
