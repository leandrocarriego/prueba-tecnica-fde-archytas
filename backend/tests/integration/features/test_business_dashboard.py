"""El tablero: contar lo que se puede contar, y decir siempre qué quedó afuera.

La frase del cliente es la especificación de la 009 — *"que se nos avise cuáles
son, no que se sumen como si fueran válidas"*— y estos tests la fijan:

* una venta repetida **idéntica** se cuenta una sola vez, sin preguntarle a
  nadie (RF-11, RF-12);
* una repetida con un dato distinto **no suma** hasta que alguien decida
  (RF-13, RF-15);
* una rota se aparta con su motivo (RF-16 a RF-23);
* y cada indicador informa cuántos registros excluyó, **también cuando no
  excluyó ninguno** (RF-25, RF-27).
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.sales.models import SaleState
from app.modules.sales.service import SalesService
from app.shared.events import NormalizedSale

pytestmark = [pytest.mark.integration, pytest.mark.database]


def sale(
    code: str,
    *,
    total: int = 100_000,
    quantity: int = 5,
    sold_on: date | None = None,
    product_code: str | None = "COR-0001",
) -> NormalizedSale:
    """One normalised sales record, as `ingestion` publishes it."""
    from app.modules.ingestion.parsers import sale_code_key

    return NormalizedSale(
        staging_row_id=0,
        code=code,
        code_key=sale_code_key(code),
        sold_on=sold_on or date(2026, 3, 15),
        product_code=product_code,
        quantity=quantity,
        total=Decimal(total),
    )


async def known(session: AsyncSession, *codes: str) -> None:
    """Teach this module which products the catalog knows."""
    service = SalesService(session)
    for code in codes:
        await service.remember_product(code)


class TestRepeatedSales:
    """H2: el mismo código dos veces, y qué las separa."""

    async def test_two_identical_records_are_counted_once(self, session: AsyncSession) -> None:
        """RF-11, RF-12: sin esperar a nadie, y diciendo que unificó."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)

        # Act
        await service.register_sales(batch_id=1, sales=(sale("V-00001"), sale("V-00001")))

        # Assert
        counted = await service.list_sales(state=SaleState.COUNTED)
        discarded = await service.list_sales(state=SaleState.DISCARDED)
        assert counted.total == 1
        assert discarded.total == 1
        assert (await service.dashboard()).invoiced.value == Decimal(100_000)

    async def test_the_code_is_compared_without_its_spelling(self, session: AsyncSession) -> None:
        """RF-10: `v-00001` y `V-00001` son la misma venta."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)

        # Act
        await service.register_sales(batch_id=1, sales=(sale("V-00001"), sale(" v00001 ")))

        # Assert
        assert (await service.list_sales(state=SaleState.COUNTED)).total == 1

    async def test_records_that_differ_are_held_until_somebody_decides(
        self, session: AsyncSession
    ) -> None:
        """RF-13, RF-15: ninguna de las dos suma mientras tanto."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)

        # Act
        await service.register_sales(
            batch_id=1, sales=(sale("V-00002", quantity=5), sale("V-00002", quantity=9))
        )

        # Assert
        assert (await service.list_sales(state=SaleState.COUNTED)).total == 0
        assert (await service.dashboard()).invoiced.value == Decimal(0)
        queue = await service.review_queue()
        assert queue.pending_groups == 1
        assert queue.groups[0].differences == ["quantity"]

    async def test_choosing_a_version_counts_it_and_keeps_the_other_beside_it(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-31, RF-33, RF-34, RF-36."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)
        await service.register_sales(
            batch_id=1, sales=(sale("V-00003", total=100_000), sale("V-00003", total=120_000))
        )
        group = (await service.review_queue()).groups[0]
        chosen = group.versions[0]

        # Act
        resolved = await service.resolve_group(
            group.code_key, action="keep", sale_id=chosen.id, actor_user_id=owner.id
        )

        # Assert
        assert [item.state for item in resolved].count(SaleState.COUNTED) == 1
        assert [item.state for item in resolved].count(SaleState.DISCARDED) == 1
        assert all(item.resolved_by_user_id == owner.id for item in resolved)
        assert (await service.dashboard()).invoiced.value == chosen.total

    async def test_declaring_them_distinct_counts_all_of_them(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-32: nunca fueron la misma venta, y el código compartido es el error."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)
        await service.register_sales(
            batch_id=1, sales=(sale("V-00004", total=10_000), sale("V-00004", total=20_000))
        )
        group = (await service.review_queue()).groups[0]

        # Act
        await service.resolve_group(
            group.code_key, action="distinct", sale_id=None, actor_user_id=owner.id
        )

        # Assert
        assert (await service.dashboard()).invoiced.value == Decimal(30_000)

    async def test_undoing_a_resolution_puts_it_back_and_recalculates(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-35."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)
        await service.register_sales(
            batch_id=1, sales=(sale("V-00005", total=10_000), sale("V-00005", total=20_000))
        )
        group = (await service.review_queue()).groups[0]
        await service.resolve_group(
            group.code_key, action="distinct", sale_id=None, actor_user_id=owner.id
        )

        # Act
        await service.undo_resolution(group.code_key)

        # Assert
        assert (await service.dashboard()).invoiced.value == Decimal(0)
        assert (await service.review_queue()).pending_groups == 1


class TestBrokenRecords:
    """H3: lo que no se puede sumar se aparta con el motivo, y nunca se completa."""

    async def test_a_sale_of_a_product_that_does_not_exist_is_held(
        self, session: AsyncSession
    ) -> None:
        """RF-20, RF-23."""
        # Arrange — el catálogo conoce uno, y la venta apunta a otro.
        await known(session, "COR-0001")
        service = SalesService(session)

        # Act
        await service.register_sales(batch_id=1, sales=(sale("V-00010", product_code="COR-9999"),))

        # Assert
        held = await service.list_sales(state=SaleState.HELD)
        assert held.total == 1
        assert held.items[0].reason == "La venta apunta a un producto que no existe"

    async def test_an_amount_far_from_the_usual_is_held_as_an_outlier(
        self, session: AsyncSession
    ) -> None:
        """RF-21: contra lo que ya está contado para ese producto, no contra una tabla."""
        # Arrange — tres ventas normales enseñan qué es lo habitual.
        await known(session, "COR-0001")
        service = SalesService(session)
        await service.register_sales(
            batch_id=1,
            sales=(
                sale("V-00020", total=100_000),
                sale("V-00021", total=110_000),
                sale("V-00022", total=90_000),
            ),
        )

        # Act — y una que se va diez veces por encima.
        await service.register_sales(batch_id=2, sales=(sale("V-00023", total=1_000_000),))

        # Assert
        held = await service.list_sales(state=SaleState.HELD)
        assert held.total == 1
        assert held.items[0].reason == "El total se aleja de lo habitual para ese producto"

    async def test_what_the_portal_said_is_kept_when_somebody_corrects_it(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-38, RF-39, RF-41: y un valor estimado queda marcado como tal."""
        # Arrange
        await known(session, "COR-0001", "COR-0002")
        service = SalesService(session)
        await service.register_sales(batch_id=1, sales=(sale("V-00030", product_code="COR-9999"),))
        held = (await service.list_sales(state=SaleState.HELD)).items[0]

        # Act
        corrected = await service.correct_sale(
            held.id,
            values={"product_code": "COR-0002", "sold_on": None, "quantity": None, "total": None},
            is_estimated=True,
            actor_user_id=owner.id,
        )

        # Assert
        assert corrected.state is SaleState.COUNTED
        assert corrected.product_code == "COR-0002"
        assert corrected.is_estimated is True
        assert corrected.portal_values["product_code"] == "COR-9999"


class TestTheIndicators:
    """H1 y H4: el número, y cuántos registros no entraron en él."""

    async def test_every_indicator_reports_what_it_left_out(self, session: AsyncSession) -> None:
        """RF-25, RF-26."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)
        await service.register_sales(
            batch_id=1,
            sales=(
                sale("V-00040", total=50_000),
                sale("V-00041", total=50_000, product_code="COR-9999"),
            ),
        )

        # Act
        dashboard = await service.dashboard()

        # Assert
        assert dashboard.invoiced.value == Decimal(50_000)
        assert dashboard.invoiced.sales == 1
        assert dashboard.invoiced.excluded == 1

    async def test_it_says_so_even_when_it_left_out_nothing(self, session: AsyncSession) -> None:
        """RF-27: cero excluidos es una respuesta, no un silencio."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)
        await service.register_sales(batch_id=1, sales=(sale("V-00050"),))

        # Act
        dashboard = await service.dashboard()

        # Assert
        assert dashboard.invoiced.excluded == 0
        assert dashboard.invoiced.has_estimates is False

    async def test_the_monthly_curve_only_adds_what_counts(self, session: AsyncSession) -> None:
        """RF-03, RF-04."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)
        await service.register_sales(
            batch_id=1,
            sales=(
                sale("V-00060", total=10_000, sold_on=date(2026, 1, 10)),
                sale("V-00061", total=20_000, sold_on=date(2026, 2, 10)),
                sale("V-00062", total=30_000, sold_on=date(2026, 2, 20)),
                sale("V-00063", total=99_000, sold_on=date(2026, 2, 25), product_code="COR-9999"),
            ),
        )

        # Act
        dashboard = await service.dashboard()

        # Assert
        by_month = {point.month: point.total for point in dashboard.by_month}
        assert by_month[date(2026, 1, 1)] == Decimal(10_000)
        assert by_month[date(2026, 2, 1)] == Decimal(50_000)

    async def test_a_window_changes_this_number_and_no_other(self, session: AsyncSession) -> None:
        """RF-05: cada corte elige su período por separado."""
        # Arrange
        await known(session, "COR-0001")
        service = SalesService(session)
        await service.register_sales(
            batch_id=1,
            sales=(
                sale("V-00070", total=10_000, sold_on=date(2026, 1, 10)),
                sale("V-00071", total=20_000, sold_on=date(2026, 5, 10)),
            ),
        )

        # Act
        january = await service.dashboard(since=date(2026, 1, 1), until=date(2026, 1, 31))

        # Assert
        assert january.invoiced.value == Decimal(10_000)
        assert (await service.dashboard()).invoiced.value == Decimal(30_000)
