# Tablero del negocio — Contratos HTTP

<!-- ARTEFACTO INTERNO. Es el detalle largo que `plan.md` referencia. -->

**Feature:** 009-business-dashboard · **Fecha:** 2026-08-31 · **Prefijo:** `/api/v1`

Siete endpoints en dos módulos: cinco de `sales` y dos de tablero, uno servido por `sales` y otro por
`catalog`. Cada uno declara su sección y su nivel (`PY-09`); quién alcanza ese nivel lo decide la
matriz de `identity`.

Los errores siguen la forma única de la plataforma (`ERR-01`): `{"detail": "...", "details": {...}}`,
con el `detail` en español porque lo lee una persona.

---

## Las ventas

`backend/app/modules/sales/routes.py` · `router`, prefijo `/sales`

### `GET /sales`

**`SALES` · `READ`** — dueño y ventas. Compras recibe 403 (RF-08).

| Query | Tipo | Default | Qué hace |
|---|---|---|---|
| `skip` | `int ≥ 0` | `0` | |
| `limit` | `int 1..200` | `50` | |
| `state` | `SaleState?` | — | `COUNTED` \| `HELD` \| `DISCARDED` |
| `since`, `until` | `date?` | — | Contra `sold_on`, inclusive en los dos extremos |

**Respuesta `200` — `SaleList`:** `{ items, total, skip, limit }`, ordenadas por `sold_on` descendente
con los nulos al final.

**`SaleRead`** (`sales/schemas.py:12-30`):

```
id, code, code_key, sold_on?, product_code?, quantity?, total?, state,
reason?, portal_values?, is_estimated, duplicate_of_sale_id?,
resolved_by_user_id?, resolved_at?
```

`portal_values` es un objeto con las cuatro claves tal como las informó el portal —`sold_on`,
`product_code`, `quantity`, `total`, las dos últimas como cadenas— y **no cambia nunca**, se corrija
lo que se corrija. Es RF-02 y es lo que hace verificable cualquier diferencia (RF-41).

> **Ninguna pantalla consume esta ruta.** Es la superficie por la que se verifica el total a mano, que
> es el criterio de aceptación de RF-04. No es código de más; es una pantalla de menos, y ningún
> requisito la pide.

### `GET /sales/review`

**`SALES` · `WRITE`** — dueño y ventas (RF-29).

**Pide `WRITE` y no `READ` a propósito.** La cola de revisión es donde se decide, y quien no puede
decidir no tiene por qué mirar la lista de lo que otro tiene pendiente. Hoy nadie fuera de dueño y
ventas alcanza `WRITE` sobre `SALES`, así que la diferencia no cambia el resultado; cambia lo que la
ruta **declara**.

**Respuesta `200` — `ReviewQueue`:**

```
{
  groups: SaleGroup[],   // las repetidas con diferencias
  broken: SaleRead[],    // las apartadas por sí mismas
  pending_groups: int,   // RF-14
  held: int              // RF-28: todas las HELD, sin ventana
}
```

**`SaleGroup`** lleva `code_key`, `versions` —las dos o más enfrentadas, RF-30— y `differences`, que
son los nombres de los campos en que difieren, tomados de `COMPARED`. Es lo que le permite a la
pantalla **marcar** la diferencia en vez de dejar que una persona compare fila por fila, y es lo que
convierte la decisión en un segundo.

El reparto entre `groups` y `broken` no lo decide un campo: `held_groups()` agrupa las `HELD` por
`code_key`, y un grupo de una sola venta es una rota (`service.py:199-224`). Consecuencia a conocer:
**una venta apartada por monto atípico que además comparta código con otra aparece como grupo, no como
rota**, y la pantalla le ofrece «elegí cuál vale» donde el problema era el monto.

> **`broken` sólo trae lo que llegó a `core.sale`.** Las doce ventas sin fecha, con fecha inexistente,
> sin total o con cantidad negativa **no están acá**: quedaron en `staging.sale_row`. Ver `plan.md` →
> *Lo que falta* y D-1.

### `POST /sales/groups/{code_key}/resolution`

**`SALES` · `WRITE`** — dueño y ventas (RF-29).

```
{ action: "keep" | "distinct", sale_id: int | null }
```

| `action` | Qué hace |
|---|---|
| `keep` | La versión `sale_id` pasa a `COUNTED`; las demás a `DISCARDED` con `duplicate_of_sale_id` apuntándole. **Se siguen viendo** (RF-34) |
| `distinct` | **Todas** pasan a `COUNTED`: nunca fueron la misma venta, y el código que comparten es el error (RF-32) |

