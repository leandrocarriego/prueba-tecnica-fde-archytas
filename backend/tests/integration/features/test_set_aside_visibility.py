"""Lo apartado se ve: los orígenes que apartaban en silencio, y la cola que lo muestra.

La 011 no resuelve uno de los doce problemas — termina de cumplir el que está
antes que los doce, y que el cliente enunció con sus palabras: *«que si algo no
se puede resolver solo, nos avise en vez de adivinar mal»*.

Hasta esta feature el sistema hacía bien lo difícil —no adivinaba— y no hacía lo
fácil: avisar. Cuatro orígenes apartaban a `staging` y no se lo contaban a nadie,
así que lo apartado quedaba guardado, contado y **invisible**, que para el que
tiene que decidir es lo mismo que si se hubiera perdido.

**Por qué los fixtures se derivan.** Cuatro de las cinco pantallas se capturaron
un día bueno: sólo la de ventas trae filas ilegibles, doce. Probar que lo
apartado se ve necesita algo apartado, así que las variantes rotas salen de
romper **una celda** de la página fijada (`portal_factory`), nunca de escribir un
HTML a mano y nunca del portal en vivo (`TEST-03`).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.ingestion.service import IngestionService
from app.modules.sales.models import Sale
from app.modules.sales.service import SalesService
from app.modules.triage.models import CaseStatus, ExceptionCase
from app.modules.triage.service import (
    HISTORY_ORIGIN,
    INVOICE_ORIGIN,
    MISSING_PRODUCT,
    PRICE_LIST_ORIGIN,
    RESOLVED_ELSEWHERE,
    STALE_DAYS_KEY,
    UNKNOWN_CATEGORY,
    UNKNOWN_PRODUCT,
    UNREADABLE_HISTORY,
    UNREADABLE_INVOICE_ROW,
    UNREADABLE_MESSAGE_ROW,
    UNREADABLE_ORDER_ROW,
    UNREADABLE_PAYMENT_ROW,
    UNREADABLE_ROW,
    UNREADABLE_SALE_ROW,
    UNREADABLE_SUPPLIER_ROW,
    TriageService,
)
from app.shared.events import (
    BusinessParameterChanged,
    InvoiceRowsQuarantined,
    KnownProductsMissing,
    MessageRowsQuarantined,
    MissingProduct,
    PriceHistoryRowsQuarantined,
    PriceRowsQuarantined,
    QuarantinedRow,
    QuarantinedSourceReopened,
    QuarantinedSourceResolved,
    UnknownCategory,
    UnknownCategoryObserved,
    UnknownProduct,
    UnknownProductsObserved,
    events,
)
from app.shared.sections import BusinessSection
from tests.factories.portal_factory import (
    messages_with_a_broken_row,
    purchase_orders_with_a_broken_row,
    sales_page_bytes,
    supplier_ledger_with_a_broken_balance,
    supplier_ledger_with_a_broken_payment,
    supplier_ledger_with_both_broken,
)

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.portal]

EVERY_AREA = frozenset(BusinessSection)

# Los cuatro motivos con los que el **parser** aparta una venta. `sales` aparta
# además por razones suyas —un producto que no existe, un monto atípico—, y esas
# no abren caso en esta cola: se leyeron bien, lo que no cierra es el negocio.
# La diferencia importa acá porque sólo las primeras tienen un pendiente que
# cerrar.
PARSER_COULD_NOT_READ = (
    "La fila no trae fecha",
    "La fecha no corresponde a un día que exista",
    "La fila no trae monto",
    "La cantidad no puede ser negativa",
)


async def a_held_sale_with_its_case(
    session: AsyncSession,
) -> tuple[Sale, ExceptionCase]:
    """Una venta que el parser no pudo leer, y el pendiente que la anuncia.

    Se busca por `staging_row_id`, que es la **misma** clave con la que el caso
    se abrió. Emparejarlas por cualquier otra cosa haría pasar el test aunque el
    cierre automático cerrara el caso equivocado, que es justo el riesgo que el
    plan anotó.
    """
    broken = next(
        record
        for record in (await SalesService(session).review_queue()).broken
        if record.reason in PARSER_COULD_NOT_READ
    )
    sale = await session.get(Sale, broken.id)
    assert sale is not None
    case = next(
        item
        for item in await cases_of(session, UNREADABLE_SALE_ROW)
        if item.payload["staging_row_id"] == sale.staging_row_id
    )
    return sale, case


async def cases_of(session: AsyncSession, kind: str) -> list[ExceptionCase]:
    """Los casos de una clase, en el orden en que se abrieron."""
    result = await session.execute(
        select(ExceptionCase).where(ExceptionCase.kind == kind).order_by(ExceptionCase.id)
    )
    return list(result.scalars().all())


async def a_broken_payment_arrives(session: AsyncSession) -> None:
    """El padrón, con un comprobante cuya fecha no se puede leer."""
    await IngestionService(session).normalize_supplier_ledger(
        raw_document_id=1, content=supplier_ledger_with_a_broken_payment()
    )


async def a_broken_supplier_arrives(session: AsyncSession) -> None:
    """El padrón, con un proveedor cuyo saldo no se puede leer."""
    await IngestionService(session).normalize_supplier_ledger(
        raw_document_id=1, content=supplier_ledger_with_a_broken_balance()
    )


async def a_broken_message_arrives(session: AsyncSession) -> None:
    """El buzón, con un mensaje cuya fecha no se puede leer."""
    await IngestionService(session).normalize_messages(
        raw_document_id=2, content=messages_with_a_broken_row()
    )


async def a_broken_order_arrives(session: AsyncSession) -> None:
    """La pantalla de órdenes, con una orden cuya fecha no se puede leer."""
    await IngestionService(session).normalize_purchase_orders(
        raw_document_id=3, content=purchase_orders_with_a_broken_row()
    )


async def the_sales_screen_arrives(session: AsyncSession) -> None:
    """La pantalla de ventas entera, con las doce filas rotas que ya trae."""
    await IngestionService(session).normalize_sales(raw_document_id=4, content=sales_page_bytes())


class TestNothingIsSetAsideInSilence:
    """H1: que nada quede apartado en silencio.

    Un caso por origen, y la afirmación es la misma cuatro veces: la fila se
    aparta **y** aparece. Antes de la 011 las tres primeras se apartaban y no
    aparecían.
    """

    async def test_a_supplier_nobody_could_read_opens_a_case(self, session: AsyncSession) -> None:
        """RF-01, y es el que más costó: hasta que se arregló el parser era imposible.

        `parse_supplier_ledger` descartaba el motivo del saldo —`balance, _`— así
        que la fila se guardaba legible con `balance=None` y no había cuarentena
        que anunciar. El evento y el suscriptor de la 011 estaban construidos y
        no se podían disparar: la feature avisaba de todo salvo de esto, que era
        justamente lo que prometía arreglar.
        """
        # Act
        await a_broken_supplier_arrives(session)

        # Assert
        opened = await cases_of(session, UNREADABLE_SUPPLIER_ROW)
        assert len(opened) == 1
        assert opened[0].payload["origin"] == "padrón de proveedores"
        assert "Aceros Belgrano SA" in opened[0].payload["excerpt"]

    async def test_a_readable_supplier_is_not_set_aside(self, session: AsyncSession) -> None:
        """La otra mitad, y no es de trámite.

        Propagar el motivo puede pasarse de largo y mandar a cuarentena filas que
        se leen bien, que sería el Artículo II al revés: en vez de perder en
        silencio, inundar la cola. Ocho proveedores, siete intactos.
        """
        # Act
        await a_broken_supplier_arrives(session)

        # Assert
        assert len(await cases_of(session, UNREADABLE_SUPPLIER_ROW)) == 1

    async def test_a_payment_nobody_could_read_opens_a_case(self, session: AsyncSession) -> None:
        """RF-02."""
        # Act
        await a_broken_payment_arrives(session)

        # Assert
        opened = await cases_of(session, UNREADABLE_PAYMENT_ROW)
        assert len(opened) == 1
        assert opened[0].reason == "La fecha no corresponde a un día que exista"
        assert opened[0].status is CaseStatus.PENDING

    async def test_a_message_nobody_could_read_opens_a_case(self, session: AsyncSession) -> None:
        """RF-03.

        El buzón es el que el cliente dejó de mirar. Un mensaje que además no se
        podía interpretar estaba, hasta acá, en un segundo lugar al que nadie
        entraba: una tabla de `staging` sin pantalla ninguna.
        """
        # Act
        await a_broken_message_arrives(session)

        # Assert
        opened = await cases_of(session, UNREADABLE_MESSAGE_ROW)
        assert len(opened) == 1
        assert opened[0].reason == "La fecha no corresponde a un día que exista"

    async def test_an_order_nobody_could_read_opens_a_case(self, session: AsyncSession) -> None:
        """RF-04 — verificación de lo ya construido en la 007, no obra nueva.

        La spec 011 se firmó diciendo que una orden apartada no llegaba a la
        pantalla, y era falso: llega desde la 007. La enmienda corrigió el
        relevamiento y dejó RF-04 como requisito igual, con este test como toda
        su implementación. Lo que sostiene es que no se caiga.
        """
        # Act
        await a_broken_order_arrives(session)

        # Assert
        opened = await cases_of(session, UNREADABLE_ORDER_ROW)
        assert len(opened) == 1

    async def test_a_sale_nobody_could_read_opens_a_case(self, session: AsyncSession) -> None:
        """RF-05.

        Doce, que son las que midió el relevamiento: tres sin fecha, tres con una
        fecha que no existe, tres sin monto y tres con cantidad negativa. La 009
        las apartaba y dejaba el evento sin suscriptor **a propósito**; la 011
        revirtió esa decisión, y esto es lo que fija que quedó revertida.
        """
        # Act
        await the_sales_screen_arrives(session)

        # Assert
        opened = await cases_of(session, UNREADABLE_SALE_ROW)
        assert len(opened) == 12

    async def test_the_five_land_on_the_same_screen(self, session: AsyncSession) -> None:
        """RF-06: en un solo lugar, no en cinco.

        Es la mitad del problema que la feature resuelve. La otra mitad —que
        existan— la prueban los cuatro tests de arriba; que se lean juntos es
        esta, y es la que evita que la respuesta sea «sí, están, cada uno en su
        pantalla».
        """
        # Arrange — el padrón trae el proveedor y el comprobante de una sola
        # lectura, que es como llegan de verdad.
        await IngestionService(session).normalize_supplier_ledger(
            raw_document_id=1,
            content=supplier_ledger_with_both_broken(),
        )
        await a_broken_message_arrives(session)
        await a_broken_order_arrives(session)
        await the_sales_screen_arrives(session)

        # Act
        listed = await TriageService(session).list_cases(limit=200, visible=EVERY_AREA)

        # Assert
        kinds = {item.kind for item in listed.items}
        assert {
            UNREADABLE_SUPPLIER_ROW,
            UNREADABLE_PAYMENT_ROW,
            UNREADABLE_SUPPLIER_ROW,
            UNREADABLE_MESSAGE_ROW,
            UNREADABLE_ORDER_ROW,
            UNREADABLE_SALE_ROW,
        } <= kinds

    async def test_what_was_set_aside_is_not_counted_as_good(self, session: AsyncSession) -> None:
        """RF-05, la otra mitad: apartada **y** fuera del total.

        Un registro que abre caso y además se suma sería peor que el silencio:
        avisaría y mentiría a la vez.
        """
        # Arrange
        await the_sales_screen_arrives(session)

        # Act
        queue = await SalesService(session).review_queue()

        # Assert — las doce que el parser no pudo leer, por sus cuatro motivos.
        # `broken` guarda todo lo apartado, y la mayor parte lo aparta `sales`
        # por razones suyas —producto inexistente, monto atípico—; lo que esta
        # feature promete son las del parser, y contarlas aparte es lo que
        # distingue «no se pudo leer» de «se leyó y no cierra».
        reasons = [record.reason for record in queue.broken]
        assert reasons.count("La fila no trae fecha") == 3
        assert reasons.count("La fecha no corresponde a un día que exista") == 3
        assert reasons.count("La fila no trae monto") == 3
        assert reasons.count("La cantidad no puede ser negativa") == 3


class TestTheSameThingIsAskedOnce:
    """H1, RF-07: lo repetido se agrupa.

    Es lo que decide si la lista se puede recorrer o se abandona, que es el
    riesgo que el plan marcó como alto: cuatro orígenes que nunca abrieron un
    caso van a abrir el primer día todo lo que tengan pendiente.
    """

    async def test_a_hundred_identical_rows_are_one_case_that_counts_them(
        self, session: AsyncSession
    ) -> None:
        """Cien filas rotas iguales son **un** pendiente que dice que llegó cien veces."""
        # Arrange — cien filas distintas de `staging` que dicen exactamente lo
        # mismo, que es la forma que tiene el problema real: la misma fila rota
        # repetida en la página, no la misma fila leída cien veces.
        await events.publish(
            MessageRowsQuarantined(
                batch_id=1,
                raw_document_id=1,
                cases=tuple(
                    QuarantinedRow(
                        staging_row_id=row_id,
                        reason="La fila no trae fecha",
                        excerpt="— | Insumos Industriales Bahia | Reclamo | Sin leer |",
                    )
                    for row_id in range(1, 101)
                ),
            ),
            session,
        )

        # Assert
        opened = await cases_of(session, UNREADABLE_MESSAGE_ROW)
        assert len(opened) == 1
        assert opened[0].occurrences == 100

    async def test_giving_one_for_reviewed_records_who_and_when(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-08. Lo único que se puede hacer con una fila que el portal publicó rota."""
        # Arrange
        await a_broken_payment_arrives(session)
        case = (await cases_of(session, UNREADABLE_PAYMENT_ROW))[0]

        # Act
        resolved = await TriageService(session).resolve(
            case.id,
            decision={"action": "ignore"},
            user_id=owner.id,
            user_name=owner.name,
            remember=False,
            visible=EVERY_AREA,
        )

        # Assert
        assert resolved.status is CaseStatus.RESOLVED
        assert resolved.resolved_by_user_id == owner.id
        assert resolved.resolved_by_name == owner.name
        assert resolved.resolved_at is not None

    async def test_a_resolved_case_is_still_there_to_be_read(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-23: sale de la lista al instante y queda consultable para siempre.

        La decisión sobre un dato es lo que explica por qué ese dato es como es;
        un sistema que la borra deja de poder contestar «¿por qué este número es
        este?».
        """
        # Arrange
        await a_broken_payment_arrives(session)
        service = TriageService(session)
        case = (await cases_of(session, UNREADABLE_PAYMENT_ROW))[0]
        await service.resolve(
            case.id,
            decision={"action": "ignore"},
            user_id=owner.id,
            remember=False,
            visible=EVERY_AREA,
        )

        # Act
        pending = await service.list_cases(visible=EVERY_AREA, status=CaseStatus.PENDING)
        archived = await service.list_cases(visible=EVERY_AREA, status=CaseStatus.RESOLVED)

        # Assert
        assert case.id not in {item.id for item in pending.items}
        assert case.id in {item.id for item in archived.items}


class TestUnderstandingOneWithoutGoingToLookForIt:
    """H2: el motivo, el recorte, de dónde salió y cuándo se leyó."""

    async def test_a_case_carries_what_it_takes_to_decide(self, session: AsyncSession) -> None:
        """RF-09, RF-10, RF-11 sobre un comprobante ilegible."""
        # Arrange
        before = datetime.now(UTC)

        # Act
        await a_broken_payment_arrives(session)

        # Assert
        case = (await cases_of(session, UNREADABLE_PAYMENT_ROW))[0]
        # RF-09 — por qué no se pudo resolver solo.
        assert case.reason == "La fecha no corresponde a un día que exista"
        # RF-10 — lo que alcanzó a leer, tal como llegó.
        assert "REC-3123" in case.payload["excerpt"]
        # RF-11 — de qué pantalla del portal salió, y cuándo se leyó.
        assert case.payload["origin"] == "comprobantes de pago"
        assert datetime.fromisoformat(case.payload["read_at"]) >= before

    async def test_the_excerpt_is_what_the_row_said_and_not_a_summary(
        self, session: AsyncSession
    ) -> None:
        """RF-10 dice «tal como llegó», y eso es literal.

        El recorte tiene que servir para reconocer la fila en el portal. Un
        resumen no sirve: el que la mira necesita las mismas palabras.
        """
        # Act
        await a_broken_message_arrives(session)

        # Assert
        case = (await cases_of(session, UNREADABLE_MESSAGE_ROW))[0]
        assert case.payload["excerpt"].startswith("—")
        assert "Insumos Industriales Bahia" in case.payload["excerpt"]
        assert case.payload["origin"] == "buzón"


class TestHowLongItHasBeenWaiting:
    """H4: la antigüedad, y a partir de cuándo es demasiada."""

    @staticmethod
    async def a_case_opened_days_ago(session: AsyncSession, days: int) -> ExceptionCase:
        """Un pendiente que llegó hace tantos días."""
        await a_broken_payment_arrives(session)
        case = (await cases_of(session, UNREADABLE_PAYMENT_ROW))[0]
        await session.execute(
            update(ExceptionCase)
            .where(ExceptionCase.id == case.id)
            .values(created_at=datetime.now(UTC) - timedelta(days=days))
        )
        await session.flush()
        return case

    async def test_six_days_is_not_late_and_eight_is(self, session: AsyncSession) -> None:
        """RF-19: sin tocar nada, el límite son siete días."""
        # Arrange
        await self.a_case_opened_days_ago(session, days=6)
        service = TriageService(session)

        # Act
        soon = (await service.list_cases(visible=EVERY_AREA)).items[0]

        # Assert
        assert soon.waiting_days == 6
        assert soon.is_stale is False

    async def test_eight_days_is_late(self, session: AsyncSession) -> None:
        """RF-17."""
        # Arrange
        await self.a_case_opened_days_ago(session, days=8)

        # Act
        late = (await TriageService(session).list_cases(visible=EVERY_AREA)).items[0]

        # Assert
        assert late.waiting_days == 8
        assert late.is_stale is True

    async def test_the_limit_moves_with_the_parameter_and_not_with_the_code(
        self, session: AsyncSession
    ) -> None:
        """RF-18: el dueño lo cambia desde la pantalla que ya existe.

        Se mueve publicando el evento que la pantalla publica, no escribiendo la
        proyección a mano: lo que esto tiene que probar es que el camino entero
        funciona, y `triage` no puede leer la tabla de `operations`.
        """
        # Arrange — el mismo pendiente de ocho días que arriba está demorado.
        await self.a_case_opened_days_ago(session, days=8)
        service = TriageService(session)
        assert (await service.list_cases(visible=EVERY_AREA)).items[0].is_stale is True

        # Act — el dueño se da diez días de plazo.
        await events.publish(
            BusinessParameterChanged(key=STALE_DAYS_KEY, value=10),
            session,
        )

        # Assert
        assert (await service.list_cases(visible=EVERY_AREA)).items[0].is_stale is False

    async def test_the_screen_says_how_many_and_since_when(self, session: AsyncSession) -> None:
        """RF-15 y RF-16, que son el encabezado de la pantalla."""
        # Arrange
        await a_broken_payment_arrives(session)
        await a_broken_message_arrives(session)

        # Act
        listed = await TriageService(session).list_cases(visible=EVERY_AREA)

        # Assert
        assert listed.pending_total == 2
        assert listed.oldest_at is not None

    async def test_the_screen_also_says_what_left_the_queue_today(
        self, session: AsyncSession, owner: User
    ) -> None:
        """La otra mitad del encabezado: la cola se mueve, y se ve que se movió.

        Una pantalla que sólo cuenta lo que queda se lee como una lista que no
        avanza nunca — y el trabajo que sí avanzó es exactamente la razón por la
        que hoy es más corta.

        El día es el del negocio y no el de UTC: entre las 21:00 y la medianoche
        de Buenos Aires, UTC ya cambió de día, y ahí el conteo volvería a cero
        con el local todavía abierto.
        """
        # Arrange — dos apartados, uno resuelto recién.
        await a_broken_payment_arrives(session)
        await a_broken_message_arrives(session)
        service = TriageService(session)
        case = (await cases_of(session, UNREADABLE_PAYMENT_ROW))[0]
        await service.resolve(
            case.id,
            decision={"action": "ignore"},
            user_id=owner.id,
            remember=False,
            visible=EVERY_AREA,
        )

        # Act
        listed = await service.list_cases(visible=EVERY_AREA)

        # Assert — uno menos esperando, y uno contado del lado del que se decidió.
        assert listed.pending_total == 1
        assert listed.resolved_today == 1

    async def test_what_was_decided_yesterday_is_not_of_today(
        self, session: AsyncSession, owner: User
    ) -> None:
        """El conteo es de hoy, y por eso la prueba mueve el reloj hacia atrás."""
        # Arrange
        await a_broken_payment_arrives(session)
        service = TriageService(session)
        case = (await cases_of(session, UNREADABLE_PAYMENT_ROW))[0]
        await service.resolve(
            case.id,
            decision={"action": "ignore"},
            user_id=owner.id,
            remember=False,
            visible=EVERY_AREA,
        )
        # Act — la misma decisión, tomada ayer.
        await session.execute(
            update(ExceptionCase)
            .where(ExceptionCase.id == case.id)
            .values(resolved_at=datetime.now(UTC) - timedelta(days=1))
        )
        await session.flush()

        # Assert
        assert (await service.list_cases(visible=EVERY_AREA)).resolved_today == 0


class TestClosedByTheScreenThatOwnedTheWork:
    """H5, RF-20 y RF-21: la lista no miente cuando el trabajo se hizo en otra parte.

    Pedirle a alguien que cierre acá algo que ya resolvió en la pantalla de
    ventas es trabajo doble, y el día que se olvide la lista vuelve a mentir. Así
    que la lista se corrige sola.
    """

    async def test_correcting_the_sale_closes_the_case_nobody_closed(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-20: deja de figurar entre los pendientes, sin que nadie lo cierre."""
        # Arrange — una venta rota, con su caso abierto.
        await the_sales_screen_arrives(session)
        held, case = await a_held_sale_with_its_case(session)
        assert case.status is CaseStatus.PENDING

        # Act — se resuelve donde corresponde, y nadie toca la cola.
        await SalesService(session).correct_sale(
            held.id,
            values={"sold_on": datetime.now(UTC).date(), "total": "1000"},
            is_estimated=True,
            actor_user_id=owner.id,
        )

        # Assert
        await session.refresh(case)
        assert case.status is CaseStatus.RESOLVED

    async def test_it_says_it_was_resolved_elsewhere_and_names_nobody(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-21: queda registrado cómo se resolvió, y consultable.

        Sin nombre de persona, y es una decisión y no un olvido: la constancia de
        quién hizo el trabajo la tiene la pantalla donde se hizo, y una segunda
        copia acá sólo podría desviarse de la primera.
        """
        # Arrange
        await the_sales_screen_arrives(session)
        held, case = await a_held_sale_with_its_case(session)

        # Act
        await SalesService(session).correct_sale(
            held.id,
            values={"sold_on": datetime.now(UTC).date(), "total": "1000"},
            is_estimated=True,
            actor_user_id=owner.id,
        )

        # Assert
        await session.refresh(case)
        assert case.decision == {
            "action": RESOLVED_ELSEWHERE,
            "where": "la pantalla de ventas",
        }
        assert case.resolved_by_user_id is None
        assert case.resolved_by_name is None
        assert case.resolved_at is not None

    async def test_an_event_that_finds_no_case_is_not_an_error(self, session: AsyncSession) -> None:
        """La mayoría no cierra nada, y eso es lo normal, no una falla.

        La mayor parte de las ventas nunca tuvo un caso. Un evento que no
        encuentra qué cerrar tiene que pasar sin ruido — si levantara, cada venta
        corregida abortaría la transacción del que la corrigió (`GEN-09`).
        """
        # Act / Assert — no levanta.
        await events.publish(
            QuarantinedSourceResolved(
                kind=UNREADABLE_SALE_ROW, key="99999", resolved_where="la pantalla de ventas"
            ),
            session,
        )

        assert await cases_of(session, UNREADABLE_SALE_ROW) == []


class TestUndoingTheWorkPutsThePendingBack:
    """H5, RF-24: la única verdad sobre lo pendiente vale en las dos direcciones.

    La pantalla de ventas deja deshacer una resolución —la 009 lo prometió—, y
    hasta la 011 el caso que se había cerrado solo se quedaba cerrado. La lista
    pasaba a decir que no había nada que revisar sobre un registro que estaba,
    en ese mismo momento, otra vez en revisión.
    """

    async def test_undoing_the_resolution_reopens_the_case(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-24: vuelve a figurar, y tampoco lo reabre nadie a mano."""
        # Arrange — una venta rota, su caso, y el caso cerrado por la pantalla.
        await the_sales_screen_arrives(session)
        held, case = await a_held_sale_with_its_case(session)
        sales = SalesService(session)
        await sales.resolve_group(
            held.code_key, action="distinct", sale_id=None, actor_user_id=owner.id
        )
        await session.refresh(case)
        assert case.status is CaseStatus.RESOLVED

        # Act — alguien se arrepiente, en la pantalla donde se arrepiente.
        await sales.undo_resolution(held.code_key)

        # Assert
        await session.refresh(case)
        assert case.status is CaseStatus.PENDING
        # Sin rastro de una decisión que ya no existe, y la espera se sigue
        # contando desde que llegó y no desde que se reabrió (RF-16).
        assert case.decision is None
        assert case.resolved_at is None

    async def test_a_case_a_person_resolved_by_hand_is_not_reopened(
        self, session: AsyncSession, owner: User
    ) -> None:
        """El borde que importa: una decisión con nombre no se pisa.

        Reabrir por `fingerprint` sin mirar quién cerró el caso borraría la
        decisión de una persona porque otro registro coincidió. El nombre está
        ahí (RF-08) justamente para que eso no pase.
        """
        # Arrange — el caso lo cierra una persona, no la pantalla.
        await the_sales_screen_arrives(session)
        held, case = await a_held_sale_with_its_case(session)
        await TriageService(session).resolve(
            case.id,
            decision={"action": "acknowledge"},
            user_id=owner.id,
            user_name=owner.name,
            remember=False,
            visible=EVERY_AREA,
        )

        # Act — llega el mismo aviso de reapertura que cerraría al automático.
        await events.publish(
            QuarantinedSourceReopened(
                kind=UNREADABLE_SALE_ROW,
                key=str(held.staging_row_id),
                reopened_where="la pantalla de ventas",
            ),
            session,
        )

        # Assert — sigue resuelto, y con el nombre de quien lo resolvió.
        await session.refresh(case)
        assert case.status is CaseStatus.RESOLVED
        assert case.resolved_by_user_id == owner.id

    async def test_an_undo_that_finds_no_case_is_not_an_error(self, session: AsyncSession) -> None:
        """La mayoría de los deshacer no reabren nada, y eso es lo normal."""
        # Act / Assert — no levanta.
        await events.publish(
            QuarantinedSourceReopened(
                kind=UNREADABLE_SALE_ROW, key="99999", reopened_where="la pantalla de ventas"
            ),
            session,
        )

        assert await cases_of(session, UNREADABLE_SALE_ROW) == []


class TestEveryPendingSaysWhereItCameFrom:
    """RF-11 dice «para **cada** pendiente», y eran cinco de once.

    Las seis clases de acá abrían caso desde antes de la 011 y no decían de qué
    pantalla del portal salían ni cuándo se habían leído. Uno solo que no lo
    diga obliga a quien mira la lista a saber de antemano cuáles lo traen, que
    es exactamente el trabajo que el requisito existe para ahorrarle.

    Se ejercitan por su evento, que es donde vive el cambio: el handler es lo
    que traduce un hecho publicado en un pendiente que se puede leer.
    """

    async def test_the_six_that_predate_this_feature_say_it_too(
        self, session: AsyncSession
    ) -> None:
        """RF-11 sobre las seis clases viejas."""
        # Arrange / Act
        row = QuarantinedRow(
            staging_row_id=1, reason="No se pudo leer", excerpt="…", product_code="A1"
        )
        for event in (
            PriceRowsQuarantined(batch_id=1, cases=(row,)),
            PriceHistoryRowsQuarantined(product_code="A1", cases=(row,)),
            InvoiceRowsQuarantined(batch_id=1, cases=(row,)),
            UnknownProductsObserved(
                batch_id=1,
                cases=(
                    UnknownProduct(
                        staging_row_id=2,
                        product_code="A2",
                        description="Un caño",
                        price=Decimal("10"),
                    ),
                ),
            ),
            KnownProductsMissing(
                batch_id=1,
                products=(MissingProduct(product_id=7, product_code="A3", description="Otro"),),
            ),
            UnknownCategoryObserved(
                batch_id=1,
                cases=(UnknownCategory(category_text="ferretería", product_codes=("A4",)),),
            ),
        ):
            await events.publish(event, session)

        # Assert — las seis dicen de dónde salieron y cuándo se leyeron.
        expected_origin = {
            UNREADABLE_ROW: PRICE_LIST_ORIGIN,
            UNREADABLE_HISTORY: HISTORY_ORIGIN,
            UNREADABLE_INVOICE_ROW: INVOICE_ORIGIN,
            UNKNOWN_PRODUCT: PRICE_LIST_ORIGIN,
            MISSING_PRODUCT: PRICE_LIST_ORIGIN,
            UNKNOWN_CATEGORY: PRICE_LIST_ORIGIN,
        }
        for kind, origin in expected_origin.items():
            cases = await cases_of(session, kind)
            assert len(cases) == 1, kind
            assert cases[0].payload["origin"] == origin, kind
            assert cases[0].payload["read_at"], kind

    async def test_a_rubro_that_came_back_does_not_claim_it_was_read(
        self, session: AsyncSession
    ) -> None:
        """El único que puede no traer `read_at`, y es la respuesta honesta.

        Una regla revocada devuelve productos a la cola sin que se haya leído
        nada — el `batch_id` viene en cero por eso—, así que poner ahí el
        momento de la revocación sería llamar «cuándo se leyó» a cuándo alguien
        cambió de opinión. De dónde salió sí se sabe, y se dice.
        """
        # Act
        await events.publish(
            UnknownCategoryObserved(
                batch_id=0,
                cases=(UnknownCategory(category_text="bulonería", product_codes=("A9",)),),
            ),
            session,
        )

        # Assert
        case = (await cases_of(session, UNKNOWN_CATEGORY))[0]
        assert case.payload["origin"] == PRICE_LIST_ORIGIN
        assert "read_at" not in case.payload


class TestWhatWasSetAsideBeforeSurfacesOnItsOwn:
    """La pata sobre la que se apoya no haber hecho un backfill (tarea 24).

    Lo que quedó en cuarentena **antes** de que existieran estos suscriptores no
    tiene caso, y se decidió no abrírselo con una tarea de una vez, sino dejar
    que aflore en la próxima lectura. Esa decisión se apoya en un solo hecho: que
    estas pantallas se releen **enteras**, así que la fila rota se vuelve a
    apartar y ahí sí abre caso.

    Es un hecho, no una esperanza, y por eso se prueba. Si fuera falso, lo
    apartado hace meses seguiría invisible y la decisión tendría que ser otra —
    que es exactamente lo que este test avisaría.

    El estado «apartado sin caso» se arma borrando el caso que la primera lectura
    abrió: es el mismo estado en el que quedó la base antes de esta feature, con
    la fila en `staging` y nada en la cola.
    """

    async def test_a_row_quarantined_before_opens_its_case_on_the_next_reading(
        self, session: AsyncSession
    ) -> None:
        """El padrón y los comprobantes vuelven a abrir el caso solos.

        El buzón **no**, y no está acá por eso: ver el test de abajo.
        """
        for arrives, kind in (
            (a_broken_supplier_arrives, UNREADABLE_SUPPLIER_ROW),
            (a_broken_payment_arrives, UNREADABLE_PAYMENT_ROW),
        ):
            # Arrange — una lectura abre el caso, y lo borramos: así quedaba la
            # base antes de la 011, con la fila apartada y la cola vacía.
            await arrives(session)
            assert await cases_of(session, kind), kind
            await session.execute(delete(ExceptionCase).where(ExceptionCase.kind == kind))
            await session.flush()
            assert await cases_of(session, kind) == [], kind

            # Act — la próxima lectura de la misma pantalla.
            await arrives(session)

            # Assert — aflora solo, sin que nadie corra un backfill.
            assert await cases_of(session, kind), kind

    async def test_the_inbox_is_the_one_that_does_not(self, session: AsyncSession) -> None:
        """Y es un hecho medido, no una omisión: el buzón no lo hace.

        La decisión de no correr un backfill se apoyaba en que las cuatro
        pantallas se releen enteras. Para el buzón es falso, y el motivo es
        fino: el `external_id` de un mensaje se compone con fecha, remitente y
        asunto, y una fecha que no se pudo leer compone el literal `"None|…"`,
        que es una clave tan buena como cualquier otra. Así que el mensaje roto
        queda **conocido** desde la primera lectura y el filtro lo saca de todas
        las siguientes.

        Para lo que se aparte de acá en adelante da igual —el caso ya está
        abierto—. Lo que significa es que lo que el buzón publicó roto **antes**
        de que existieran estos suscriptores no aflora solo.

        El test afirma el hecho tal como es, sin celebrarlo: el día que alguien
        cambie el filtro o corra un backfill, este test falla y le avisa que la
        decisión que lo justificaba cambió.
        """
        # Arrange — como quedaba la base antes de la 011: apartado y sin caso.
        await a_broken_message_arrives(session)
        assert await cases_of(session, UNREADABLE_MESSAGE_ROW)
        await session.execute(
            delete(ExceptionCase).where(ExceptionCase.kind == UNREADABLE_MESSAGE_ROW)
        )
        await session.flush()

        # Act — la próxima lectura del buzón entero.
        await a_broken_message_arrives(session)

        # Assert — no vuelve, porque ya es conocido.
        assert await cases_of(session, UNREADABLE_MESSAGE_ROW) == []
