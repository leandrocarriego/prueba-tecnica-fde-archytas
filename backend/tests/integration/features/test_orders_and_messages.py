"""Órdenes y bandeja: qué se estancó, quién escribió, y a quién se le avisa.

Lo que la 007 pone en juego y por eso se fija acá:

* **desde cuándo** una orden está donde está no lo dice el portal: lo sabe esta
  plataforma desde que empezó a mirarla (RF-05, RF-48), y una orden recibida no
  está estancada por más que lleve meses (RF-10, RF-14);
* un **pedido repetido** se señala y nunca bloquea el registro (RF-15, RF-20);
* un mensaje cuyo tipo no se reconoce **se muestra** sin clasificar (RF-25), y
  uno cuyo remitente no se identifica se muestra diciéndolo (RF-24);
* en la **primera** lectura de la bandeja no se despierta a nadie (RF-47).
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.messaging.models import MessageKind, MessageState
from app.modules.messaging.service import MessagingService
from app.modules.purchases.service import PurchasesService, today_here
from app.modules.triage.models import CaseStatus, ExceptionCase
from app.modules.triage.service import UNREADABLE_ORDER_ROW
from app.shared.errors import ConflictError
from app.shared.events import (
    NormalizedMessage,
    NormalizedPurchaseOrder,
    NormalizedSupplier,
    PurchaseOrderRowsQuarantined,
    QuarantinedRow,
    SupplierMessageReceived,
    events,
)
from tests.factories.purchases_factory import REGISTER

pytestmark = [pytest.mark.integration, pytest.mark.database]


def order(
    number: str,
    supplier_text: str,
    *,
    status: str = "Pendiente de envio",
    product_code: str = "COR-0078",
    ordered_on: date | None = None,
) -> NormalizedPurchaseOrder:
    """One normalised row of the purchase orders screen."""
    return NormalizedPurchaseOrder(
        staging_row_id=0,
        number=number,
        ordered_on=ordered_on or today_here(),
        supplier_text=supplier_text,
        product_code=product_code,
        product_text=f"{product_code} - Articulo",
        quantity=10,
        amount=None,
        status_text=status,
    )


def message(
    external_id: str, *, sender: str, kind: str, subject: str = "Asunto"
) -> NormalizedMessage:
    """One normalised message of the inbox."""
    return NormalizedMessage(
        staging_row_id=0,
        external_id=external_id,
        received_at=datetime.now(UTC),
        sender_text=sender,
        kind_text=kind,
        subject=subject,
        body="Cuerpo del mensaje",
    )


async def register(session: AsyncSession) -> None:
    """Load the register both modules identify against."""
    cards = tuple(
        NormalizedSupplier(legal_name=name, tax_id=tax_id, payment_term_days=term)
        for name, tax_id, term in REGISTER
    )
    await PurchasesService(session).remember_suppliers(cards)
    await MessagingService(session).remember_suppliers(cards)


class TestWatchingAnOrder:
    """H1 y H2: desde cuándo está donde está, y cuándo eso es demasiado."""

    async def test_time_in_a_state_is_counted_from_the_first_observation(
        self, session: AsyncSession
    ) -> None:
        """RF-05, RF-48: el portal no lo publica, así que se sabe desde que se mira."""
        # Arrange
        await register(session)
        service = PurchasesService(session)

        # Act
        await service.register_orders(
            batch_id=1, orders=(order("OC-0001", "Herramientas Cuyo SRL"),)
        )

        # Assert
        listing = await service.list_orders()
        watched = next(item for item in listing.items if item.number == "OC-0001")
        assert watched.status_since == today_here()
        assert watched.days_in_status == 0

    async def test_an_order_that_advances_restarts_the_clock(self, session: AsyncSession) -> None:
        """RF-04, RF-14: avanzar es dejar de estar estancada, sin apagar ninguna marca."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_orders(
            batch_id=1, orders=(order("OC-0002", "Herramientas Cuyo SRL"),)
        )
        stored = await service.purchases.order_numbered("OC-0002")
        assert stored is not None
        stored.status_since = today_here() - timedelta(days=90)
        await session.flush()
        assert (await service.list_orders(only_stalled=True)).stalled == 1

        # Act — la misma orden, en otro estado.
        await service.register_orders(
            batch_id=2,
            orders=(order("OC-0002", "Herramientas Cuyo SRL", status="Enviada al proveedor"),),
        )

        # Assert
        assert (await service.list_orders(only_stalled=True)).stalled == 0

    async def test_a_received_order_is_never_stalled(self, session: AsyncSession) -> None:
        """RF-10: lo que ya llegó no está esperando a nadie."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_orders(
            batch_id=1, orders=(order("OC-0003", "Herramientas Cuyo SRL", status="Recibida"),)
        )
        stored = await service.purchases.order_numbered("OC-0003")
        assert stored is not None
        stored.status_since = today_here() - timedelta(days=90)
        await session.flush()

        # Assert
        assert (await service.list_orders()).stalled == 0

    async def test_the_counts_per_state_are_reported(self, session: AsyncSession) -> None:
        """RF-07."""
        # Arrange
        await register(session)
        service = PurchasesService(session)

        # Act
        await service.register_orders(
            batch_id=1,
            orders=(
                order("OC-0010", "Herramientas Cuyo SRL"),
                order("OC-0011", "Herramientas Cuyo SRL", status="Recibida"),
            ),
        )

        # Assert
        listing = await service.list_orders()
        assert listing.per_status == {"Pendiente de envio": 1, "Recibida": 1}


class TestARepeatedOrder:
    """H3: se señala, se muestra con cuál coincide, y nunca frena el registro."""

    async def test_it_is_flagged_without_blocking_the_order(self, session: AsyncSession) -> None:
        """RF-15, RF-16, RF-20."""
        # Arrange
        await register(session)
        service = PurchasesService(session)

        # Act — el mismo producto al mismo proveedor, dentro de la ventana.
        await service.register_orders(
            batch_id=1,
            orders=(
                order(
                    "OC-0020", "Herramientas Cuyo SRL", ordered_on=today_here() - timedelta(days=3)
                ),
                order("OC-0021", "Herramientas Cuyo SRL"),
            ),
        )

        # Assert
        listing = await service.list_orders()
        flagged = next(item for item in listing.items if item.number == "OC-0021")
        assert flagged.repeat_of_number == "OC-0020"
        assert len(listing.items) == 2

    async def test_the_flag_can_be_dismissed_with_who_did_it(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-18, RF-19."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_orders(
            batch_id=1,
            orders=(
                order(
                    "OC-0030", "Herramientas Cuyo SRL", ordered_on=today_here() - timedelta(days=3)
                ),
                order("OC-0031", "Herramientas Cuyo SRL"),
            ),
        )
        flagged = next(
            item for item in (await service.list_orders()).items if item.number == "OC-0031"
        )

        # Act
        dismissed = await service.dismiss_repeat(flagged.id, actor_user_id=owner.id)

        # Assert
        assert dismissed.repeat_of_order_id is None
        assert dismissed.repeat_dismissed_at is not None


class TestTheInbox:
    """H4 y H5: qué es cada mensaje, de quién es, y quién lo tiene."""

    async def test_it_classifies_by_what_the_portal_writes(self, session: AsyncSession) -> None:
        """RF-22, RF-23."""
        # Arrange
        await register(session)
        service = MessagingService(session)

        # Act
        await service.register_messages(
            messages=(
                message("MSG-1", sender="Aceros Belgrano SA", kind="Reclamo de pago"),
                message("MSG-2", sender="Aceros Belgrano SA", kind="Vencimiento proximo"),
                message("MSG-3", sender="Aceros Belgrano SA", kind="Stock bajo"),
            ),
            first_run=True,
        )

        # Assert
        listing = await service.list_messages()
        kinds = {item.external_id: item.kind for item in listing.items}
        assert kinds["MSG-1"] is MessageKind.PAYMENT_CLAIM
        assert kinds["MSG-2"] is MessageKind.DUE_SOON
        assert kinds["MSG-3"] is MessageKind.LOW_STOCK
        assert all(item.supplier_name == "Aceros Belgrano SA" for item in listing.items)

    async def test_a_kind_nobody_mapped_is_shown_unclassified(self, session: AsyncSession) -> None:
        """RF-25: se muestra, no se descarta. Es Artículo II en su lugar más chico."""
        # Arrange
        await register(session)
        service = MessagingService(session)

        # Act
        await service.register_messages(
            messages=(message("MSG-4", sender="Aceros Belgrano SA", kind="Otra cosa"),),
            first_run=True,
        )

        # Assert
        listing = await service.list_messages()
        assert listing.items[0].kind is MessageKind.UNCLASSIFIED
        assert listing.items[0].kind_text == "Otra cosa"

    async def test_a_sender_outside_the_register_is_shown_saying_so(
        self, session: AsyncSession
    ) -> None:
        """RF-24: visible y sin atribuir al nombre más parecido."""
        # Arrange
        await register(session)
        service = MessagingService(session)

        # Act
        await service.register_messages(
            messages=(message("MSG-5", sender="Alguien Que No Existe SA", kind="Reclamo de pago"),),
            first_run=True,
        )

        # Assert
        read = (await service.list_messages()).items[0]
        assert read.supplier_name is None
        assert read.sender_unidentified is True

    async def test_the_inbox_can_be_asked_for_one_supplier(self, session: AsyncSession) -> None:
        """RF-26: los reclamos pendientes **de un proveedor**, y salen sólo esos.

        El filtro existía en la API y no había control que lo pidiera. Lo que
        fija este test es el par: por qué nombres se puede filtrar —el padrón
        como lo guarda este módulo, que son exactamente los valores que
        `supplier_name` puede tomar— y que filtrar por uno deje afuera al otro.
        """
        # Arrange
        await register(session)
        service = MessagingService(session)
        await service.register_messages(
            messages=(
                message("MSG-7", sender="Aceros Belgrano SA", kind="Reclamo de pago"),
                message("MSG-8", sender="Herramientas Cuyo SRL", kind="Reclamo de pago"),
            ),
            first_run=True,
        )

        # Act
        senders = await service.senders()
        theirs = await service.list_messages(
            kind=MessageKind.PAYMENT_CLAIM,
            state=MessageState.PENDING,
            supplier_name="Aceros Belgrano SA",
        )

        # Assert
        assert "Aceros Belgrano SA" in senders
        assert senders == sorted(senders)
        assert theirs.total == 1
        assert theirs.items[0].supplier_name == "Aceros Belgrano SA"

    async def test_the_same_message_is_not_registered_twice(self, session: AsyncSession) -> None:
        """La bandeja se lee entera cada vez, y casi todo ya se había leído."""
        # Arrange
        await register(session)
        service = MessagingService(session)
        same = message("MSG-6", sender="Aceros Belgrano SA", kind="Reclamo de pago")

        # Act
        first = await service.register_messages(messages=(same,), first_run=True)
        second = await service.register_messages(messages=(same,), first_run=False)

        # Assert
        assert (first, second) == (1, 0)
        assert (await service.list_messages()).total == 1

    async def test_resolving_one_records_who_and_when(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-28, RF-29, RF-31."""
        # Arrange
        await register(session)
        service = MessagingService(session)
        await service.register_messages(
            messages=(message("MSG-7", sender="Aceros Belgrano SA", kind="Stock bajo"),),
            first_run=True,
        )
        pending = (await service.list_messages()).items[0]

        # Act
        resolved = await service.resolve(pending.id, actor_user_id=owner.id)

        # Assert
        assert resolved.state is MessageState.RESOLVED
        assert resolved.resolved_by_user_id == owner.id
        assert await service.count_pending() == 0

    async def test_it_can_be_assigned_and_annotated(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-30, RF-32."""
        # Arrange
        await register(session)
        service = MessagingService(session)
        await service.register_messages(
            messages=(message("MSG-8", sender="Aceros Belgrano SA", kind="Stock bajo"),),
            first_run=True,
        )
        pending = (await service.list_messages()).items[0]

        # Act
        assigned = await service.assign(pending.id, assignee_user_id=owner.id)
        annotated = await service.annotate(pending.id, note="Lo hablo el lunes")

        # Assert
        assert assigned.assignee_user_id == owner.id
        assert annotated.note == "Lo hablo el lunes"


class TestWhoIsWokenUp:
    """H6 y H7: en la primera lectura nadie, y después sólo por lo que importa."""

    async def test_the_first_reading_wakes_nobody(self, session: AsyncSession) -> None:
        """RF-47: los que ya estaban en la bandeja entran pendientes y en silencio."""
        # Arrange
        await register(session)
        announced: list[SupplierMessageReceived] = []

        async def record(event: SupplierMessageReceived, _session: AsyncSession) -> None:
            announced.append(event)

        events.subscribe(SupplierMessageReceived)(record)
        try:
            # Act
            await MessagingService(session).register_messages(
                messages=(message("MSG-9", sender="Aceros Belgrano SA", kind="Reclamo de pago"),),
                first_run=True,
            )
        finally:
            events.unsubscribe(SupplierMessageReceived, record)

        # Assert
        assert announced == []

    async def test_a_claim_that_arrives_afterwards_does_wake_somebody(
        self, session: AsyncSession
    ) -> None:
        """RF-33: y un aviso de stock bajo no (no está entre los urgentes)."""
        # Arrange
        await register(session)
        announced: list[SupplierMessageReceived] = []

        async def record(event: SupplierMessageReceived, _session: AsyncSession) -> None:
            announced.append(event)

        events.subscribe(SupplierMessageReceived)(record)
        try:
            # Act
            await MessagingService(session).register_messages(
                messages=(
                    message("MSG-10", sender="Aceros Belgrano SA", kind="Reclamo de pago"),
                    message("MSG-11", sender="Aceros Belgrano SA", kind="Stock bajo"),
                ),
                first_run=False,
            )
        finally:
            events.unsubscribe(SupplierMessageReceived, record)

        # Assert
        assert [event.kind for event in announced] == ["PAYMENT_CLAIM"]


class TestAnOrderWithoutASupplierHasAWayOut:
    """H8: la orden apartada se resuelve una sola vez y vuelve a la lista.

    Estaba firmada y no estaba construida: la orden **se apartaba bien** —eso es
    RF-08— y después no había salida. Ni ruta, ni conteo, ni filtro, ni dónde
    guardar quién la resolvió.
    """

    async def test_an_unidentifiable_supplier_holds_the_order_with_its_reason(
        self, session: AsyncSession
    ) -> None:
        """RF-08, RF-50, RF-55: entra igual, apartada, y **con el motivo**.

        El motivo se descartaba al registrar. RF-55 pide justamente el que se
        perdía: «este proveedor no está en el padrón» es distinto de «el nombre
        no alcanza», y de esa diferencia depende que nadie intente darlo de alta
        desde la revisión.
        """
        # Arrange
        await register(session)
        service = PurchasesService(session)

        # Act
        await service.register_orders(
            batch_id=1, orders=(order("OC-9001", "Metalurgica Quilmes SRL"),)
        )

        # Assert
        listing = await service.list_orders(only_in_review=True)
        assert listing.held == 1
        assert listing.items[0].supplier_id is None
        assert listing.items[0].supplier_text == "Metalurgica Quilmes SRL"
        assert listing.items[0].review_reason is not None

    async def test_resolving_it_records_who_and_takes_it_off_the_queue(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-54, RF-56, RF-57."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_orders(
            batch_id=1, orders=(order("OC-9002", "Metalurgica Quilmes SRL"),)
        )
        held = (await service.list_orders(only_in_review=True)).items[0]
        supplier = (await service.list_suppliers()).items[0]

        # Act
        resolved = await service.resolve_order(
            held.id, supplier_id=supplier.id, remember=True, actor_user_id=owner.id
        )

        # Assert
        assert resolved.supplier_id == supplier.id
        assert resolved.resolved_by_user_id == owner.id
        assert resolved.resolved_at is not None
        assert (await service.list_orders(only_in_review=True)).held == 0

    async def test_one_decision_resolves_every_order_written_the_same_way(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-61, RF-62: el relevamiento midió **veinte** formas de escribir un nombre.

        Decidir la misma una y otra vez es exactamente la cola que un equipo de
        tres personas termina abandonando.
        """
        # Arrange — tres órdenes con el nombre escrito igual.
        await register(session)
        service = PurchasesService(session)
        await service.register_orders(
            batch_id=1,
            orders=(
                order("OC-9003", "Metalurgica Quilmes SRL"),
                order("OC-9004", "Metalurgica Quilmes SRL", product_code="COR-0079"),
                order("OC-9005", "Metalurgica Quilmes SRL", product_code="COR-0080"),
            ),
        )
        assert (await service.list_orders(only_in_review=True)).held == 3
        held = (await service.list_orders(only_in_review=True)).items[0]
        supplier = (await service.list_suppliers()).items[0]

        # Act — una sola decisión.
        await service.resolve_order(
            held.id, supplier_id=supplier.id, remember=True, actor_user_id=owner.id
        )

        # Assert
        assert (await service.list_orders(only_in_review=True)).held == 0

    async def test_the_next_order_written_that_way_arrives_identified(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-58: guardada la grafía, la que llegue después no pasa por revisión."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_orders(
            batch_id=1, orders=(order("OC-9006", "Metalurgica Quilmes SRL"),)
        )
        held = (await service.list_orders(only_in_review=True)).items[0]
        supplier = (await service.list_suppliers()).items[0]
        await service.resolve_order(
            held.id, supplier_id=supplier.id, remember=True, actor_user_id=owner.id
        )

        # Act
        await service.register_orders(
            batch_id=2, orders=(order("OC-9007", "Metalurgica Quilmes SRL"),)
        )

        # Assert
        assert (await service.list_orders(only_in_review=True)).held == 0
        arrived = [item for item in (await service.list_orders()).items if item.number == "OC-9007"]
        assert arrived[0].supplier_id == supplier.id

    async def test_a_held_order_is_never_flagged_as_a_repeat_and_is_checked_on_resolution(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-59 y RF-60, que son las dos mitades de la misma regla.

        Sin proveedor no hay con qué comparar y señalarla igual sería adivinar.
        Resuelta, la comparación se hace **una vez** en vez de nunca.
        """
        # Arrange — un pedido ya identificado, y otro del mismo producto escrito
        # de una forma que el sistema no reconoce.
        await register(session)
        service = PurchasesService(session)
        supplier = (await service.list_suppliers()).items[0]
        await service.register_orders(batch_id=1, orders=(order("OC-9008", supplier.legal_name),))
        await service.register_orders(
            batch_id=2, orders=(order("OC-9009", "Metalurgica Quilmes SRL"),)
        )
        held = (await service.list_orders(only_in_review=True)).items[0]
        assert held.repeat_of_order_id is None  # RF-59

        # Act
        resolved = await service.resolve_order(
            held.id, supplier_id=supplier.id, remember=False, actor_user_id=owner.id
        )

        # Assert — RF-60: ahora sí hay contra qué comparar.
        assert resolved.repeat_of_order_id is not None
        assert resolved.repeat_of_number == "OC-9008"

    async def test_an_order_that_is_not_held_cannot_be_resolved(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Resolver dos veces no es idempotente: la segunda vez significa otra cosa."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        supplier = (await service.list_suppliers()).items[0]
        await service.register_orders(batch_id=1, orders=(order("OC-9010", supplier.legal_name),))
        identified = (await service.list_orders()).items[0]

        # Act / Assert
        with pytest.raises(ConflictError):
            await service.resolve_order(
                identified.id, supplier_id=supplier.id, remember=False, actor_user_id=owner.id
            )


class TestAnOrderRowNobodyCouldInterpret:
    """RF-08 y el Artículo II sobre la fila de órdenes que no se pudo tipar."""

    async def test_it_opens_a_case_instead_of_stopping_in_quarantine(
        self, session: AsyncSession
    ) -> None:
        """El agujero que el converge encontró: se publicaba y nadie escuchaba.

        `ingestion` publicaba `PurchaseOrderRowsQuarantined` desde el primer día
        y no había un solo suscriptor: la fila quedaba en cuarentena en `staging`
        y ahí terminaba. En esta pantalla es peor que en cualquier otra — la 007
        existe porque los pedidos se pierden, y un pedido que la plataforma nunca
        admite haber visto es el caso más literal de eso.
        """
        # Act
        await events.publish(
            PurchaseOrderRowsQuarantined(
                batch_id=11,
                cases=(
                    QuarantinedRow(
                        staging_row_id=41,
                        reason="La fila no tiene numero de orden",
                        excerpt="Herramientas Cuyo SRL;;COR-0078;10;Pendiente de envio",
                    ),
                ),
            ),
            session,
        )

        # Assert
        opened = (
            (
                await session.execute(
                    select(ExceptionCase).where(ExceptionCase.kind == UNREADABLE_ORDER_ROW)
                )
            )
            .scalars()
            .all()
        )
        assert len(opened) == 1
        assert opened[0].status is CaseStatus.PENDING
        assert opened[0].reason == "La fila no tiene numero de orden"
        assert opened[0].payload["excerpt"] == (
            "Herramientas Cuyo SRL;;COR-0078;10;Pendiente de envio"
        )