Las dos escriben `decision`, `resolved_by_user_id` y `resolved_at` en **todas** las filas del grupo, con
el usuario del token y nunca del cuerpo (RF-36).

| Código | Cuándo |
|---|---|
| `200` | La lista de `SaleRead` del grupo entero, elegidas y descartadas |
| `403` | Compras |
| `404` | `No encontramos esa venta`, con `details.code_key` |
| `422` | Un `action` que no es uno de los dos |

**El código va en la ruta y no el id**, porque lo que se resuelve es el grupo y no una venta: la
decisión es sobre «estas dos son la misma», que es una propiedad del código.

**No hay recálculo.** El total del mes cambia porque las agregaciones filtran por `COUNTED`, así que
RF-33 se cumple por no hacer nada. Si alguna vez aparece un `recalculate()` en este servicio, algo del
diseño se rompió.

> **`keep` con `sale_id` nulo descarta el grupo entero.** No hay validación cruzada entre `action` y
> `sale_id`: ninguna versión coincide con `None`, todas pasan a `DISCARDED`, y el grupo desaparece de
> los indicadores sin que nadie lo elija. La pantalla nunca manda eso; la puerta está abierta igual.

### `DELETE /sales/groups/{code_key}/resolution`

**`SALES` · `WRITE`** — dueño y ventas (RF-35).

Sin cuerpo. Devuelve todas las versiones a `HELD` con `DUPLICATE_WITH_DIFFERENCES`, borra `decision`,
`duplicate_of_sale_id` y los campos de autoría, y con eso los indicadores vuelven a su valor anterior
—otra vez, sin recalcular nada—.

| Código | Cuándo |
|---|---|
| `200` | Las versiones, de vuelta en `HELD` |
| `404` | No hay ventas con ese código |
| `409` | `Esa venta no tiene una resolución que deshacer` |

**El `409` es la distinción que la firma dejó explícita:** lo que el sistema unificó solo, por ser
idéntico, **no tiene una resolución que deshacer**. Sin `decision` no hay nada que revertir, y decirlo
con un `409` es más honesto que devolver `200` sin haber hecho nada.

Es un `DELETE` sobre `/resolution` y no un `POST /undo` porque lo que se borra es la decisión, y el
verbo dice qué desaparece.

### `PATCH /sales/{sale_id}`

**`SALES` · `WRITE`** — dueño y ventas (RF-38, RF-39, RF-41).

```
{ sold_on?: date, product_code?: str(64), quantity?: int, total?: decimal, is_estimated?: bool }
```

Sólo se aplican los campos **no nulos**: mandar `null` no borra un valor, lo deja como estaba. Es una
decisión, y tiene una consecuencia que hay que conocer: **no hay forma de vaciar un campo por esta
ruta**. Ningún requisito lo pide —las correcciones son para completar, no para vaciar— y por eso el
contrato es así.

`is_estimated` es **acumulativo**: `sale.is_estimated or is_estimated`. Una vez que un registro tiene
un valor estimado, no deja de tenerlo por una corrección posterior sobre otro campo. Es lo que hace
que RF-40 —el indicador declara que alguno de sus valores es estimado— no mienta.

Después de aplicar, el servicio decide si el registro ya se puede contar:

| Situación | Resultado |
|---|---|
| Sigue sin fecha o sin total | `422` `La venta sigue sin fecha o sin total` — **y los cambios ya aplicados se pierden**, porque no hay `commit` |
| El producto sigue sin existir | Queda `HELD` con `reason = UNKNOWN_PRODUCT` |
| Todo en orden | Pasa a `COUNTED`, `reason` a nulo, y entra a los indicadores |

| Código | Cuándo |
|---|---|
| `200` | El `SaleRead` corregido |
| `404` | `No encontramos esa venta` |
| `409` | `Esa venta no está apartada` — sólo se corrige lo que está `HELD` |
| `422` | Sigue faltando la fecha o el total |

