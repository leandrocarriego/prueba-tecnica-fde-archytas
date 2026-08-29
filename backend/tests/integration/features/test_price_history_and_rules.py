"""Two borders the feature is built on, and neither of them is the happy path.

**RF-40** — the published history and the one the system accumulates meet at the
same instant, and only one point may survive. The plan is explicit that the
database decides it, not the code, so what is under test is that the constraint
is actually the thing being leaned on.

**RF-37** — revoking a rule runs the feature *backwards*: it is the only
requirement that gives work back instead of taking it away.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import PricePoint, PriceSource, Product
from app.modules.catalog.service import CatalogService
from app.modules.identity.models import User
from app.modules.ingestion.models import ResolutionRuleProjection
from app.modules.triage.models import CaseStatus, ExceptionCase
from app.modules.triage.service import UNKNOWN_PRODUCT, TriageService
from app.shared.events import NormalizedHistoryPoint
from tests.factories.catalog_factory import ProductFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

A_MOMENT = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)


async def points_of(session: AsyncSession, product: Product) -> list[PricePoint]:
    """Every point of a product, oldest first."""
    result = await session.execute(
        select(PricePoint)
        .where(PricePoint.product_id == product.id)
        .order_by(PricePoint.changed_at)
    )
    return list(result.scalars().all())


class TestWhereTheTwoHistoriesMeet:
    """RF-40: one price, one moment, one point — whoever saw it."""

    async def test_a_published_point_does_not_duplicate_one_the_system_recorded(
        self, session: AsyncSession
    ) -> None:
        """The same instant arriving from both sides has to leave one row.

        `source` is deliberately out of the unique key: a point is identified by
        its product and its moment, and treating "the portal said it" and "we
        saw it" as different points would double every history on day one.
        """
        # Arrange
        product = await ProductFactory.create(session, price=100)
        await ProductFactory.add_point(
            session, product, price=100, changed_at=A_MOMENT, source=PriceSource.SYSTEM
        )

        # Act
        await CatalogService(session).import_published_history(
            product_code=product.code,
            points=(
                NormalizedHistoryPoint(staging_row_id=1, price=Decimal("100"), changed_at=A_MOMENT),
            ),
        )

        # Assert
        points = await points_of(session, product)
        assert len(points) == 1
        assert points[0].source is PriceSource.SYSTEM

    async def test_a_published_point_at_a_different_moment_is_kept(
        self, session: AsyncSession
    ) -> None:
        """The guard is the moment, not the price: two dates are two points."""
        # Arrange
        product = await ProductFactory.create(session, price=100)
        await ProductFactory.add_point(
            session, product, price=100, changed_at=A_MOMENT, source=PriceSource.SYSTEM
        )

        # Act
        await CatalogService(session).import_published_history(
            product_code=product.code,
            points=(
                NormalizedHistoryPoint(
                    staging_row_id=1,
                    price=Decimal("100"),
                    changed_at=A_MOMENT - timedelta(days=1),
                ),
            ),
        )

        # Assert
        assert len(await points_of(session, product)) == 2

    async def test_a_history_of_an_unknown_product_is_not_lost_and_not_invented(
        self, session: AsyncSession
    ) -> None:
        """There is nothing to attach it to; the screen it came from is in `raw` either way."""
        # Act
        await CatalogService(session).import_published_history(
            product_code="COR-9999",
            points=(
                NormalizedHistoryPoint(staging_row_id=1, price=Decimal("100"), changed_at=A_MOMENT),
            ),
        )

        # Assert
        total = await session.execute(select(func.count()).select_from(PricePoint))
        assert int(total.scalar_one()) == 0

    async def test_importing_the_same_published_history_twice_changes_nothing(
        self, session: AsyncSession
    ) -> None:
        """The acceptance criterion of RF-40, at the level the import happens."""
        # Arrange
        product = await ProductFactory.create(session, price=100)
        published = tuple(
            NormalizedHistoryPoint(
                staging_row_id=index,
                price=Decimal(str(100 + index)),
                changed_at=A_MOMENT + timedelta(days=index),
            )
            for index in range(5)
        )
        service = CatalogService(session)

        # Act
        await service.import_published_history(product_code=product.code, points=published)
        await service.import_published_history(product_code=product.code, points=published)

        # Assert
        assert len(await points_of(session, product)) == 5


class TestRevokingARule:
    """RF-37: the one requirement that runs the feature backwards."""

    @pytest.fixture
    async def a_resolved_case(self, session: AsyncSession, owner: User) -> ExceptionCase:
        """An unknown product somebody decided to incorporate, and the rule it left."""
        service = TriageService(session)
        await service.open_case(
            kind=UNKNOWN_PRODUCT,
            reason="El producto no está entre los conocidos",
            payload={"product_code": "COR-0999", "description": "Producto nuevo", "price": "1000"},
            key="COR-0999",
            batch_id=1,
        )
        opened = (
            (await session.execute(select(ExceptionCase).order_by(ExceptionCase.id.desc())))
            .scalars()
            .first()
        )
        assert opened is not None
        await service.resolve(opened.id, decision={"action": "incorporate"}, user_id=owner.id)
        return opened

    async def test_the_case_it_resolved_goes_back_to_pending(
        self, session: AsyncSession, owner: User, a_resolved_case: ExceptionCase
    ) -> None:
        """The queue gets the question back, instead of the answer staying wrong quietly."""
        # Arrange
        rule = (await TriageService(session).list_rules())[0]

        # Act
        await TriageService(session).revoke_rule(rule.id, user_id=owner.id)

        # Assert
        await session.refresh(a_resolved_case)
        assert a_resolved_case.status is CaseStatus.PENDING

    async def test_the_case_forgets_who_had_decided_it(
        self, session: AsyncSession, owner: User, a_resolved_case: ExceptionCase
    ) -> None:
        """A pending case showing a decision and an author would be a contradiction."""
        # Arrange
        rule = (await TriageService(session).list_rules())[0]

        # Act
        await TriageService(session).revoke_rule(rule.id, user_id=owner.id)

        # Assert
        await session.refresh(a_resolved_case)
        assert a_resolved_case.decision is None
        assert a_resolved_case.resolved_by_user_id is None
        assert a_resolved_case.resolved_at is None

    async def test_ingestion_stops_applying_it(
        self, session: AsyncSession, owner: User, a_resolved_case: ExceptionCase
    ) -> None:
        """The projection is what `ingestion` reads while it normalises, and it has to empty."""
        # Arrange
        rule = (await TriageService(session).list_rules())[0]
        before = (await session.execute(select(ResolutionRuleProjection))).scalars().all()
        assert len(before) == 1

        # Act
        await TriageService(session).revoke_rule(rule.id, user_id=owner.id)

        # Assert
        after = (await session.execute(select(ResolutionRuleProjection))).scalars().all()
        assert after == []

    async def test_the_product_it_had_incorporated_stops_being_known(
        self, session: AsyncSession, owner: User, a_resolved_case: ExceptionCase
    ) -> None:
        """Otherwise the next list would find it known and never set it aside again."""
        # Arrange
        rule = (await TriageService(session).list_rules())[0]
        incorporated = await session.execute(select(Product).where(Product.code == "COR-0999"))
        assert incorporated.scalar_one_or_none() is not None

        # Act
        await TriageService(session).revoke_rule(rule.id, user_id=owner.id)

        # Assert
        gone = await session.execute(select(Product).where(Product.code == "COR-0999"))
        assert gone.scalar_one_or_none() is None

    async def test_it_does_not_touch_products_that_came_from_a_list(
        self, session: AsyncSession, owner: User, a_resolved_case: ExceptionCase
    ) -> None:
        """Undoing a rule undoes **that rule**, not the catalog."""
        # Arrange
        from_a_list = await ProductFactory.create(session, price=500)
        rule = (await TriageService(session).list_rules())[0]

        # Act
        await TriageService(session).revoke_rule(rule.id, user_id=owner.id)

        # Assert
        survivor = await session.execute(select(Product).where(Product.code == from_a_list.code))
        assert survivor.scalar_one_or_none() is not None
