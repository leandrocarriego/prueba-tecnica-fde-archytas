"""What `triage` does when something happens elsewhere.

Sixteen subscriptions: one per way the platform can fail to resolve something
on its own, plus the two that close a case when the work got done on the screen
that owned it and reopen it if that work is undone, plus the one that keeps the
parameter this module reads. None of them knows which module published: a case is a case, whether
it came from an unreadable row of the price list, from a product nobody has
ever heard of, or from a row of the invoices (004) or the purchase orders (007)
screen.

The queue never had to change shape to take any of them, which is the point of
a generic queue: a `kind`, a free-form payload, and the decision learned as a
rule.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.triage.service import (
    DISPUTED_ENTRY_REASON,
    DISPUTED_INVOICE,
    DISPUTED_ORDER,
    HISTORY_ORIGIN,
    INVOICE_ORIGIN,
    MESSAGE_ORIGIN,
    MISSING_PRODUCT,
    MISSING_PRODUCT_REASON,
    ORDER_ORIGIN,
    PAYMENT_ORIGIN,
    PRICE_LIST_ORIGIN,
    SALE_ORIGIN,
    STALE_DAYS_KEY,
    SUPPLIER_ORIGIN,
    UNKNOWN_CATEGORY,
    UNKNOWN_CATEGORY_REASON,
    UNKNOWN_PRODUCT,
    UNKNOWN_PRODUCT_REASON,
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
    DailyDigestContribution,
    DailyDigestRequested,
    InvoiceRowsQuarantined,
    KnownProductsMissing,
    ManualEntryDisputed,
    MessageRowsQuarantined,
    PaymentRowsQuarantined,
    PendingWorkReported,
    PriceHistoryRowsQuarantined,
    PriceRowsQuarantined,
    PurchaseOrderRowsQuarantined,
    QuarantinedSourceReopened,
    QuarantinedSourceResolved,
    SaleRowsQuarantined,
    SalesHeld,
    SupplierRowsQuarantined,
    UnknownCategoryObserved,
    UnknownProductsObserved,
    events,
)
from app.shared.sections import BusinessSection

logger = get_logger(__name__)

# Cuántos motivos nombra el resumen uno por uno. El resto va en la cuenta.
DIGEST_LINES = 5


@events.subscribe(DailyDigestRequested)
async def contribute_to_the_digest(event: DailyDigestRequested, session: AsyncSession) -> None:
    """Say how many decisions are waiting, and for what.

    **Es la cola entera y no la de un área.** El recorte por permisos es de la
    pantalla, que lo hace contra quien la está mirando; un resumen que sale a un
    teléfono no tiene a nadie mirando todavía, y contar la mitad sería peor que
    contar de más: el que lo recibe entra, ve el recorte que le toca y decide.

    Los motivos van agrupados con su cuenta, no uno por caso. Dieciséis
    renglones que dicen lo mismo con distinto proveedor no son un resumen.
    """
    service = TriageService(session)
    waiting = await service.count_pending()
    reasons = await service.pending_by_reason(DIGEST_LINES) if waiting else []
    await events.publish(
        DailyDigestContribution(
            source="decisions",
            pending=waiting,
            lines=tuple(f"• {reason} ({total})" for reason, total in reasons),
        ),
        session,
    )
    del event


@events.subscribe(PriceRowsQuarantined)
async def open_unreadable_rows(event: PriceRowsQuarantined, session: AsyncSession) -> None:
    """A row of the list could not be interpreted (RF-06)."""
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_ROW,
            section=BusinessSection.PURCHASING,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "product_code": case.product_code,
                "excerpt": case.excerpt,
                "origin": PRICE_LIST_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            key=f"{case.product_code or case.excerpt}|{case.reason}",
            batch_id=event.batch_id,
        )
    logger.info("Unreadable rows queued", extra={"cases": len(event.cases)})


@events.subscribe(UnknownProductsObserved)
async def open_unknown_products(event: UnknownProductsObserved, session: AsyncSession) -> None:
    """The list brought a product the catalog does not know (RF-07)."""
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNKNOWN_PRODUCT,
            section=BusinessSection.PURCHASING,
            reason=UNKNOWN_PRODUCT_REASON,
            payload={
                "staging_row_id": case.staging_row_id,
                "product_code": case.product_code,
                "description": case.description,
                "price": str(case.price),
                "origin": PRICE_LIST_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            key=case.product_code,
            batch_id=event.batch_id,
        )
    logger.info("Unknown products queued", extra={"cases": len(event.cases)})


@events.subscribe(KnownProductsMissing)
async def open_missing_products(event: KnownProductsMissing, session: AsyncSession) -> None:
    """A known product stopped coming in the list (RF-28)."""
    service = TriageService(session)
    for product in event.products:
        await service.open_case(
            kind=MISSING_PRODUCT,
            section=BusinessSection.PURCHASING,
            reason=MISSING_PRODUCT_REASON,
            payload={
                "product_id": product.product_id,
                "product_code": product.product_code,
                "description": product.description,
                "origin": PRICE_LIST_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            key=str(product.product_id),
            batch_id=event.batch_id,
        )
    logger.info("Missing products queued", extra={"cases": len(event.products)})


@events.subscribe(PriceHistoryRowsQuarantined)
async def open_unreadable_history(
    event: PriceHistoryRowsQuarantined, session: AsyncSession
) -> None:
    """The published history of a product could not be read (RF-39).

    The product keeps its current price: nothing in this path touches it.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_HISTORY,
            section=BusinessSection.PURCHASING,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "product_code": event.product_code,
                "excerpt": case.excerpt,
                "origin": HISTORY_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            key=f"{event.product_code}|{case.excerpt}",
        )
    logger.info(
        "Unreadable history queued",
        extra={"product_code": event.product_code, "cases": len(event.cases)},
    )


