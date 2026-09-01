# Calendario de vencimientos — Modelo de datos

<!--
  ARTEFACTO INTERNO. Es el detalle largo que `plan.md` referencia.
  Todo lo de acá está verificado contra el código: cada tabla dice en qué
  archivo y en qué línea vive su modelo, y en qué migración su DDL.
-->

**Feature:** 006-due-date-calendar · **Fecha:** 2026-08-31

Dos tablas nuevas en `core` y dos columnas de `core.invoice` que esta feature lee y escribe. **No
hay migración propia de la 006**: su DDL viaja en `backend/alembic/versions/0011_invoices_and_suppliers.py`,
la migración única que 004, 005, 006 y 007 comparten porque las cuatro se construyeron en la misma
pasada.

## `core.due_date` — una entrada del calendario

Modelo: `backend/app/modules/purchases/models.py:423-466` · DDL:
`backend/alembic/versions/0011_invoices_and_suppliers.py:562-595`

Es **una fila y no una columna de la factura**, y esa es la decisión de diseño de la feature: un
vencimiento se mueve, y moverlo tiene que conservar de dónde venía. Además, un vencimiento cargado
a mano (RF-12) no tiene factura donde vivir.

| Columna | Tipo | Nulo | Por qué está |
|---|---|---|---|
| `id` | `integer` PK | no | |
| `on_date` | `date` | no | La fecha vigente: la que ubica la entrada en el calendario (RF-01) |
| `description` | `varchar(300)` | no | Lo que se lee en la tarjeta (RF-02). Para una factura la arma `_sync_due_date` como `Factura {número} — {proveedor tal como lo escribió el portal}` |
| `amount` | `numeric(14,4)` | sí | El monto (RF-02). Nulo se admite: un vencimiento cargado a mano puede no tenerlo todavía |
| `invoice_id` | `integer` FK → `core.invoice.id` `ON DELETE CASCADE` | sí | Nulo en los cargados a mano. Es lo que permite llegar a la factura desde el calendario (RF-07) |
| `origin` | `core.due_date_origin` | no, `DEFAULT 'MANUAL'` | `INVOICE` o `MANUAL`: la distinción de RF-14, y la que decide si se puede borrar (RF-18) |
| `original_date` | `date` | no | Dónde estaba antes de la primera reprogramación. **Nunca se reescribe** una vez que alguien movió la entrada (RF-20) |
| `created_by_user_id` | `integer` | sí | Quién la cargó (RF-13). Nulo en las que puso una factura, porque no las puso nadie |
| `created_at` | `timestamptz` `DEFAULT now()` | no | Cuándo se cargó (RF-13) |

**Índices**

| Índice | Qué es | Por qué |
|---|---|---|
| `ix_due_date_on_date` | `(on_date)` | La consulta del calendario es siempre una ventana de fechas |
| `uq_due_date_invoice` | único **parcial** sobre `(invoice_id)` `WHERE invoice_id IS NOT NULL` | Una factura tiene **una** entrada en el calendario. Parcial porque los cargados a mano tienen `invoice_id` nulo y no son duplicados entre sí |

**Campo derivado, no columna**

`DueDate.was_rescheduled` es una `@property` de Python (`models.py:460-463`): `on_date != original_date`.
Es lo que RF-24 señala en el calendario, y es también lo que hace que la próxima lectura del portal
**no pise** una fecha que una persona movió (`service.py:1547-1549`).

## `core.due_date_change` — un movimiento de una entrada

Modelo: `backend/app/modules/purchases/models.py:469-492` · DDL:
`backend/alembic/versions/0011_invoices_and_suppliers.py:715-740`

Una fila por movimiento, en orden. Es lo que contesta RF-23 —la fecha original, todas las
reprogramaciones y los motivos escritos— y lo que resuelve RF-34 sin necesidad de bloqueos: si dos
personas mueven la misma entrada, la última gana en `due_date.on_date` y las dos quedan acá.

