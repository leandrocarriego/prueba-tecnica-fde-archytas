# 007 — Órdenes de compra y avisos · Informe de convergencia

**Feature:** 007-orders-alerts · **Rama:** `feat/004-to-009-remaining-specs` · **Fecha:** 2026-08-31
**Rol:** Lead · **Skill:** `agents/skills/converge.md`

## Veredicto

> **Deriva mayor.** El código y la spec describen **casi** el mismo producto: 58 de los 62
> requisitos firmados están implementados con evidencia, y la H8 entera y RF-38 —que `plan.md`
> anotaba como faltantes— hoy existen y tienen test. Lo que bloquea el gate son **tres requisitos
> parciales** cuya mitad visible no está construida (RF-06, RF-26 y RF-37: el sistema sabe hacerlo,
> la persona no tiene por dónde pedirlo) y **un hueco del Artículo II** en las órdenes que no se
> pueden tipar.

La feature **no pasa** al `Code-Reviewer` hasta resolver H-1 a H-4.

## Qué se verificó

- 62 requisitos de `spec.md`, uno por uno, contra `backend/app/` y `frontend/`.
- Inventario inverso: rutas de `purchases`, `messaging` y `notifications`, páginas `/ordenes`,
  `/mensajes` y `/configuracion`, tasks de beat, modelos y parámetros.
- Las 54 tareas de `tasks.md` marcadas completas, contra el archivo que cada una nombra.
- `plan.md` → *Contexto de traspaso* y *Deriva contra la spec firmada* (D-0 a D-5).
- `bash scripts/diagrams/validate.sh docs/specs/007-orders-alerts/diagrams/` → **9/9 ✓**, y los
  diagramas leídos paso por paso contra el código.
- Las cinco reglas del dominio de `AGENTS.md`.

## Tabla de trazabilidad (resumen por historia)

