# Tablero del negocio — Plan técnico

<!--
  ARTEFACTO INTERNO. No se exporta al cliente.
-->

**Feature:** 009-business-dashboard · **Spec aprobada el:** 2026-08-31 · **Fecha:** 2026-08-30
**Rol:** `Backend-Architect` · `Frontend-Architect`

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | Una lectura nueva: `/ventas` |
| II — Nada se descarta | Sí | **Es la feature entera.** Una venta repetida, rota o con un monto fuera de lo habitual no se suma y no se borra: queda apartada con su motivo, y cada indicador informa cuántos registros dejó afuera |
| III — Flujo unidireccional, `raw` inmutable | Sí | `raw` → `staging.sale_row` → `core.sale`. Lo que informó el portal queda en `portal_values` aunque alguien corrija el registro (RF-41) |
| IV — Las fronteras entre módulos son reales | Sí | `sales` contesta "ese producto no existe" contra **su propia proyección** de los códigos del catálogo, alimentada por `ProductsRegistered`. Los cortes de precios y stock los sirve `catalog`, que es su dueño, por su propio endpoint |
| **V — Spec primero, y con firma** | **Fuera de orden** | Firmada el 2026-08-31, después de construir. Ver abajo |
| VI — Lo que no está tipado y testeado no está terminado | Parcial | 13 tests de integración y 5 unitarios del parser. **El fixture de `/ventas` es derivado, no capturado** |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | Se reusa el cliente de `portal` |
| VIII — Un idioma para cada audiencia | Sí | |
| IX — Las dependencias entran por la puerta | Sí | Cero dependencias nuevas |

### Excepción al Artículo V, y quién la aprobó

El Artículo V dice que ninguna feature pasa a planificación técnica sin firma, y que una excepción
**la aprueba el humano y queda registrada en el plan**. Pasó en dos momentos, como en la 006.

**Al construir, el 2026-08-30.** El humano pidió implementar las seis specs pendientes y, consultado
sobre las tres que estaban en borrador, respondió *"Las seis, igual"*.

**Al firmar, el 2026-08-31.** Antes de la firma, una auditoría recorrió la spec contra el paso 1 de
`approve_spec.md` y encontró bloqueos reales, que se cerraron escribiendo lo que ya estaba acordado
en el brief, en otra spec firmada o en el código —nunca con una decisión de producto nueva—. Cada
elección quedó listada en la sección **«Para confirmar al firmar»** de `spec.md`.

Al firmar no creció el alcance: RF-21 y RF-22 se reescribieron en su lugar para decir lo que el sistema ya hace —el promedio de las ventas contadas de ese producto, sin ventana; diferencia porcentual; tolerancia inicial de 300 % en el panel—. El requisito estaba vago, el código no.

Queda dicho, porque el orden importa y este documento es donde consta: **se firmó sobre código ya
construido**. Para esta feature el gate del Artículo V es un registro, no un filtro — no hubo un
momento en que el acuerdo pudiera haber cambiado lo que se construía. Lo que el gate sí puede hacer
todavía es `/converge`.

## Enfoque

La frase del cliente es la especificación: *"que se nos avise cuáles son, no que se sumen como si
fueran válidas"*. Todo lo demás sale de ahí.

**Repetidas idénticas se cuentan una sola vez, sin preguntar** (RF-11): no hay nada que decidir. Con
**un dato distinto**, ninguna de las dos suma hasta que alguien elija (RF-13, RF-15) — y la pantalla
las muestra enfrentadas con los campos en que difieren señalados, que es lo que convierte "estas dos
no son iguales" en una decisión de un segundo.

**El código se compara sin sus diferencias de escritura** (RF-10), y ahí está el número que el
relevamiento midió: 17 grupos mirando el código tal cual, 27 normalizándolo. La normalización saca
espacios, guiones y mayúsculas y **nada más**: un código que difiere en un dígito es otra venta, y
ninguna regla puede tapar eso.

**Lo habitual para un producto se deriva de lo ya contado**, no de una tabla que alguien mantenga
(RF-21). Una cifra típica guardada es una segunda verdad sobre las mismas ventas, y queda vieja la
primera vez que se corrige una.

**Cada indicador informa lo que excluyó, incluso cuando excluyó cero** (RF-25, RF-27). "Cero
excluidos" es una respuesta; un silencio no.

## Lo que hay que saber antes de confiar en esto

> **El fixture de `/ventas` es derivado, no capturado**, igual que el de la bandeja. Reproduce las
> 588 filas y las anomalías exactas que la spec enumera, pero las columnas son una deducción. Vale
> lo mismo que en la 007: hay que recapturar cuando se pueda entrar al portal.

**El corte de stock depende de que el origen siga publicando el stock cada día.** Es el supuesto que
la spec declara, y ahora tiene una consecuencia concreta: `core.stock_point` guarda una foto por
producto y por día, y el corte compara la del principio del período con la del final. Un producto
sin foto en alguno de los dos extremos **no** cuenta como cero: queda excluido y el corte lo dice.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `portal` | Lee `/ventas` | No |
| `ingestion` | `staging.sale_row`, el parser y la clave normalizada del código | No |
| `sales` | **Todo lo comercial**: registros, deduplicación, apartados e indicadores | **Sí** |
| `catalog` | `core.stock_point` y los tres cortes que son suyos: precios, stock y altas | No |

## Contratos

| Ruta | Quién | Requisitos |
|---|---|---|
| `GET /sales` | dueño · ventas | RF-04, RF-15 |
| `GET /sales/review` | dueño · ventas | RF-13, RF-14, RF-23, RF-26, RF-28, RF-30 |
| `POST`/`DELETE /sales/groups/{code_key}/resolution` | dueño · ventas | RF-29, RF-31 a RF-36 |
| `PATCH /sales/{id}` | dueño · ventas | RF-38, RF-39, RF-41 |
| `GET /dashboard/sales` | dueño · ventas | RF-03, RF-05 a RF-07, RF-25, RF-27 |
| `GET /dashboard/catalog` | dueño · ventas | RF-42 a RF-46 |

Compras no llega a ninguna (RF-08).

## Alternativas descartadas

- **Un solo endpoint de tablero.** RF-05 pide que cada corte elija su período **por separado**, y un
  endpoint único obligaría a mandar cuatro ventanas o a compartir una.
- **Que `sales` calcule los cortes de precios y stock.** Son del catálogo. `sales` tendría que
  proyectarse el historial de precios entero para dibujar una curva.
- **Un valor "típico" por producto guardado en una tabla.** Ver *Enfoque*.

## Contexto de traspaso

**Para el Developer** — Lo decidido: la clave normalizada del código se **guarda** en
`staging.sale_row.code_key` y no se deriva al leer, así el agrupamiento es un índice y significa
siempre lo mismo que significaba cuando la fila aterrizó.

**Para el Tester** — Lo que falla en silencio es la deduplicación: si una repetida con datos
distintos se contara, el tablero daría un número más alto y nadie lo notaría hasta que el cliente lo
verifique a mano — que es exactamente lo que la feature existe para evitar.

**Para el Code-Reviewer** — `GEN-02` sobre `sales`: la tentación es importar `catalog` para saber si
un producto existe. Si aparece ese import, el diseño se rompió.
