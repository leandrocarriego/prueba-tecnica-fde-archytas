# Control propio del sistema — Modelo de datos

<!-- ARTEFACTO INTERNO. Detalle de lo que plan.md resume. -->

**Feature:** 003-system-control · **Fecha:** 2026-08-29

Dos tablas nuevas, una tabla existente que cambia de rol, y un catálogo que deliberadamente **no**
es una tabla. Nada de esta feature escribe en `raw` ni en `staging`.

## `operations.audit_entry` — la bitácora

Una fila por cambio manual, de cualquier módulo, sobre cualquier dato. Es la tabla que contesta
*"quién editó qué, cuándo, qué decía antes y por qué"* (H2).

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `entity_type` | `varchar(100)` | Qué clase de dato se tocó: `catalog.product`, `catalog.product_price`. Indexado junto a `entity_id`. |
| `entity_id` | `varchar(100)` | El identificador dentro de su módulo. Texto y no `int` porque no toda entidad futura va a tener clave numérica. |
| `field` | `varchar(100)` NULL | El campo corregido. Nulo cuando el cambio es del registro entero — un alta a mano. |
| `action` | enum `audit_action` | `CREATED`, `UPDATED`, `CORRECTED`, `CORRECTION_REVERTED`. |
| `old_value` | `jsonb` NULL | Lo que decía antes (RF-10). Nulo en un alta. |
| `new_value` | `jsonb` NULL | Lo que dice ahora. Nulo en una anulación que restituye el valor del portal. |
| `reason_code` | `varchar(50)` NULL | El motivo elegido de la lista (RF-11). |
| `reason_detail` | `text` NULL | El detalle escrito, siempre opcional. |
| `actor_user_id` | `int` | Quién lo hizo (RF-09). Sin FK a `users`: `identity` es otro módulo y una FK entre schemas de módulos distintos es acoplamiento de esquema. Se resuelve por proyección al mostrar. |
| `section` | enum `section` | `PURCHASING`, `SALES`, `SYSTEM`. Es lo que permite el filtro de RF-19. |
| `occurred_at` | `timestamptz` | Indexado descendente: el historial se lee de más nuevo a más viejo (RF-13). |

**Índices**: `(entity_type, entity_id)` para RF-15, `(occurred_at DESC)` para RF-13,
`(actor_user_id, occurred_at DESC)` para RF-14, `(section)` para RF-19.

**Inmutabilidad (RF-16, RF-17).** La migración instala **dos** triggers sobre la misma función,
y los dos hacen falta: uno `BEFORE UPDATE OR DELETE ... FOR EACH ROW`, y otro
`BEFORE TRUNCATE ... FOR EACH STATEMENT`, porque **un trigger de fila no se dispara nunca ante un
`TRUNCATE`** — sin el segundo, una sola sentencia borra el historial entero sin una palabra.
Postgres sólo admite triggers a nivel sentencia sobre `TRUNCATE`, así que son dos y no un evento
más del primero.

No es defensa en profundidad decorativa: el requisito dice *"el sistema debe impedir"*, y un
método que el repositorio no expone sólo impide hasta que alguien lo agregue. El repositorio
expone `insert`, `list` y `list_for_entity`, y nada más.

**Sin FK a `users`, a propósito.** `identity` es un módulo y `operations` es otro; una FK sería una
dependencia de esquema entre dos módulos que no se conocen. El nombre de quien hizo el cambio se
resuelve en la capa HTTP, con la misma `dependencies.py` que ya cruza la frontera para autorizar.

## `core.correction` — la corrección, en el módulo dueño del dato

Una fila por campo corregido a mano sobre un dato que vino del portal. Vive en `core` porque la
escribe `catalog`; cuando 004 construya facturas, tendrá **su** tabla con la misma forma, dada por el
mixin de `shared/corrections.py`.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `entity_type` | `varchar(100)` | `catalog.product`, `catalog.product_price`. |
| `entity_id` | `varchar(100)` | |
| `field` | `varchar(100)` | Qué campo se corrigió. `(entity_type, entity_id, field)` es único entre las vigentes. |
| `portal_value` | `jsonb` | **Lo que el portal informó.** No se toca nunca (RF-25). Es lo que se restituye al anular (RF-31). |
| `corrected_value` | `jsonb` | Lo que quedó. |
| `reason_code` | `varchar(50)` | De la lista (RF-11). |
| `reason_detail` | `text` NULL | |
| `corrected_by_user_id` | `int` | |
| `corrected_at` | `timestamptz` | |
| `status` | enum `correction_status` | `ACTIVE`, `CONFLICTED`, `REVERTED`. |
| `conflict_value` | `jsonb` NULL | Lo que el portal informó después y no coincide con `portal_value` (RF-28). |
| `conflict_detected_at` | `timestamptz` NULL | |
| `reverted_by_user_id` | `int` NULL | RF-32. |
| `reverted_at` | `timestamptz` NULL | |