> **Tres cosas que este contrato promete y hoy no se cumplen** (`plan.md` → D-4, D-5):
>
> - **La pantalla sólo ofrece corregir el código de producto**, con un `window.prompt`. La fecha, el
>   total y la cantidad no se pueden corregir desde ninguna pantalla, aunque el endpoint las acepte.
> - **`is_estimated` nunca se manda en `true`**: la única llamada del frontend lo fija en `false`. Con
>   lo que `has_estimates` no puede ser `true` y RF-40 está cumplido sobre algo que no puede ocurrir.
> - **Esta corrección no pasa por el mecanismo común de la 003**: no publica `ManualChangeRecorded`, no
>   aparece en `/historial` y **no se puede dejar sin efecto**, a diferencia de las correcciones de
>   `catalog` y `purchases`. La spec firmada lo declara en «Para confirmar al firmar».

---

## El tablero

Dos endpoints, en dos módulos distintos, **y ésa es la decisión**: cada corte elige su período por
separado (RF-05) y cada dominio sirve lo suyo (Artículo IV). El frontend compone.

### `GET /dashboard/sales`

`sales/routes.py` · `dashboard_router` · **`DASHBOARD` · `READ`** — dueño y ventas (RF-08).

| Query | Tipo | Default |
|---|---|---|
| `since`, `until` | `date?` | — (todo el histórico) |

**Respuesta `200` — `SalesDashboard`:**

```
{
  since?, until?,
  invoiced: Indicator,     // RF-07: el primer contenido del tablero
  by_month: MonthTotal[],  // RF-03
  held_total: int,         // RF-28, SIN ventana
  pending_groups: int      // RF-14
}
```

**`Indicator`** lleva `value`, `sales`, `excluded` y `has_estimates` **juntos, en un solo tipo**. No
es una comodidad: es lo que hace que **no se pueda devolver un número sin su exclusión**. Quien agregue
un indicador nuevo tiene que llenar los cuatro campos, y RF-25 y RF-27 pasan de ser una regla que
alguien recuerda a ser una firma de tipos.

`excluded` es `HELD + DISCARDED` dentro de la ventana. Dos advertencias:

- **Mezcla lo que el sistema unificó solo con lo que una persona descartó** (D-3), así que RF-12
  —cuántas unificó— no se puede leer de acá.
- **No cuenta las doce que quedaron en `staging`** (D-1), así que el número está por debajo de la
  verdad.

`held_total` y `pending_groups` **no respetan la ventana**: son el estado de la cola entera, que es lo
que RF-28 pide y lo que la pantalla usa para el enlace a la revisión.

### `GET /dashboard/catalog`

`catalog/routes.py:246-263` · `catalog_dashboard_router` · **`DASHBOARD` · `READ`** — dueño y ventas.

| Query | Tipo | Default |
|---|---|---|
| `since`, `until` | `date?` | — |

**Respuesta `200` — `CatalogDashboard`:**

```
{
  since?, until?,
  price_curve: PriceCurvePoint[],   // RF-42: mes, promedio, cuántos cambios
  price_curve_excluded: int,
  stock: StockCut[],                // RF-43: producto, apertura, cierre, ran_out
  stock_excluded: int,              // RF-46
  new_products: NewProductRead[]    // RF-45
}
```

- **`price_curve`** promedia los puntos del historial de precios por mes, que es lo que el proveedor
  informó de verdad. Una curva armada con el precio vigente hoy redibujaría el pasado cada vez que un
  precio cambia.
- **`stock`** compara la foto más cercana a `since` con la más cercana a `until`. `ran_out` es
  `closing == 0` y es RF-44. **Sin `since` no hay apertura y el corte sale vacío**, con todos los
  productos en `stock_excluded`.
- **`stock_excluded`** son los productos sin foto en alguno de los dos extremos. No se cuentan como
  cero, porque decir cero sería inventar un stock.

> **Dos incumplimientos de RF-46** (`plan.md` → D-6): `price_curve_excluded` está **fijo en `0`**, no
> calculado —dice «cero excluidos» sin haber contado—, y el corte de **altas no tiene `excluded`** ni
> en el schema ni en la pantalla.

---

## Lo que ninguna ruta expone, a propósito

- **La tolerancia de monto atípico y el intervalo de lectura** se ajustan en el panel de parámetros de
  la 003, no acá. Es la regla de negocio de la spec: *«no hay valores escondidos en el tablero ni en
  la pantalla de revisión»*.
- **Reprocesar el histórico con una tolerancia nueva.** La spec dice explícitamente que mover el
  número no reevalúa lo ya cargado, y una ruta que lo hiciera sería alcance que nadie firmó.
- **Exportar el tablero.** Declarado fuera de alcance: no se pidió.
- **Escribir cualquier cosa en el portal.** Artículo I. La corrección vive de este lado.
