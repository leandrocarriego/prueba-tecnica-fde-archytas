# Calendario de vencimientos — Plan técnico

<!--
  ARTEFACTO INTERNO. No se exporta al cliente.
-->

**Feature:** 006-due-date-calendar · **Estado de la spec:** Borrador · **Fecha:** 2026-08-30
**Rol:** `Backend-Architect` · `Frontend-Architect`

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | El calendario no toca SIGProv: se arma con las facturas que `004` ya registró |
| II — Nada se descarta | Sí | Cada movimiento de un vencimiento queda en `core.due_date_change` con quién lo hizo y el motivo. Nada se pisa |
| III — Flujo unidireccional, `raw` inmutable | Sí | No hay extracción en esta feature |
| IV — Las fronteras entre módulos son reales | Sí | El calendario vive en `purchases`, con la factura. Ver *Alternativas descartadas* |
| **V — Spec primero, y con firma** | **Fuera de orden** | Firmada el 2026-08-30, después de construir. Ver abajo |
| VI — Lo que no está tipado y testeado no está terminado | Parcial | 8 tests de integración sobre las reglas de mover un vencimiento. **La H5 —el canal en vivo— no está construida**, ver *Lo que falta* |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | No hay credenciales en juego |
| VIII — Un idioma para cada audiencia | Sí | |
| IX — Las dependencias entran por la puerta | Sí | Cero dependencias nuevas |

### Excepción al Artículo V, y quién la aprobó

El Artículo V dice que ninguna feature pasa a planificación técnica sin firma, y que una excepción
**la aprueba el humano y queda registrada en el plan**. Es lo que pasó, en dos momentos.

**Al construir, el 2026-08-30.** El humano pidió implementar las seis specs pendientes y,
consultado sobre las tres que estaban en borrador, respondió *"Las seis, igual"*. Se construyó sin
acuerdo del cliente, sabiendo que si al firmar pedía cambios el costo sería de rehacer, no de
construir.

**Al firmar, el mismo día.** La spec quedó **Aprobada el 2026-08-30**, después de que una auditoría
la recorriera entera contra el paso 1 de `approve_spec.md` y no encontrara nada que corregir: sin
marcadores pendientes, sin secciones vacías, sin decisiones técnicas filtradas, con sus siete
diagramas hechos, validados y en lenguaje de negocio.

Queda dicho, porque el orden importa y este documento es donde consta: **se firmó sobre código ya
construido**. Eso convierte el gate del Artículo V en un registro, no en un filtro — para esta
feature no hubo un momento en que el acuerdo pudiera haber cambiado lo que se construía. Lo que el
gate sí puede hacer todavía es `/converge`: contrastar el código contra lo que quedó firmado, y si
no describen el mismo producto, la decisión de qué corregir sigue siendo del humano.

Al firmar estaba sobre la mesa que **la H5 completa —RF-31 a RF-36, el canal en vivo— no está
construida** (ver *Lo que falta*). Las ocho historias son severables entre sí: si se decide diferir
o descartar el canal en vivo, se saca H5 con sus seis requisitos y el resto de la spec se sostiene
sin reescritura.

## Enfoque

**Un vencimiento es una fila, no una columna de la factura.** Porque se mueve, y moverlo tiene que
conservar de dónde venía. `core.due_date` guarda la fecha vigente y la original; cada movimiento va
a `core.due_date_change`.

**La distinción que hay que no romper** es la que separa RF-26/RF-27 de RF-28/RF-30:

| | Se reprograma **antes** de vencer | Se reprograma **después** |
|---|---|---|
| El plazo para emitir el recibo | se mueve con la fecha nueva | **no se mueve**: sigue negado |
| El atraso del proveedor | se mide contra la fecha nueva | se mide contra la **original** |
| ¿Sigue señalada como vencida sin recibo? | no | **sí** |

Si mover una tarjeta habilitara el recibo de una factura vencida, RF-34 de la 005 dejaría de valer
con sólo arrastrar. Está testeado en
`test_rescheduling_one_that_already_fell_due_changes_none_of_that`.

## Lo que falta

**La H5 completa: RF-31 a RF-36, el canal en vivo.** Lo que dos personas mirando el calendario ven
hoy es el estado del momento en que cargaron la pantalla; un cambio de otro no aparece solo, no se
avisa quién lo hizo, y no hay aviso de conexión interrumpida.

Está anotado en la pantalla (`app/(private)/calendario/page.tsx`) y es lo primero que hay que
construir si la 006 se firma. El resto de la feature no depende de eso: RF-34 —dos personas mueven
el mismo vencimiento, gana el último y el anterior queda en el historial— **sí** está resuelto, por
la tabla de movimientos.

## Alternativas descartadas

- **Un módulo `calendar` propio.** El contenido central del calendario es el vencimiento de una
  factura, y reprogramarlo cambia el plazo del recibo de esa factura. Serían dos módulos leyéndose
  todo el tiempo, que es la señal de que son uno.
- **Guardar el vencimiento sólo en `core.invoice`.** No habría dónde poner un vencimiento cargado a
  mano (RF-12), ni cómo conservar la fecha original.

## Contexto de traspaso

**Para el Developer** — Lo que sigue abierto es el canal en vivo. El resto está: `_sync_due_date`
mantiene la entrada de una factura en paso con la factura, y **no la pisa si alguien ya la movió a
mano** — una decisión de una persona no la deshace la próxima lectura del portal.

**Para el Tester** — El caso que más fácil se rompe es reprogramar una vencida: si después de eso se
puede emitir el recibo, se implementó RF-26 donde iba RF-28.