| Requisitos | Qué prometen | Dónde están | Evidencia | Estado |
|---|---|---|---|---|
| RF-01, RF-21 | Traer órdenes y bandeja con su frecuencia | `operations/service.py::SYNC_JOBS` (`purchase_orders`, `messages` con `message_sync.interval_minutes`), `operations/tasks.py::tick_extractions` | `beat_schedule["extraction-tick"]` | Implementado |
| RF-02 a RF-05, RF-07, RF-49, RF-50 | Listado con proveedor, fecha, monto, estado, antigüedad y conteos | `purchases/service.py::list_orders`, `register_orders` (`status_since`, `observed_from_start`), `frontend/app/(private)/ordenes/page.tsx`, `components/purchases/OrderTable.tsx` | `test_orders_and_messages.py::test_time_in_a_state_is_counted_from_the…`, `::test_the_counts_per_state_are_reported` | Implementado |
| RF-06 | Filtrar por estado **y por proveedor** | API: `GET /purchase-orders?supplier_id=`. Pantalla: sólo estado, estancadas y apartadas | `ordenes/page.tsx:15-26` — no hay control de proveedor | **Parcial** |
| RF-08, RF-55 | Apartar sin adivinar, con su motivo | `service.py::register_orders` (`supplier, reason = await self.resolve_supplier(...)`, `review_reason=reason`) | `::test_an_unidentifiable_supplier_holds_t…` | Implementado |
| RF-09, RF-46 | Ventas no llega a órdenes ni a mensajes | Matriz de la 002: `Section.PURCHASE_ORDERS` / `SUPPLIER_MESSAGES` con `_SALES: NONE` | tests de permisos por comportamiento (403) | Implementado |
| RF-10 a RF-14, RF-48 | Estancamiento, su límite configurable y su reinicio | `service.py::_is_stalled`, `RECEIVED_STATUS`, `status_since = today`, parámetro `purchase_order.stalled_days` | `::test_a_received_order_is_never_stalled`, `::test_an_order_that_advances_restarts_th…` | Implementado |
| RF-15 a RF-20, RF-59, RF-60 | Pedido repetido, su ventana, su descarte y su reevaluación | `repository.py::earlier_order_for` (devuelve `None` sin proveedor → RF-59), `service.py::dismiss_repeat`, `_attach_order` (RF-60) | `::test_a_held_order_is_never_flagged_as_a_repeat_and_is_checked_on_resolution` | Implementado |
| RF-22 a RF-25, RF-27 a RF-29, RF-31, RF-32 | Clasificar, identificar remitente, resolver, contar, anotar | `messaging/service.py::register_messages`, `_kind_of`, `_sender_of`, `resolve`, `annotate` | `::test_it_classifies_by_what_the_portal_w…`, `::test_a_kind_nobody_mapped_is_shown_uncl…` | Implementado |
| RF-26 | Filtrar mensajes por tipo, **proveedor** y estado | API: `GET /messages?supplier_name=`. Pantalla: tipo y estado | `mensajes/page.tsx:15-29` — no hay control de proveedor | **Parcial** |
| RF-30 | Asignar responsable, y Julián no es asignable | `messaging/routes.py::assign_message` (valida contra `who_reaches(SUPPLIER_MESSAGES)`), `GET /messages/assignees`, `components/messaging/MessageList.tsx:127-146` | `::test_it_can_be_assigned_and_annotated` | Implementado |
| RF-33, RF-34, RF-42, RF-43, RF-44, RF-45 | Aviso inmediato en la franja, al número correcto, y sólo a quien tiene acceso | `notifications/handlers.py::warn_about_a_message` + `_deliver` (`countdown`), `delivery.py::delay_until_window`, `phones_for`, `stop_alerting` | `test_alert_routing.py::test_a_saturday_night_claim_waits_until_monday`, `::test_somebody_who_lost_their_access_stops_rec…` | Implementado |
| RF-35, RF-36, RF-40, RF-41 | Resumen diario a la hora configurada, sin resueltos, una vez por día | `notifications/tasks.py::daily_digest` (`DailyDigestRequested` + `DailyDigestContribution`), `_is_the_hour`, `purchases/handlers.py:112-131` | `::test_a_digest_with_nothing_pending_is_still_w…`, `::test_a_resolved_message_is_not_in_the_digest` | Implementado |
| RF-37 | El **dueño define** quién recibe cada tipo de aviso | API: `GET/PUT /alerts/routes` (`notifications/routes.py`), `DEFAULT_ROUTES`. **Ninguna pantalla la llama** | `grep -rn "/alerts" frontend` → sólo `lib/api/types.ts` | **Parcial** |
| RF-38 | Un aviso que no se entrega se registra y se ve | `tasks.py::_report_delivery_failure` → `AlertDeliveryFailed` → `messaging/handlers.py::record_a_failed_alert` → `MessageList.tsx:99` | `::test_the_failure_is_recorded_on_the_message_i…`, `::test_an_alert_with_no_message_behind_it_is_an…` | Implementado |
| RF-39, RF-47 | Un solo aviso por mensaje; la puesta en marcha no despierta a nadie | `register_messages` (`external_id` único + `if not first_run`) | `::test_the_same_message_is_not_registered…`, `::test_the_first_reading_wakes_nobody` | Implementado |
| RF-51 a RF-54, RF-56 a RF-58, RF-61, RF-62 | La H8 entera: contar, filtrar, resolver, registrar quién, y que la decisión alcance a las demás | `service.py::orders_in_review`, `resolve_order`, `_attach_order`, `_apply_alias` (facturas **y** órdenes), `OrderTable.tsx:139-162` | `::test_resolving_it_records_who_and_takes…`, `::test_one_decision_resolves_every_order_…`, `::test_the_next_order_written_that_way_ar…` | Implementado |

**D-0 y D-5 quedaron cerrados**: la H8 y RF-38 existen, con test. **D-3 quedó cerrado**: la ruta de
asignación valida el rol y la pantalla la llama.

## Hallazgos