| Columna | Tipo | Nulo | Por qué está |
|---|---|---|---|
| `id` | `integer` PK | no | |
| `due_date_id` | `integer` FK → `core.due_date.id` `ON DELETE CASCADE`, indexado | no | De qué entrada es este movimiento |
| `previous_date` | `date` | no | De dónde venía |
| `new_date` | `date` | no | A dónde fue |
| `reason` | `text` | sí | **Ofrecido, nunca exigido** (RF-22). Nulo es un movimiento sin motivo escrito, y es válido |
| `actor_user_id` | `integer` | no | Quién lo movió (RF-21). No nulo: mover es siempre un acto de una persona |
| `changed_at` | `timestamptz` `DEFAULT now()` | no | Cuándo (RF-21). Es el orden en que se lee el historial (`repository.py:578-586`) |

## `core.due_date_origin` — el enum

Migración: `0011_invoices_and_suppliers.py:55` (declarado en `NEW_TYPES`) y `:571`.

`INVOICE` · `MANUAL`. Se crea y se dropea con la 0011; una tabla que se va no se lleva su enum, por
eso la migración los dropea por nombre.

## Las dos columnas de `core.invoice` que esta feature toca

Modelo: `backend/app/modules/purchases/models.py:224-229`. **Ninguna de las dos es de la 006**: las
crea la 004/005 y esta feature las lee, y a una la escribe.

| Columna | Quién la escribe acá | La regla |
|---|---|---|
| `due_on` | `move_due_date` la reescribe **sólo si la factura todavía no venció** (`service.py:1681-1683`) | Es lo que hace que el plazo del recibo (RF-26) y la medición del atraso (RF-27) se muevan con la fecha nueva. Y es lo que hace que **no** se muevan cuando ya venció: si `due_on` no cambia, `issue_receipt` sigue rechazando (RF-28, `service.py:1358-1362`), `_average_delay` sigue midiendo contra la original (RF-29, `service.py:1088-1105`) y `is_overdue_without_receipt` sigue en `True` (RF-30, `service.py:802-804`) |
| `original_due_on` | Nadie, en esta feature | Se fija al registrar la factura (`service.py:580`) o cuando aparece el plazo del proveedor (`service.py:1006-1009`), y el calendario no la toca nunca. **No es la fuente de RF-29**: RF-29 funciona porque `due_on` se queda quieto, no porque exista esta columna |

## Lo que el calendario calcula y no guarda

`PurchasesService.calendar()` (`service.py:1554-1595`) devuelve un `DueDateRead`
(`schemas.py:280-298`) donde siete campos **no** salen de una columna:

| Campo | De dónde sale | RF |
|---|---|---|
| `was_rescheduled` | la property del modelo | RF-24 |
| `is_past` | `entry.on_date < today_here()` | RF-06 |
| `supplier_name` | el padrón, por `invoice.supplier_id` | RF-02 |
| `receipt_issued` | `_read_invoices` → los recibos vigentes | RF-09 |
| `is_overdue_without_receipt` | `_read_invoices` → `due_on < hoy and not receipt_issued` | RF-11, RF-30 |
| `payment_state` | `_read_invoices` → los pagos imputados | RF-39 |
| `changes` | `repository.changes_of(...)`, y **sólo si la entrada fue reprogramada** | RF-23 |

Los dos filtros (RF-10 `without_receipt`, RF-40 `hide_settled`) se aplican **sobre esos campos
calculados**, después de armarlos, no sobre una columna guardada (`service.py:1591-1594`).

> **La trampa está en el cruce.** Los cuatro campos que vienen de la factura se buscan en un
> diccionario armado con `due_between(since, until)`, o sea las facturas cuyo `invoice.due_on` cae
> en la ventana — no las facturas de las entradas que se van a mostrar. Cuando la entrada se movió
> pero `due_on` se quedó (el caso de la factura vencida, RF-28 a RF-30), los dos pueden caer en
> ventanas distintas y los cuatro campos vuelven en su valor por defecto. Está anotado como deriva
> en `plan.md`.

## El reloj

Todas las comparaciones con "hoy" pasan por `today_here()` (`service.py:188-196`), que es **America/Argentina/Buenos_Aires y no UTC**: un vencimiento es un día que alguien lee parado en el negocio, y tres horas del día equivocado en cada punta son exactamente la diferencia entre vencer hoy y estar vencida.
