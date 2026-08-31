"""Los tres cortes del tablero que son del catálogo: precios, stock y altas.

La H6 de la 009 estaba construida y **sin un solo test**: cinco requisitos
verdes por lectura. Lo que se fija acá es lo que la spec promete y lo que el
plan advierte que sorprende:

* la curva de precios es la de lo que el proveedor informó (RF-42);
* el stock compara la foto del inicio con la del final del período (RF-43) y
  señala lo que quedó en cero (RF-44);
* las altas son los productos que aparecieron por primera vez ahí (RF-45);
* y **cada corte dice cuántos registros dejó afuera** (RF-46), donde un
  producto sin foto en algún extremo queda excluido y **no** contado como cero.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import PriceSource
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.service import CatalogService

pytestmark = [pytest.mark.integration, pytest.mark.database]

WINDOW_START = date(2026, 3, 1)
WINDOW_END = date(2026, 3, 31)


async def product(session: AsyncSession, code: str, *, seen_on: date = date(2026, 3, 10)) -> int:
    """A product the catalog knows, met on a given day."""
    registered = await CatalogRepository(session).add_product(
        code=code,
        description=f"Producto {code}",
        seen_at=datetime.combine(seen_on, datetime.min.time(), tzinfo=UTC),
    )
    return int(registered.id)


async def stock(session: AsyncSession, product_id: int, *, on: date, quantity: int) -> None:
    """The stock the list published for a product on one day."""
    await CatalogRepository(session).add_stock_point(
        product_id=product_id, quantity=quantity, observed_on=on, batch_id=1
    )


async def priced(session: AsyncSession, product_id: int, *, on: date, price: int) -> None:
    """One point of what the supplier charged."""
    await CatalogRepository(session).add_point(
        product_id=product_id,
        price=Decimal(price),
        changed_at=datetime.combine(on, datetime.min.time(), tzinfo=UTC),
        source=PriceSource.PORTAL,
    )


class TestTheStockCut:
    """RF-43, RF-44 y la mitad de RF-46."""

    async def test_it_compares_the_photograph_at_each_end_of_the_window(
        self, session: AsyncSession
    ) -> None:
        """RF-43: cuánto había al inicio y cuánto al final, por producto."""
        # Arrange
        product_id = await product(session, "COR-1001")
        await stock(session, product_id, on=date(2026, 3, 2), quantity=40)
        await stock(session, product_id, on=date(2026, 3, 28), quantity=12)

        # Act
        board = await CatalogService(session).dashboard(since=WINDOW_START, until=WINDOW_END)

        # Assert
        cut = next(item for item in board.stock if item.product_id == product_id)
        assert cut.opening == 40
        assert cut.closing == 12
        assert cut.ran_out is False

    async def test_a_product_that_ended_the_window_at_zero_is_flagged(
        self, session: AsyncSession
    ) -> None:
        """RF-44."""
        # Arrange
        product_id = await product(session, "COR-1002")
        await stock(session, product_id, on=date(2026, 3, 2), quantity=25)
        await stock(session, product_id, on=date(2026, 3, 30), quantity=0)

        # Act
        board = await CatalogService(session).dashboard(since=WINDOW_START, until=WINDOW_END)

        # Assert
        cut = next(item for item in board.stock if item.product_id == product_id)
        assert cut.ran_out is True

    async def test_a_product_the_list_never_priced_is_excluded_not_zero(
        self, session: AsyncSession
    ) -> None:
        """RF-46: decir cero sería inventar un stock que nadie informó."""
        # Arrange — uno con fotos, y uno del que la lista nunca publicó stock.
        complete = await product(session, "COR-1003")
        await stock(session, complete, on=date(2026, 3, 2), quantity=10)
        await stock(session, complete, on=date(2026, 3, 30), quantity=8)
        await product(session, "COR-1004")

        # Act
        board = await CatalogService(session).dashboard(since=WINDOW_START, until=WINDOW_END)

        # Assert
        assert [cut.product_id for cut in board.stock] == [complete]
        assert board.stock_excluded == 1

    async def test_a_single_observation_is_reported_at_both_ends(
        self, session: AsyncSession
    ) -> None:
        """Lo que el corte hace hoy con **una sola** foto dentro del período.

        `stock_at` toma la foto *más cercana* a cada borde, no la del día exacto
        —está decidido así porque la lista se publica los días que se publica—,
        así que con una única observación la misma foto es la de apertura y la
        de cierre, y el producto se lee como «no se movió».

        **Es una inferencia sobre un solo dato, y este test la deja escrita en
        vez de que aparezca como una sorpresa.** Si el negocio prefiere que un
        producto con una sola observación quede excluido, es un cambio de RF-43
        y lo decide el humano, no un refactor.
        """
        # Arrange
        product_id = await product(session, "COR-1012")
        await stock(session, product_id, on=date(2026, 3, 30), quantity=5)

        # Act
        board = await CatalogService(session).dashboard(since=WINDOW_START, until=WINDOW_END)

        # Assert
        cut = next(item for item in board.stock if item.product_id == product_id)
        assert cut.opening == 5
        assert cut.closing == 5
        assert board.stock_excluded == 0

    async def test_without_a_window_the_cut_is_empty_and_says_so(
        self, session: AsyncSession
    ) -> None:
        """El caso que sorprende, y que el plan advierte: sin `since` no hay apertura.

        No es un defecto — es la consecuencia de que el corte compare dos fotos
        y de que sin borde no haya ninguna que tomar. Lo que importa es que el
        número de excluidos lo diga en vez de mostrar una lista vacía y callarse.
        """
        # Arrange
        product_id = await product(session, "COR-1005")
        await stock(session, product_id, on=date(2026, 3, 2), quantity=10)

        # Act
        board = await CatalogService(session).dashboard()

        # Assert
        assert board.stock == []
        assert board.stock_excluded == 1


class TestThePriceCurve:
    """RF-42 y la otra mitad de RF-46."""

    async def test_it_averages_what_the_supplier_reported_month_by_month(
        self, session: AsyncSession
    ) -> None:
        """RF-42: los puntos del historial, que es lo que el proveedor informó."""
        # Arrange
        product_id = await product(session, "COR-1006")
        await priced(session, product_id, on=date(2026, 3, 5), price=1000)
        await priced(session, product_id, on=date(2026, 3, 20), price=1400)

        # Act
        board = await CatalogService(session).dashboard(since=WINDOW_START, until=WINDOW_END)

        # Assert
        assert len(board.price_curve) == 1
        assert board.price_curve[0].average_price == Decimal(1200)
        assert board.price_curve[0].changes == 2

    async def test_it_counts_the_products_it_left_out_instead_of_assuming_none(
        self, session: AsyncSession
    ) -> None:
        """RF-46: un producto sin ningún precio en la ventana no entra en ningún mes.

        El corte informaba «cero excluidos» sin haber contado, que es lo único
        que un indicador de esta feature no puede hacer.
        """
        # Arrange
        with_price = await product(session, "COR-1007")
        await priced(session, with_price, on=date(2026, 3, 5), price=1000)
        await product(session, "COR-1008")

        # Act
        board = await CatalogService(session).dashboard(since=WINDOW_START, until=WINDOW_END)

        # Assert
        assert board.price_curve_excluded == 1


class TestTheNewProducts:
    """RF-45, y RF-46 diciendo en voz alta que este corte no excluye nada."""

    async def test_it_lists_the_products_first_met_inside_the_window(
        self, session: AsyncSession
    ) -> None:
        """RF-45."""
        # Arrange
        inside = await product(session, "COR-1009", seen_on=date(2026, 3, 12))
        await product(session, "COR-1010", seen_on=date(2026, 1, 12))

        # Act
        board = await CatalogService(session).dashboard(since=WINDOW_START, until=WINDOW_END)

        # Assert
        assert [new.product_id for new in board.new_products] == [inside]

    async def test_it_reports_that_it_excluded_nothing(self, session: AsyncSession) -> None:
        """RF-27 y RF-46: «cero excluidos» es una respuesta; un silencio no."""
        # Arrange
        await product(session, "COR-1011", seen_on=date(2026, 3, 12))

        # Act
        board = await CatalogService(session).dashboard(since=WINDOW_START, until=WINDOW_END)

        # Assert
        assert board.new_products_excluded == 0