@events.subscribe(InvoiceRowsQuarantined)
async def open_unreadable_invoice_rows(
    event: InvoiceRowsQuarantined, session: AsyncSession
) -> None:
    """A row of the invoices screen could not be typed (RF-07, RF-34 of 004).

    This subscription is what makes the Artículo II true on the invoices side.
    `ingestion` published this event from the first day and **nobody listened**:
    the row went to quarantine in `staging` and stopped there, so it was not
    counted, not shown and never decided — the silence the article exists to
    forbid. Its two siblings on the price side have opened a case since 001;
    this one did not, and nothing failed loudly enough for anybody to notice.

    What a person can do about it is **see it and say they saw it**, and no
    more: an invoice is only ever born from a row the portal published, and
    typing one by hand from this queue would be loading an invoice by hand,
    which the signed spec puts out of scope. So it is the same shape as an
    unreadable history — the excerpt, and a decision that closes it.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_INVOICE_ROW,
            section=BusinessSection.PURCHASING,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "excerpt": case.excerpt,
                "origin": INVOICE_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            key=f"{case.excerpt}|{case.reason}",
            batch_id=event.batch_id,
        )
    logger.info("Unreadable invoice rows queued", extra={"cases": len(event.cases)})


@events.subscribe(PurchaseOrderRowsQuarantined)
async def open_unreadable_order_rows(
    event: PurchaseOrderRowsQuarantined, session: AsyncSession
) -> None:
    """A row of the purchase orders screen could not be typed (RF-08 of 007).

    The same subscription the invoices needed, on the screen where losing a row
    hurts most: 007 exists because *«nadie sigue los pedidos»*, and a purchase
    order that is quarantined without opening a case is a pedido nobody follows
    for the most literal reason there is — the platform never admitted it saw
    it.

    What a person can do is see it and say they saw it. An order is only ever
    born from a row the portal published, and typing one by hand here would be
    loading an order by hand, which no requirement asks for.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_ORDER_ROW,
            section=BusinessSection.PURCHASING,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "excerpt": case.excerpt,
                # De qué pantalla salió y cuándo se leyó, como los cuatro que
                # agrega la 011. Este caso existe desde la 007 y no lo decía, y
                # RF-11 dice «cada pendiente»: uno solo que no lo diga obliga a
                # quien mira la lista a saber de antemano cuáles lo traen.
                "origin": ORDER_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            key=f"{case.excerpt}|{case.reason}",
            batch_id=event.batch_id,
        )
    logger.info("Unreadable order rows queued", extra={"cases": len(event.cases)})


