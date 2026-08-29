# Rubros unificados — Modelo de datos

**Feature:** 008-product-categories · **Fecha:** 2026-08-29 · Detalle de `plan.md` → *Datos*.

Todo vive en el esquema `core`, salvo la regla de `triage`, que sigue en `operations` y no se
toca. Migración: `0003_product_categories`, sobre la cabeza `0002`.

## `core.category` — el rubro

| Campo | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `name` | `str(100)` único | Lo que el dueño lee en sus informes. Único: dos rubros con el mismo nombre son un error de carga, no un caso de negocio |
| `created_at` | `timestamptz` | |

RF-07 —no borrar un rubro con productos— **no** se resuelve con `ON DELETE RESTRICT`. La FK
igual va como `RESTRICT` de red de seguridad, pero la verificación vive en el servicio, porque el
sistema tiene que **decir por qué** no se puede, y un error de integridad de Postgres no es un
mensaje para una persona.

## `core.category_alias` — la equivalencia

Proyección local de las reglas de `triage`, más las 18 formas sembradas.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `category_id` | `int` FK → `core.category.id` | A qué rubro apunta |
| `text_normalized` | `str(200)` único | La clave de matcheo |
| `text_original` | `str(200)` | La forma tal como llegó. Es lo que muestran RF-03 y RF-23 |
| `rule_id` | `int` | La regla de `triage` de la que salió. **Siempre presente**: las sembradas también tienen su regla, para que no existan dos clases de equivalencia |
| `source` | `SEED` \| `LEARNED` | De dónde vino |
| `created_at` | `timestamptz` | |

**La normalización es deliberadamente tonta**: `strip()`, colapsar espacios internos, `casefold()`.
Nada más. No quita acentos, no expande `/` a ` y `, no corta abreviaturas. Sólo colapsa los pares
que difieren en mayúsculas —`ELECTRICIDAD` y `Electricidad` son la misma clave—; `Ferreteria Gral.`
y `Ferreteria General` son **dos filas distintas apuntando al mismo rubro**, que es exactamente lo
que la tabla de equivalencias es y por qué se siembra explícita.

Las 18 formas de la spec producen 18 filas y 7 rubros. Que dos filas compartan `category_id` es lo
normal, no una anomalía.

## `core.product` — lo que se le suma

| Campo | Tipo | Notas |
|---|---|---|
| `category_id` | `int` nulo FK → `core.category.id` | **Nulo es «sin rubro»** |
| `category_raw` | `str(200)` nulo | Lo que dijo el proveedor, sin interpretar |
| `subcategory_raw` | `str(200)` nulo | RF-08: se guarda y se muestra, no se agrupa por ella |
| `classified_by_user_id` | `int` nulo | RF-18 |
| `classified_at` | `timestamptz` nulo | RF-18 |
| `classified_by_rule_id` | `int` nulo | Qué equivalencia lo clasificó. Precedente: `registered_by_rule_id` |

`classified_by_rule_id` es lo que hace posible RF-31: al revocarse una regla, se desasigna
**exactamente** lo que esa regla había clasificado, sin tocar lo que decidió una persona a mano.
Un producto clasificado a mano tiene `classified_by_user_id` y `classified_by_rule_id` nulo, y una
revocación no lo alcanza.

Índice en `(category_id)` para el conteo por rubro de RF-04, y parcial sobre
`category_id IS NULL` para la cola de sin clasificar de RF-11 y RF-12.

## Cómo se clasifica un lote

1. Llega `PriceListNormalized`, ahora con `category_raw` y `subcategory_raw` por fila.
2. Se normaliza `category_raw` y se busca en `category_alias`.
3. **Hay equivalencia** → `category_id` de esa equivalencia, `classified_by_rule_id` con su
   `rule_id`. RF-02, RF-25.
4. **No hay equivalencia y `category_raw` no es nulo** → el producto queda con `category_id` nulo
   y se abre un caso `unknown_category` en `triage`, con `fingerprint` por texto normalizado: cien
   productos con la misma forma desconocida abren **un** caso. RF-21, RF-22, RF-23, RF-26.
5. **`category_raw` es nulo** → queda «sin rubro» y entra en la cola de sin clasificar. RF-09 a
   RF-12.

## La propuesta por subcategoría

No hay tabla. Para un producto sin rubro con `subcategory_raw = S`:

```
SELECT category_id FROM core.product
WHERE subcategory_raw = S AND category_id IS NOT NULL
GROUP BY category_id
```

- **Exactamente un `category_id`** → esa es la propuesta. RF-14.
- **Cero, o más de uno** → sin propuesta. RF-17.

El "más de uno" cae en RF-17 a propósito: la spec dice "subcategoría **conocida**", y una
subcategoría que apunta a dos rubros no lo es. Desempatar por mayoría sería el sistema decidiendo,
que es lo que la feature no hace. Sobre el fixture medido las 10 subcategorías resuelven a un solo
rubro, así que hoy las 8 salen con propuesta; la rama de RF-17 igual se implementa y se testea,
porque el catálogo cambia.

## Estados

Los de `spec.md` → `diagrams/estados-producto.mmd`, en términos de estas columnas:

| Estado de la spec | Cómo se lee acá |
|---|---|
| En un rubro | `category_id IS NOT NULL` |
| Sin rubro | `category_id IS NULL` y no hay caso pendiente |
| Apartado para revisión | `category_id IS NULL` y hay un caso `unknown_category` pendiente |

La equivalencia no tiene columna de estado: vigente es existir en `category_alias`. Revocada la
regla, la fila se borra de la proyección y el registro auditable queda en
`operations.resolution_rule`, con su `revoked_at` y quién la revocó.

## Lo que cambia en `operations.resolution_rule`

Dos cambios chicos, los dos por RF-28:

| Campo | Cambio | Por qué |
|---|---|---|
| `created_by_user_id` | pasa a nulo | Una equivalencia **sembrada no la decidió nadie**: vino del acuerdo firmado. Atribuírsela al dueño sería mentir en un registro de auditoría |
| `updated_by_user_id`, `updated_at` | nuevos, nulos | Quién corrigió la equivalencia y cuándo. Es lo que permite reapuntarla **sin** perder quién la creó, y por eso reapuntar no contradice el "se revoca, nunca se borra" |

## Corregir y revocar, lado a lado

| | Corregir — RF-28, RF-29 | Revocar — RF-30, RF-31 |
|---|---|---|
| Ruta | `PATCH /triage/rules/{rule_id}` *(nueva)* | `DELETE /triage/rules/{rule_id}` *(ya existe)* |
| La regla queda | Vigente, con `decision` nueva | Revocada, con `revoked_at` |
| El alias queda | Reapuntado al rubro nuevo | Borrado de la proyección |
| Los productos | **Se reasignan** al rubro nuevo | Se desasignan y **vuelven a revisión** |
| Los casos de `triage` | No se tocan | Se reabren, vía `UnknownCategoryObserved` |

Es la distinción que más fácil se confunde al implementar: **corregir no manda a nadie a la cola.**
Si después de un `PATCH` los productos aparecen en revisión, se implementó RF-31 donde iba RF-29.

En los dos casos el alcance es `WHERE classified_by_rule_id = :rule_id`: lo que esa equivalencia
clasificó, y nada más. Un producto que clasificó una persona a mano tiene esa columna nula, no
depende de ninguna equivalencia, y ni se reasigna ni vuelve a la cola.