| # | Tipo | Qué dice el artefacto | Qué hace el código | Rol dueño | Acción |
|---|---|---|---|---|---|
| **H-1** | Requisito sin implementar (parcial) | RF-37: *«el dueño define quién recibe cada tipo de aviso»*, y su criterio dice *«el dueño cambia los destinatarios»* | `GET/PUT /alerts/routes` existen y están probadas; **no hay pantalla**. El dueño sólo puede cambiarlos con una request a mano | `Developer` (frontend) | Agregar el control de destinatarios por tipo de aviso en `/configuracion`, sobre las rutas que ya existen |
| **H-2** | Requisito sin implementar (parcial) | RF-06: filtrar órdenes *«por estado y por proveedor»* | `list_orders` acepta `supplier_id`; `/ordenes` sólo ofrece estado, estancadas y apartadas | `Developer` (frontend) | Agregar el filtro por proveedor a la pantalla de órdenes |
| **H-3** | Requisito sin implementar (parcial) | RF-26: filtrar mensajes *«por tipo, por proveedor y por estado»*, y su criterio pide *«los reclamos pendientes de un proveedor»* | `list_messages` acepta `supplier_name`; `/mensajes` sólo ofrece tipo y estado | `Developer` (frontend) | Agregar el filtro por proveedor a la pantalla de mensajes |
| **H-4** | Contradicción con una regla del dominio | Artículo II: nada se descarta, lo ilegible va a cuarentena **y genera una fila en `operations.exception`**. Es la D-1 de `plan.md`, todavía abierta | `ingestion/service.py:637` publica `PurchaseOrderRowsQuarantined` y **nadie está suscripto**: `triage/handlers.py` suscribe `PriceRowsQuarantined`, `InvoiceRowsQuarantined`, `PriceHistoryRowsQuarantined` — las órdenes no. Una fila de orden que no se puede tipar no se cuenta ni se ve | `Developer` (backend), con el `Backend-Architect` | Suscribir `triage` a `PurchaseOrderRowsQuarantined`, calcado del handler de `InvoiceRowsQuarantined`, con su test |
| **H-5** | Alcance no pedido | D-2 de `plan.md`, todavía abierta | `PurchaseOrdersStalled` está en `shared/events/catalog.py:885` y se exporta en `__init__.py`, y **no se publica ni se consume** en ningún lado. Es vocabulario compartido que no significa nada | `Backend-Architect` | O quitarlo del catálogo, o —si el aviso de estancamiento fuera del resumen es alcance— llevarlo a la spec y firmarlo. Hoy es un evento muerto |

## Observaciones que no son hallazgos

- **D-4 (`RECEIVED_STATUS`) quedó cubierto de costado, y conviene saber cómo.** No hay test que
  compare la constante con el fixture, pero `tests/unit/ingestion/test_section_parsers.py:158-163`
  afirma sobre la captura real que hay exactamente **11 órdenes `"Recibida"`**. Si el portal
  cambiara la grafía, ese test rompe antes de que once órdenes recibidas empiecen a estancarse. La
  dependencia sigue siendo frágil; el aviso temprano existe.
- **`purchase_orders` comparte el parámetro `invoice_sync.interval_hours`.** RF-01 pide *«la
  frecuencia configurada»* y no una propia, así que no es deriva — pero cambiar la de facturas
  cambia también la de órdenes, y eso no está dicho en ninguna pantalla.
- **RF-14 y RF-48 no tienen código propio**: salen de reiniciar `status_since` en
  `register_orders`. Ya está anotado en `plan.md`; se repite acá porque es lo que un refactor
  rompe sin que ningún nombre lo delate.
- **Las cinco reglas del dominio**: sólo lectura del portal ✓ (nada escribe a SIGProv), navegador y
  no cliente HTTP ✓ (`portal/client.py`, sin `httpx` contra secciones), flujo unidireccional ✓,
  credenciales sólo en el entorno ✓. La única que la feature roza es la tercera, y es H-4.

## Las dos salidas (decide el humano, Artículo V)

1. **Implementar lo que falta.** H-1 a H-3 son tres controles de pantalla sobre APIs que ya
   existen y ya están probadas; H-4 es un handler calcado de uno que ya está escrito. Vuelve al
   `Developer` y después otra vez al `Tester`. Es el camino corto y el que deja la spec intacta.
2. **Corregir la spec.** Si se acepta que el filtro por proveedor y la configuración de
   destinatarios se resuelven por API en esta entrega, RF-06, RF-26 y RF-37 hay que reescribirlos
   diciendo eso, y **el cliente vuelve a firmar** con `/approve-spec`. H-4 **no** admite esta
   salida: el Artículo II no se renegocia.

No elijo por el cliente. H-5 se decide igual, en el mismo momento: se quita el evento o se firma
lo que lo justifica.

---

## Cierre — 2026-08-31

**El humano eligió la salida 1: implementar lo que falta.** H-1 a H-4 están construidos y probados;
la spec no se tocó y el gate de la firma no se reabre.

| # | Estado | Dónde quedó |
|---|---|---|
| **H-1** | Cerrada | `components/notifications/AlertRoutes.tsx` en `/configuracion`, con `app/actions/alerts.ts` y `lib/notifications/types.ts`. `RouteWrite` acepta ahora sólo `OWNER` y `PURCHASING` — un control en pantalla sobre un string libre dejaba ofrecer ventas para los reclamos de la bandeja que RF-46 le cierra. `test_rbac.py::test_the_owner_changes_a_route_and_sales_is_not_offerable` |
| **H-2** | Cerrada | Filtro por proveedor en `/ordenes`, un `form` con GET que conserva los demás filtros en campos ocultos |
| **H-3** | Cerrada | Filtro por proveedor en `/mensajes`, más `GET /messages/senders` — el padrón como lo guarda `messaging`, que son los valores exactos que `supplier_name` puede tomar. `::test_the_inbox_can_be_asked_for_one_supplier`, `::test_purchasing_can_read_the_senders_it_filters_by` |
| **H-4** | Cerrada | `triage/handlers.py::open_unreadable_order_rows` → caso `unreadable_order_row`, visible en `/revision` y cerrable dándolo por revisado. `::TestAnOrderRowNobodyCouldInterpret` |
| **H-5** | **Abierta** | Sigue siendo una decisión, no una tarea: se quita `PurchaseOrdersStalled` del catálogo o se firma el aviso que lo justificaría |

