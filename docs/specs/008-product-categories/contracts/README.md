# Rubros unificados — Contratos

<!-- ARTEFACTO INTERNO. El detalle que plan.md resume en dos tablas. -->

**Feature:** 008-product-categories · **Fecha:** 2026-08-31

Dos contratos, de naturaleza distinta:

- **[El contrato HTTP](#el-contrato-http)** — lo que el frontend le pide al backend. Los tipos del
  frontend se generan desde el schema de OpenAPI (`make frontend-api-types`, `TS-05`), así que la
  **fuente de verdad** es `backend/app/modules/catalog/routes.py` + `schemas.py` y
  `backend/app/modules/triage/routes.py` + `schemas.py`. Este documento dice lo que el schema no
  puede decir: quién puede llamar cada ruta, qué RF cubre y por qué un error es el que es.
- **[El contrato de eventos](#el-contrato-de-eventos)** — lo que un módulo le cuenta a otro sin
  importarlo (Artículo IV). La fuente de verdad es `backend/app/shared/events/catalog.py`.

Prefijo de todas las rutas: `/api/v1`. **Ninguna es pública**: ninguna figura en `PUBLIC_ROUTES` de
`backend/tests/architecture/test_route_authorization.py`.

> **Este documento describe lo construido**, no lo planificado. Donde el código no hace lo que la
> spec firmada pide, está marcado y remite a `plan.md` → *Deriva contra la spec firmada*.

---

## El contrato HTTP

### Cómo se declara la autorización

Cada ruta declara su dependencia con `Depends(get_current_user)` —cualquier sesión válida— o con
`require_section(Section.X, Level.Y)`, las dos importadas de `app.modules.identity.dependencies`, el
**único** import que cruza una frontera de módulo. `Level` está ordenado, así que quien tiene
`WRITE` también lee.

Dos secciones gobiernan esta feature, y **no se solapan**
(`backend/app/modules/identity/permissions.py:75,86`):

| Sección | `OWNER` | `PURCHASING` | `SALES` |
|---|---|---|---|
| `PRODUCT_CATEGORIES` | `WRITE` | `NONE` | `WRITE` |
| `PRICES` | `WRITE` | `WRITE` | `READ` |

Que sean casi disjuntas es lo que produce la deriva nº 1 del plan: las escrituras de `/categories`
son de ventas y las de `/triage/rules` son de compras, y la spec firmada le pide las dos a ventas.

**No existe un `require_sales()`.** La autorización vive en la matriz de `permissions.py`, que un
test recorre entera (`backend/tests/unit/identity/test_permissions.py:34`).

### El sobre de error

Todos los errores salen con la misma forma (`backend/app/main.py:140-150`):

```json
{ "error": { "type": "ConflictError", "message": "…", "details": { } } }
```

Los servicios lanzan errores de dominio de `app/shared/errors.py` y **nunca** `HTTPException`
(`ERR-04`); `app/main.py:74-80` los traduce:

| Error de dominio | HTTP | Cuándo, en esta feature |
|---|---|---|
| `NotFoundError` | `404` | No existe el rubro (`No encontramos ese rubro`) o el producto |
| `ConflictError` | `409` | Ya hay un rubro con ese nombre (RF-05, RF-06) · el rubro tiene productos y no se borra (RF-07) · el rubro todavía tiene formas escritas asignadas · la regla ya está revocada (`PATCH` y `DELETE` de `/triage/rules`) |
| — | `403` | La sesión no llega al nivel que la ruta pide. Mensaje en español: `No tenés permiso para esta sección` |
| — | `401` | Sin token, o token vencido |

### Rutas de `catalog`

Fuente: `backend/app/modules/catalog/routes.py:151-243`.

#### `GET /categories`

- **Autorización:** `Depends(get_current_user)` — los tres roles.
- **Cubre:** RF-01, RF-03, RF-04, RF-09, RF-10, RF-11.
- **Respuesta** `200` — `CategoryList`:

```jsonc
{
  "items": [
    {
      "id": 3,
      "name": "Pinturas y Adhesivos",
      "product_count": 18,
      "aliases": [
        {
          "id": 7,
          "category_id": 3,
          "text_original": "PINTURAS Y ADHESIVOS",
          "text_normalized": "pinturas y adhesivos",
          "rule_id": 7,
          "source": "SEED",
          "created_at": "2026-08-30T19:12:00Z"
        }
      ]
    }
  ],
  "unclassified_count": 8,   // «sin rubro»: NO es una fila de core.category (RF-09)
  "total_products": 100      // items[].product_count + unclassified_count (RF-10)
}
```

`unclassified_count` y `total_products` cuentan **sólo productos `ACTIVE`**
(`catalog/repository.py:300`). Los rubros vienen ordenados por nombre.

#### `GET /categories/unclassified`

- **Autorización:** `Depends(get_current_user)` — los tres roles.
- **Cubre:** RF-11, RF-12, RF-14, RF-15, RF-17.
- **Query:** `skip` (≥0, default 0) · `limit` (1..500, default 100).
- **Respuesta** `200` — `UnclassifiedList`:

```jsonc
{
  "items": [
    {
      "product_id": 41,
      "code": "TOR-0012",
      "description": "Tornillo autoperforante 8x1",
      "category_raw": null,              // llegó sin categoría
      "subcategory_raw": "Tornillos",    // RF-08
      "proposed_category_id": 2,         // RF-14: se calcula al salir, NO se guarda (RF-16)
      "proposed_category_name": "Ferretería General"
    }
  ],
  "total": 8, "skip": 0, "limit": 100
}
```

La propuesta sale de qué rubro tienen los productos ya clasificados con esa misma subcategoría. Si
la subcategoría resuelve a **cero o a más de un** rubro, los dos campos vienen en `null`: es RF-17,
y desempatar sería el sistema decidiendo (`catalog/service.py:799-800`).

#### `GET /categories/aliases`

- **Autorización:** `Depends(get_current_user)` — los tres roles.
- **Cubre:** RF-27, parcialmente.
- **Respuesta** `200` — `list[CategoryAliasRead]`, ordenadas por `id`.

**Quién decidió cada equivalencia no está en esta respuesta**: vive en la regla de `triage`, y la
pantalla las une por `rule_id` pidiendo además `GET /triage/rules?kind=unknown_category`. Para
ventas esa segunda llamada devuelve `403`, así que RF-27 se degrada — deriva nº 3 del plan.

#### `POST /categories`

- **Autorización:** `require_section(PRODUCT_CATEGORIES, WRITE)` — dueño y ventas.
- **Cubre:** RF-05.
- **Cuerpo** — `CategoryWrite`: `{ "name": "Griferías" }` (1..100 caracteres).
- **Respuesta** `201` — `CategoryRead` con `product_count: 0` y `aliases: []`.
- **`409`** si ya existe un rubro con ese nombre. La comparación es **case-insensitive** en el
  servicio, aunque el índice único de la base sea exacto (`catalog/repository.py:270-280`).

#### `PATCH /categories/{category_id}`

- **Autorización:** `require_section(PRODUCT_CATEGORIES, WRITE)` — dueño y ventas.
- **Cubre:** RF-06.
- **Cuerpo** — `CategoryWrite`. **Respuesta** `200` — `CategoryRead` con su conteo y sus formas.
- **`404`** si no existe · **`409`** si el nombre nuevo ya es de otro rubro.
- Publica `ManualChangeRecorded` con `entity_type="catalog.product_category"`, `field="name"`, el
  nombre viejo y el nuevo: el cambio queda en el log único de la plataforma sin que `catalog` sepa
  que ese log existe.

#### `DELETE /categories/{category_id}`

- **Autorización:** `require_section(PRODUCT_CATEGORIES, WRITE)` — dueño y ventas.
- **Cubre:** RF-07. **Respuesta** `204`.
- **`409`** con el motivo si el rubro tiene productos:
  `{"message": "El rubro tiene productos asignados y por eso no se puede eliminar", "details": {"category_id": 3, "products": 18}}`.
- **`409` también si tiene formas escritas asignadas** — mensaje distinto, `details.aliases`. RF-07
  sólo habla de productos: es la deriva nº 8 del plan.
- El chequeo vive en el servicio y no en un `ON DELETE`: el sistema tiene que poder **decir por
  qué**. La FK igual es `RESTRICT`, como red.

#### `PUT /products/{product_id}/category`

- **Autorización:** `require_section(PRODUCT_CATEGORIES, WRITE)` — dueño y ventas.
- **Cubre:** RF-13, RF-15, RF-18, RF-19, RF-20.
- **Cuerpo** — `ProductCategoryWrite`: `{ "category_id": 2 }`.
- **Respuesta** `200` — `UnclassifiedProduct` con `proposed_category_id` ya apuntando al rubro
  elegido. **`404`** si no existe el producto o el rubro.
- **Confirmar la propuesta y corregirla son esta misma llamada**: la única diferencia es qué
  `category_id` viaja, y el sistema no tiene por qué distinguirlas (RF-15).
- Escribe `classified_by_user_id` y `classified_at` desde el **token**, nunca desde el cuerpo
  (RF-18), y pone `classified_by_rule_id` en `null`: una decisión a mano no depende de ninguna
  equivalencia y una revocación no la puede arrastrar.
- Publica `ManualChangeRecorded` con `entity_type="catalog.product"`, `field="category_id"`.

### Rutas de `triage` que esta feature usa

Fuente: `backend/app/modules/triage/routes.py:48-137`. **Las cinco piden
`require_section(PRICES, WRITE)` — dueño y compras. Ventas recibe `403`** (deriva nº 1).

| Método y ruta | Cubre | Qué hace |
|---|---|---|
| `GET /triage/cases?kind=unknown_category` | RF-21, RF-23, RF-26 | La cola. `payload` de un caso de rubro: `{"category_text", "product_codes", "products"}`. `occurrences` dice cuántas veces volvió |
| `POST /triage/cases/{case_id}/resolution` | RF-24, RF-25 | Cuerpo `{"decision": {"category_id": 2}, "remember": true}`. Crea la regla, publica `QuarantineCaseResolved` y `catalog` proyecta la equivalencia y la aplica retroactivamente. **`409`** si el caso ya estaba resuelto |
| `GET /triage/rules?kind=unknown_category` | RF-27 | Cada equivalencia con `created_by_name`, `created_at`, `updated_by_user_id`, `updated_at`. Las sembradas dicen `"Sembrado en la puesta en marcha"` y `created_by_user_id: null` |
| `PATCH /triage/rules/{rule_id}` *(nueva en 008)* | RF-28, RF-29 | Cuerpo `{"decision": {"category_id": 5}}`. La regla **queda vigente**, gana `updated_by_user_id`/`updated_at`, y `catalog` reapunta el alias y **reasigna** sus productos. **Nadie vuelve a la cola.** `404` si no existe · `409` si ya está revocada |
| `DELETE /triage/rules/{rule_id}` *(ya existía)* | RF-30, RF-31 | `204`. La regla se revoca —nunca se borra—, sus casos se reabren, el alias se baja de la proyección y sus productos **vuelven** a «sin rubro» y a la cola de revisión. `409` si ya estaba revocada |

**La diferencia entre las dos últimas es toda la H5** y es lo más fácil de confundir al
implementar: corregir reasigna, revocar devuelve a la cola. En los dos casos el alcance es
`WHERE classified_by_rule_id = :rule_id`, así que un producto que clasificó una persona a mano no se
mueve.

`remember: false` en la resolución es la puerta trasera del invariante: crea la equivalencia **sin
regla**, y entonces ni el `PATCH` ni el `DELETE` la alcanzan. La pantalla nunca manda ese flag; ver
deriva nº 10 del plan.

---

## El contrato de eventos

Fuente: `backend/app/shared/events/catalog.py`. Todos son `@dataclass(frozen=True, slots=True)`, van
en pasado y llevan identificadores y valores planos — nunca un modelo de SQLAlchemy (`GEN-08`). Los
handlers corren en la sesión y la transacción de quien publicó, y si uno falla, la aborta
(`GEN-09`).

### `PriceListNormalized` *(modificado por 008)*

`ingestion` → `catalog.apply_batch`. Cada `NormalizedPriceRow` suma dos campos **con default**, para
no romper a quien ya construía el evento en `001`:

```python
category_raw: str | None = None      # exactamente como lo escribió el proveedor
subcategory_raw: str | None = None   # RF-08: se guarda y se muestra, no se agrupa por ella
```

### `UnknownCategoryObserved` *(nuevo)*

`catalog` → `triage.open_unknown_categories`. Es lo que abre el caso (RF-21, RF-22, RF-26) y también
lo que devuelve productos a la cola al revocar una equivalencia (RF-31): **un solo camino, no una
rama de revocación**.

```python
batch_id: int
cases: tuple[UnknownCategory, ...]   # UnknownCategory(category_text: str, product_codes: tuple[str, ...])
```

Una entrada **por forma escrita**, no por producto: cien filas del mismo lote escritas igual son una
sola pregunta. `batch_id` viaja en `0` cuando el evento sale de una revocación y no de un lote.

### `QuarantineCaseResolved` *(existente, con un `kind` nuevo)*

`triage` → `catalog.apply_decision`. Con `kind="unknown_category"`:

- `decision = {"category_id": N}`
- `matcher = {"kind": "unknown_category", "category_text": "Pinturas/Adhesivos"}` — **el matcher sale
  por el texto, nunca por el producto que lo trajo.** Si saliera por `product_code`, la equivalencia
  se aplicaría a una fila y las otras noventa y nueve quedarían en la cola, y RF-25 fallaría en
  silencio (`triage/service.py:271-274`).
- `rule_id` puede ser `null` si se resolvió con `remember: false`.

### `QuarantineRuleRevoked` *(existente)*

`triage` → `catalog.undo_rule`. Con `kind="unknown_category"`, `catalog` baja el alias, desasigna sus
productos y republica `UnknownCategoryObserved`.

### `QuarantineRuleRedecided` *(nuevo)*

`triage` → `catalog.repoint_rule`. Es la mitad de H5 que **no** es una revocación:

```python
rule_id: int
kind: str
matcher: dict[str, Any]
decision: dict[str, Any]           # la nueva
previous_decision: dict[str, Any]  # la que había
decided_by_user_id: int
```

### `ManualChangeRecorded` *(existente, reutilizado)*

`catalog` → `operations` (el log único de la plataforma, de 003). Dos entidades:

| `entity_type` | Cuándo | `field` |
|---|---|---|
| `catalog.product_category` | Se agrega, renombra o borra un rubro | `name` |
| `catalog.product` | Alguien le da o le cambia el rubro a un producto | `category_id` |

Siempre con `section = BusinessSection.SALES`, `actor_user_id` del token, `old_value` y `new_value`.
Es lo que hace verdadero RF-18 sin que `catalog` aprenda que existe un log.

### Lo que **no** se publica

`catalog` no anuncia «producto clasificado» como evento propio: hoy nadie lo escucharía. Publicar
sin consumidor es vocabulario compartido que nadie usa; cuando P3 lo necesite, lo agrega su plan.