@events.subscribe(UnknownCategoryObserved)
async def open_unknown_categories(event: UnknownCategoryObserved, session: AsyncSession) -> None:
    """A written form of a category nobody has decided about (RF-21 of 008).

    One case per written form, and the fingerprint is the text: a hundred
    products of the same batch spelled the same way ask **one** question, and
    the count of how many times it came back is what the screen shows.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNKNOWN_CATEGORY,
            section=BusinessSection.PURCHASING,
            reason=UNKNOWN_CATEGORY_REASON,
            payload={
                "category_text": case.category_text,
                "product_codes": list(case.product_codes),
                "products": len(case.product_codes),
                "origin": PRICE_LIST_ORIGIN,
                # **El único caso donde `read_at` puede no existir, y no es un
                # olvido.** RF-11 pide de dónde salió y *cuándo se leyó*, y este
                # evento se publica por dos caminos: una lectura de la lista, y
                # una regla que alguien revocó (008), que devuelve a la cola
                # productos que ya estaban clasificados. En el segundo no hubo
                # lectura ninguna — el `batch_id` viene en cero justamente por
                # eso—, y poner ahí el momento de la revocación sería llamar
                # «cuándo se leyó» a cuándo Marcela cambió de opinión.
                **({"read_at": event.occurred_at.isoformat()} if event.batch_id else {}),
            },
            key=case.category_text,
            batch_id=event.batch_id or None,
        )
    logger.info("Unknown categories queued", extra={"cases": len(event.cases)})


# ── the four silences 011 closes ─────────────────────────────────────────────
#
# All four are the same subscription written four times, and that repetition is
# the honest shape: each one names its own screen of the portal, its own area of
# the business and its own kind, and the only thing they share — what a
# quarantined row *is* — is already shared, in `QuarantinedRow`.
#
# None of them learns a rule. `remember=True` is the default of `resolve`, so
# the route has to be told otherwise; what makes these four different is that
# there is nothing to learn: a row the portal published broken cannot be fixed
# from here, the portal is read-only, and typing it by hand is out of scope. So
# what a person can do is see it, understand it and leave it on record that they
# did — which is more than the nothing they could do before.


@events.subscribe(SupplierRowsQuarantined)
async def open_unreadable_supplier_rows(
    event: SupplierRowsQuarantined, session: AsyncSession
) -> None:
    """A row of the supplier register could not be typed (RF-01 of 011)."""
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_SUPPLIER_ROW,
            section=BusinessSection.PURCHASING,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "excerpt": case.excerpt,
                "origin": SUPPLIER_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            key=f"{case.excerpt}|{case.reason}",
        )
    logger.info("Unreadable supplier rows queued", extra={"cases": len(event.cases)})


@events.subscribe(PaymentRowsQuarantined)
async def open_unreadable_payment_rows(
    event: PaymentRowsQuarantined, session: AsyncSession
) -> None:
    """A payment record could not be typed (RF-02 of 011)."""
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_PAYMENT_ROW,
            section=BusinessSection.PURCHASING,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "excerpt": case.excerpt,
                "origin": PAYMENT_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            key=str(case.staging_row_id),
            batch_id=event.batch_id,
        )
    logger.info("Unreadable payment rows queued", extra={"cases": len(event.cases)})


@events.subscribe(MessageRowsQuarantined)
async def open_unreadable_message_rows(
    event: MessageRowsQuarantined, session: AsyncSession
) -> None:
    """A message of the inbox could not be typed (RF-03 of 011).

    This is the one that closes the loop the client described with his own
    words: the portal inbox stopped being read because it was one more place to
    remember to open. A message the platform could not even type was, until
    now, in a *second* such place — a `staging` table with no screen at all.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_MESSAGE_ROW,
            section=BusinessSection.PURCHASING,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "excerpt": case.excerpt,
                "origin": MESSAGE_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            # The excerpt, not the row id. Two broken messages that say the
            # same thing are one question with a count beside it (RF-07), and a
            # key on the row id would make them two.
            #
            # It also survives a change on the other side of the wall: whether
            # the inbox re-types a broken message on every reading is
            # `ingestion`'s decision and it is open right now (see the comment
            # in `normalize_messages`). With the excerpt as the key, this
            # handler gives the same answer either way.
            key=f"{case.excerpt}|{case.reason}",
            batch_id=event.batch_id,
        )
    logger.info("Unreadable message rows queued", extra={"cases": len(event.cases)})