**Verificación:** suite completa en verde — **1569 tests, 92,20 % de cobertura** (antes 1530 y
91,11 %) —, `ruff`, `mypy`, `tsc --noEmit`, `eslint`, `prettier --check` y `next build` limpios, y
los 441 tests de arquitectura pasan: ninguna frontera se cruzó para construir esto.

**Un hallazgo nuevo, de otra feature.** Al cerrar H-4 quedó a la vista que `SaleRowsQuarantined`
(009) se publica y **nadie está suscripto**: es el mismo agujero del Artículo II, en la pantalla de
ventas. No se tocó acá porque no es de esta spec — es material del `/converge` de la 009.

Con H-1 a H-4 cerradas, la 007 **converge**, y lo único que separa a la feature del
`Code-Reviewer` es la decisión sobre H-5.

---

## Re-verificación — 2026-08-31 (segunda corrida de `/converge`)

Corrida completa de `agents/skills/converge.md` sobre el estado actual de la rama
`feat/004-to-009-remaining-specs`. **Las cuatro hallazgos que bloqueaban el gate siguen cerradas
en el código**, verificadas de nuevo contra archivo y test, no contra este informe:

| # | Evidencia releída |
|---|---|
| **H-1** | `frontend/components/notifications/AlertRoutes.tsx`, llamada desde `app/(private)/configuracion/page.tsx` vía `app/actions/alerts.ts`. `test_rbac.py::test_the_owner_changes_a_route_and_sales_is_not_offerable` |
| **H-2** | `ordenes/page.tsx:34` (`supplier_id`) y el `<select>` de proveedores en `:96-98`, alimentado por `GET /suppliers` |
| **H-3** | `mensajes/page.tsx:32` (`supplier_name`) y el `<select>` de `:98`, alimentado por `GET /messages/senders`. `::test_the_inbox_can_be_asked_for_one_supplier`, `test_rbac.py::test_purchasing_can_read_the_senders_it_filters_by` |
| **H-4** | `triage/handlers.py:162 ::open_unreadable_order_rows` suscripto a `PurchaseOrderRowsQuarantined`. `test_orders_and_messages.py:592 ::TestAnOrderRowNobodyCouldInterpret` |

`bash scripts/diagrams/validate.sh docs/specs/007-orders-alerts/diagrams/` → **9/9 ✓**.
`tasks.md` no tiene ninguna tarea sin marcar.

**H-5 sigue abierta y sigue siendo la única.** `PurchaseOrdersStalled` aparece sólo en
`shared/events/catalog.py:885` y en `shared/events/__init__.py:58,137`: nadie lo publica y nadie
lo consume.

### Veredicto de esta corrida

> **Deriva menor.** El código y la spec describen el mismo producto: los 62 requisitos firmados
> tienen implementación con evidencia. Lo único que queda es vocabulario compartido que no
> significa nada — un evento del catálogo que ningún requisito pide y ningún código usa. No es
> una capacidad de negocio visible para el usuario, así que **no bloquea el gate**.

La 007 **pasa al `Code-Reviewer`**.

### Cierre de H-5 — 2026-08-31

**El humano eligió quitar el evento.** `PurchaseOrdersStalled` se eliminó de
`shared/events/catalog.py` y de los dos lugares donde `shared/events/__init__.py` lo exportaba.
No había publicador ni suscriptor, así que no hubo cambio de comportamiento y ningún test lo
nombraba. El aviso de estancamiento fuera del resumen diario no es alcance firmado; si alguna vez
lo fuera, el evento vuelve **junto a su publicador**, no antes.

`plan.md` → D-2 y `tasks.md` → *Notas para `/converge`* quedaron actualizados para que no sigan
describiendo un evento que ya no existe.

**Verificación:** `ruff check` y `mypy` limpios sobre `app/shared/events/`, y los tests de
arquitectura en verde.

Con H-5 cerrada, la 007 **converge sin hallazgos abiertos**.
