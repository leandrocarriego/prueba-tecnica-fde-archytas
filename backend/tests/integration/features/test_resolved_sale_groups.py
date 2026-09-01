"""Los casos resueltos: lo que se decidió, quién, cuándo, y cómo se vuelve atrás.

Tres requisitos firmados no tenían dónde ocurrir hasta que existió esta consulta.
Un caso decidido sale de `held_groups` —RF-37 pide que la cola tenga un pendiente
menos— y con eso se iba de la pantalla entero: nadie podía ver la versión
descartada al lado de la elegida (RF-34), ni leer qué se decidió y por quién
(RF-36), ni deshacerlo (RF-35), porque el botón de deshacer vivía sobre los
grupos **pendientes**, donde por definición no hay resolución que revertir.

Lo que estos tests fijan, y es el punto: la consulta se apoya en `decision`, la
misma columna que `undo_resolution` exige. Cualquier otra —`resolved_at`, o el
estado— vuelve a poner en la lista casos sobre los que el botón sólo puede
fallar.
"""

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.sales.service import SalesService
from app.shared.events import NormalizedSale

pytestmark = [pytest.mark.integration, pytest.mark.database]

ACTOR = 7


def sale(code: str, *, quantity: int = 5, total: int = 100_000) -> NormalizedSale:
    """One normalised record, as `ingestion` publishes it."""
    from app.modules.ingestion.parsers import sale_code_key

    return NormalizedSale(
        staging_row_id=0,
        code=code,
        code_key=sale_code_key(code),
        sold_on=date(2026, 3, 15),
        product_code="COR-0001",
        quantity=quantity,
        total=Decimal(total),
    )


async def a_decided_group(session: AsyncSession, code: str = "V-00001") -> SalesService:
    """Two versions that differ, and somebody choosing one of them."""
    service = SalesService(session)
    await service.remember_product("COR-0001")
    await service.register_sales(batch_id=1, sales=(sale(code, quantity=5), sale(code, quantity=9)))
    queue = await service.review_queue()
    chosen = queue.groups[0].versions[0]
    await service.resolve_group(
        queue.groups[0].code_key, action="keep", sale_id=chosen.id, actor_user_id=ACTOR
    )
    return service


class TestResolvedGroups:
    """RF-34, RF-35 y RF-36: el caso decidido sigue siendo visible."""

    async def test_a_decided_case_leaves_the_queue_but_not_the_screen(
        self, session: AsyncSession
    ) -> None:
        """RF-37 y RF-34 a la vez: uno menos pendiente, y todavía consultable."""
        # Arrange & Act
        service = await a_decided_group(session)

        # Assert
        assert (await service.review_queue()).groups == []
        resolved = await service.resolved_groups()
        assert len(resolved) == 1
        assert len(resolved[0].versions) == 2

    async def test_the_discarded_version_stays_beside_the_chosen_one(
        self, session: AsyncSession
    ) -> None:
        """RF-34: se sigue viendo la que se descartó, no sólo la que quedó."""
        # Arrange & Act
        service = await a_decided_group(session)

        # Assert
        states = {version.state.value for version in (await service.resolved_groups())[0].versions}
        assert states == {"COUNTED", "DISCARDED"}

    async def test_the_case_says_what_was_decided_and_by_whom(self, session: AsyncSession) -> None:
        """RF-36: qué se decidió, quién y cuándo — el nombre lo pone la ruta."""
        # Arrange & Act
        service = await a_decided_group(session)

        # Assert
        group = (await service.resolved_groups())[0]
        assert group.action == "keep"
        assert group.kept_sale_id is not None
        assert group.resolved_by_user_id == ACTOR
        assert group.resolved_at is not None

    async def test_undoing_takes_the_case_out_of_the_resolved_list(
        self, session: AsyncSession
    ) -> None:
        """RF-35: deshecha la decisión, el caso vuelve a pendientes y a nada más."""
        # Arrange
        service = await a_decided_group(session)
        code_key = (await service.resolved_groups())[0].code_key

        # Act
        await service.undo_resolution(code_key)

        # Assert
        assert await service.resolved_groups() == []
        assert len((await service.review_queue()).groups) == 1

    async def test_what_the_system_merged_on_its_own_is_not_a_resolved_case(
        self, session: AsyncSession
    ) -> None:
        """El caso que hizo falta separar: unificar no es decidir.

        Dos idénticas se unifican solas y una queda `DISCARDED` sin que nadie
        haya decidido nada. Si esta lista se armara por estado, ese caso
        aparecería con un botón de deshacer que sólo puede contestar 409 —que es
        exactamente el defecto que se está corrigiendo—, y la firma es explícita
        en que lo unificado no tiene resolución que revertir.
        """
        # Arrange
        service = SalesService(session)
        await service.remember_product("COR-0001")

        # Act
        await service.register_sales(batch_id=1, sales=(sale("V-00009"), sale("V-00009")))

        # Assert
        assert (await service.list_sales(state=None)).total == 2
        assert await service.resolved_groups() == []

    async def test_a_corrected_broken_record_is_not_a_resolved_case_either(
        self, session: AsyncSession
    ) -> None:
        """El otro caso que separa `decision` de `resolved_at`.

        Corregir una venta rota estampa `resolved_at` y no deja `decision`: es
        una corrección, no la resolución de una repetida, y `undo_resolution`
        la rechazaría. Filtrar por `resolved_at` la traería a esta lista.
        """
        # Arrange
        service = SalesService(session)
        await service.remember_product("COR-0001")
        await service.register_sales(
            batch_id=1,
            sales=(
                NormalizedSale(
                    staging_row_id=0,
                    code="V-00040",
                    code_key="v00040",
                    sold_on=None,
                    product_code="COR-0001",
                    quantity=5,
                    total=Decimal(100_000),
                    reason="La fila no trae fecha",
                ),
            ),
        )
        held = (await service.review_queue()).broken[0]

        # Act
        await service.correct_sale(
            held.id, values={"sold_on": date(2026, 4, 15)}, is_estimated=False, actor_user_id=ACTOR
        )

        # Assert
        assert await service.resolved_groups() == []


class TestTheRouteNamesWhoDecided:
    """RF-36 de punta a punta: el id se convierte en un nombre en el borde."""

    async def test_the_listing_says_who_decided_by_name(
        self, session: AsyncSession, sales_user: User, sales_client: AsyncClient
    ) -> None:
        """`ActorDirectory` es lo único que puede nombrar sin cruzar la frontera.

        Que el nombre lo ponga la ruta y no el servicio es lo que deja a `sales`
        sin importar `identity` (Artículo IV), y que llegue **hasta la respuesta**
        es lo que separa cumplir RF-36 de simularlo con un "el usuario 3".
        """
        # Arrange
        service = SalesService(session)
        await service.remember_product("COR-0001")
        await service.register_sales(
            batch_id=1, sales=(sale("V-00077", quantity=5), sale("V-00077", quantity=9))
        )
        queue = await service.review_queue()
        chosen = queue.groups[0].versions[0]
        await service.resolve_group(
            queue.groups[0].code_key,
            action="keep",
            sale_id=chosen.id,
            actor_user_id=sales_user.id,
        )

        # Act
        response = await sales_client.get("/api/v1/sales/resolved")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["resolved_by_user_id"] == sales_user.id
        assert body[0]["resolved_by_name"] == sales_user.name