@events.subscribe(SaleRowsQuarantined)
async def open_unreadable_sale_rows(event: SaleRowsQuarantined, session: AsyncSession) -> None:
    """A sales record could not be typed (RF-05 of 011).

    009 published this event and left it deliberately unsubscribed, arguing
    that the sales review queue was already a human surface and a second one
    would show the same record to two people. 011 decided the other way, and
    the argument that decided it is the one 009 could not have made yet: there
    is **one** list of what is pending (RF-06), and the objection about two
    screens disagreeing is what RF-20 answers — resolve the sale on its own
    screen and this case closes itself.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_SALE_ROW,
            section=BusinessSection.SALES,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "excerpt": case.excerpt,
                "origin": SALE_ORIGIN,
                "read_at": event.occurred_at.isoformat(),
            },
            # The row id, because that is the key the sales screen will send
            # back when the record gets resolved there (RF-20). The two have to
            # be the same string or the case never closes.
            key=str(case.staging_row_id),
            batch_id=event.batch_id,
        )
    logger.info("Unreadable sale rows queued", extra={"cases": len(event.cases)})


@events.subscribe(SalesHeld)
async def open_held_sales(event: SalesHeld, session: AsyncSession) -> None:
    """A sales record got in and still may not be added up.

    The other half of the subscription above, and the half that was missing.
    That one takes the rows `staging` could not type at all; these are records
    that made it into `core` whole and are held anyway — two versions of the
    same sale that disagree, a sale pointing at a product nobody knows, a total
    wildly out of line, a field the parser could not read.

    Until now they lived only on the sales screen, which made RF-06 of 011 —
    **una sola lista de lo que está pendiente** — true for four origins and
    false for this one. A person emptying this queue had no way of knowing that
    another list existed, and that is exactly what happened with the portal's
    inbox before 011: what kept nobody looking at it was not its length, it was
    that it was one more place to remember to go.

    The `kind` travels in the event rather than being decided here, and that is
    deliberate: the kind and the key are one pair — `repeated_sale` is keyed by
    the code, `broken_sale` by the row — and whoever resolves it sends the same
    pair back to close it. Rebuilding either side here would close a case
    nobody resolved.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=case.kind,
            section=BusinessSection.SALES,
            reason=case.reason,
            payload={
                "code": case.code,
                # Cuántas versiones hay que mirar, para que el renglón de la
                # cola diga el tamaño de la decisión antes de abrirla.
                "versions": case.versions,
                # La llave viaja también **adentro** del caso, y no sólo dentro
                # de la huella. La huella es un hash: sirve para no abrir dos
                # veces el mismo caso y no sirve para volver a encontrar de qué
                # venta hablaba. Sin esto la pantalla tendría el caso y no el
                # registro, que es tanto como no tener el caso.
                "key": case.key,
                "origin": SALE_ORIGIN,
                "held_at": event.occurred_at.isoformat(),
            },
            key=case.key,
            batch_id=event.batch_id,
        )
    logger.info("Held sales queued", extra={"cases": len(event.cases)})


@events.subscribe(PendingWorkReported)
async def reconcile_pending_work(event: PendingWorkReported, session: AsyncSession) -> None:
    """Un módulo contó todo lo que tiene esperando a una persona.

    La suscripción que le faltaba a esta cola desde el principio, y el agujero
    que tapa no se ve mirando el código: se ve el día que se enciende. Todo lo
    demás acá abre un caso **en el momento en que algo pasa**, así que la cola
    conoce exactamente lo que ocurrió desde que existe el evento que lo cuenta.
    Lo que estaba apartado desde antes —una factura en revisión desde marzo, un
    proveedor sin CUIT desde siempre— no lo publicó nadie nunca, y para la cola
    no existe. El dueño ve «hay 12 ventas esperando una decisión», entra, y la
    cola está vacía.

    Acá el informe es completo, así que se hacen las dos mitades: se abre lo que
    falta y se cierra lo que ya no está. Es lo que hace que la promesa —*una sola
    verdad sobre si algo sigue pendiente*— valga también hacia atrás.
    """
    opened, closed = await TriageService(session).reconcile(kinds=event.kinds, items=event.items)
    if opened or closed:
        logger.info(
            "Pending work reconciled",
            extra={"kinds": list(event.kinds), "opened": opened, "closed": closed},
        )