**Índice único parcial** sobre `(entity_type, entity_id, field) WHERE status <> 'REVERTED'`: un dato
tiene a lo sumo una corrección vigente, y las anuladas se conservan porque nada se borra.

**La corrección no se borra al anularla.** Pasa a `REVERTED` con quién y cuándo (RF-32), y el valor
canónico vuelve a `portal_value`. Borrar la fila haría que el historial apuntara a algo inexistente.

## Máquina de estados de una corrección

```
                    corrige una persona
   (sin corrección) ────────────────────► ACTIVE
          ▲                                 │  el portal informa algo
          │                                 │  distinto de portal_value
          │ anula el dueño                  ▼
          └──────────── REVERTED ◄──── CONFLICTED
                            ▲               │
                            └───────────────┘
                              anula el dueño
```

`CONFLICTED` vuelve a `ACTIVE` si una persona corrige otra vez: el conflicto se cierra donde vive el
dato, no en una bandeja aparte. El diagrama cara al cliente es
[`diagrams/estados-dato.mmd`](diagrams/estados-dato.mmd), que describe lo mismo sin nombrar estados
técnicos.

## `operations.parameter` — la tabla existente, con otro rol

No cambia de forma. Cambia de significado: **deja de ser la lista de parámetros y pasa a ser la lista
de valores que el dueño cambió**. Un parámetro que nadie tocó no tiene fila, y su valor sale del
catálogo (RF-04).

Consecuencia sobre lo que ya existe: `list_parameters()` deja de devolver filas y pasa a devolver el
catálogo con los valores vigentes encima; `set_parameters()` valida contra el catálogo antes de
escribir (RF-06) y rechaza una clave desconocida. `get_parameter_value()` cae al valor inicial del
catálogo en lugar de devolver `None` con un warning, que es lo que hoy hace.

## `app/shared/parameters.py` — el catálogo, que no es una tabla

```python
@dataclass(frozen=True, slots=True)
class ParameterSpec:
    key: str
    label: str          # español: lo que el dueño lee
    effect: str         # español: qué cambia si se lo modifica (RF-05)
    kind: ParameterKind # INTEGER | DECIMAL | TIME_OF_DAY
    initial: Any
    minimum: Any | None
    maximum: Any | None
    unit: str | None
    consumed_by: str    # qué funcionalidad lo lee; vacío mientras no exista
```

Congelado, en una tupla, con un test que verifica que las claves son únicas y que cada valor inicial
cae dentro de su propio rango. Está en `shared/` por la misma razón que el catálogo de eventos: es
vocabulario compartido y **ningún módulo es su dueño**. Que sea una lista cerrada es también lo que
impide que una credencial entre como parámetro por API (Artículo VII).

## `app/shared/sections.py` — las secciones del negocio

```python
class Section(enum.StrEnum):
    PURCHASING = "PURCHASING"   # proveedores, facturas, pagos, órdenes, recibos, calendario
    SALES = "SALES"             # ventas, precios, catálogo, rubros
    SYSTEM = "SYSTEM"           # parámetros y operación de la plataforma
```

Sale del mapa de roles del brief. Es vocabulario del negocio y no de `identity`: por eso vive en
`shared/` y no dentro del módulo, y por eso `operations` puede filtrar por sección sin importar
`UserRole`. `identity.dependencies.visible_sections()` es la única traducción entre rol y sección, y
vive donde ya vive la excepción de autorización.

## Migración

Una sola, con: los dos enums nuevos (`audit_action`, `correction_status`, `section`), las dos tablas,
sus índices, y la función y el trigger de inmutabilidad. `AuditEntry` y `Correction` entran a
`app/models.py` en el mismo commit (`DB-01`; `alembic check` corre en CI).

No hay backfill: no existen correcciones previas, y la bitácora arranca vacía a propósito — inventar
filas de un pasado que nadie registró sería exactamente lo contrario de lo que esta feature promete.