@events.subscribe(QuarantinedSourceResolved)
async def close_case_resolved_elsewhere(
    event: QuarantinedSourceResolved, session: AsyncSession
) -> None:
    """What opened a case got resolved on its own screen (RF-20, RF-21).

    `triage` does not know, and must not know, who published this: `purchases`
    and `sales` announce that they finished something and whoever cares
    listens. The alternative — either of them calling `TriageService` — is the
    cross-module import the Artículo IV forbids.

    Most of these close nothing, because most payments and most sales never had
    a case. That is not an error and nothing is logged as one.
    """
    closed = await TriageService(session).close_resolved_elsewhere(
        kind=event.kind, key=event.key, where=event.resolved_where
    )
    if closed:
        logger.info(
            "Case closed elsewhere",
            extra={"kind": event.kind, "where": event.resolved_where},
        )


@events.subscribe(QuarantinedSourceReopened)
async def reopen_case_undone_elsewhere(
    event: QuarantinedSourceReopened, session: AsyncSession
) -> None:
    """The work that had closed a case got undone on its own screen (RF-24).

    The other half of the subscription above, and the reason it is a separate
    event rather than a flag on that one: closing and reopening are two facts,
    not one fact with a direction, and a subscriber that only cares about one of
    them should not have to read the other to find out.

    Same silence on the ordinary case: most undos are of work that never had a
    case, and finding nothing to reopen is not an error.
    """
    reopened = await TriageService(session).reopen_closed_elsewhere(kind=event.kind, key=event.key)
    if reopened:
        logger.info(
            "Case reopened elsewhere",
            extra={"kind": event.kind, "where": event.reopened_where},
        )


@events.subscribe(BusinessParameterChanged)
async def remember_parameter(event: BusinessParameterChanged, session: AsyncSession) -> None:
    """Keep the value of a parameter this module reads (RF-18).

    `operations` owns the parameters and this module may not read its tables,
    so what it keeps is its own projection of the one value it consumes — and
    only that one: a projection that copied every parameter would be a second
    copy of somebody else's table wearing this module's name.
    """
    if event.key != STALE_DAYS_KEY:
        return
    await TriageService(session).remember_setting(event.key, event.value)


# Cómo nombra `purchases` a cada una de las dos cosas que se pueden cargar a
# mano. Escrito acá y no importado de allá: un módulo no importa otro
# (Artículo IV), y lo que viaja en el evento es justamente un string para que
# las dos puntas puedan nombrarlo sin conocerse.
INVOICE_ENTITY = "invoice"


@events.subscribe(ManualEntryDisputed)
async def open_disputed_entry(event: ManualEntryDisputed, session: AsyncSession) -> None:
    """El portal publicó una fila que alguien ya había cargado a mano, y difieren.

    El caso lleva **los dos valores**, porque la pregunta no se puede contestar
    con uno solo: quien decide tiene que ver qué escribió la persona y qué dijo
    el portal, uno al lado del otro.

    La clave es el registro y no la lectura: el portal puede volver a publicar
    la misma fila muchas veces, y son la misma discusión sobre la misma factura,
    no una discusión nueva por cada lectura (RF-35).
    """
    kind = DISPUTED_INVOICE if event.entity == INVOICE_ENTITY else DISPUTED_ORDER
    await TriageService(session).open_case(
        kind=kind,
        section=BusinessSection.PURCHASING,
        reason=DISPUTED_ENTRY_REASON,
        payload={
            "entity": event.entity,
            "entity_id": event.entity_id,
            "number": event.number,
            "supplier_text": event.supplier_text,
            "typed": dict(event.typed),
            "published": dict(event.published),
            "origin": INVOICE_ORIGIN if event.entity == INVOICE_ENTITY else ORDER_ORIGIN,
        },
        key=f"{event.entity}:{event.entity_id}",
    )
