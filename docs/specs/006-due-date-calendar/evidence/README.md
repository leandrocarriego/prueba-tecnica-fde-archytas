# Verificación a mano — 006, tarea 45

**Primera corrida el 2026-08-31** contra el stack local, con datos sembrados a mano: un dueño,
cuatro vencimientos alrededor de hoy y un día con seis, que es lo que hace falta para que el
recorte de RF-08 tenga algo que recortar.

**Segunda corrida el mismo día**, después de corregir lo que la primera encontró.

Es lo único de la feature que **no se puede fijar con un test**. RF-41 no tiene código propio, así
que la única forma de saber si se cumple es abrirla y mirar. El arrastre (RF-19) y el selector de
fecha (RF-42) están acá por la misma razón: los dos son gestos del navegador, y lo que el backend
recibe de los dos es la misma llamada.

El teléfono es un **iPhone 13 emulado en Chromium** (390 × 664 CSS, `deviceScaleFactor` 3, eventos
táctiles). No es un teléfono de verdad: la última palabra sobre RF-41 sigue siendo de una persona
con el teléfono en la mano.

## Lo que se verificó

| Requisito | Resultado | Evidencia |
|---|---|---|
| RF-01 · un calendario, no una lista | ✅ grilla del mes de lunes a domingo; los días sin nada existen, vacíos, y los de relleno se distinguen | `rf01-grilla-del-mes.png` |
| RF-04 · abre en el mes en curso | ✅ 01/08 al 31/08, decidido por el backend | `rf41-mes-en-curso.png` |
| RF-05 · el control de mes | ✅ «Mes siguiente» lleva a 01/09–30/09 | `rf41-mes-siguiente-recorte.png` |
| RF-08 · el recorte por día | ✅ en las dos vistas: la celda del día 3 muestra cuatro y «y 2 más»; en el teléfono, cuatro y «y 2 más en este día» | `rf01-grilla-del-mes.png`, `rf41-dia-abierto.png` |
| RF-19 · arrastrar | ✅ del 26/08 al 30/08 arrastrando la tarjeta | `rf19-arrastre-escritorio.png` |
| RF-20, RF-21, RF-22 · qué queda registrado | ✅ las dos guardan la fecha original y quién movió; el arrastre sin motivo, el selector con motivo | ver abajo |
| RF-25 · confirmar al mover al pasado | ✅ preguntó; **respondiendo que no, no movió nada** · ⚠️ **cambió el mecanismo, ver abajo** | — |
| RF-42 · elegir la fecha de un selector | ✅ `<input type="date">` en el teléfono, con motivo opcional | `rf42-selector-de-fecha-telefono.png`, `rf42-movida-telefono.png` |
| RF-41 · consultar desde un teléfono | ✅ **en la segunda corrida** — ver abajo | `rf41-lo-que-se-ve-al-abrir.png`, `rf41-menu-desplegado.png` |

Lo que quedó en la base después de los dos movimientos, que es lo que RF-20 a RF-22 piden:

```
 due_date_id | previous_date |  new_date  | actor | reason
           1 | 2026-08-26    | 2026-08-30 |     2 |
           2 | 2026-08-30    | 2026-09-20 |     2 | Lo acordamos por telefono
```

## RF-41: qué encontró la primera corrida, y qué se corrigió

El contenido del calendario **siempre** estuvo bien en un teléfono, y eso es lo que se midió:

- `scrollWidth` = 390px con un viewport de 390px: **no hay desplazamiento horizontal**.
- Ninguna tarjeta se sale de la pantalla; la más ancha mide 318px.
- Los botones «Mover», «Corregir» y «Eliminar» entran en una línea y se tocan con el pulgar.
- El recorte por día sigue avisando cuántos hay.

El problema estaba antes: **al abrir `/calendario` en un teléfono, la primera pantalla entera era
el menú**. La barra lateral medía 832px de alto sobre un viewport de 664px y el título
«Calendario» arrancaba en y=864px. Hacía falta desplazarse una pantalla y media para ver el primer
vencimiento. No era del calendario: le pasaba a todas las pantallas.

**Corregido**: en pantallas angostas la barra se pliega en una franja que dice dónde está parada la
persona, con el botón que abre el resto (`components/auth/Navigation.tsx`). Medido después:

| | Antes | Después |
|---|---|---|
| Alto de la barra | 832px | **76px** |
| El título «Calendario» empieza en | y=864px | **y=108px** |
| ¿Hay que desplazarse para ver el calendario? | Sí, pantalla y media | **No** |

Desde `md` no cambió nada: la barra sigue fija a la izquierda y ahí no hay nada que plegar. La
conducta —plegada por omisión, se abre, se cierra al elegir una sección— está fijada en
`frontend/tests/navigation-collapsible.test.tsx`. Que **se vea** bien no lo demuestra ningún test:
eso es lo que demuestran las capturas de acá.

## Cómo repetirla

Los scripts que la corrieron son andamio, no producto, y viven fuera del repositorio. Lo que hace
falta para rehacerla: levantar el stack (`make dev`, backend y frontend nativos), un usuario con
contraseña, unos vencimientos alrededor de hoy —con un día de más de cuatro— y Playwright con
`p.devices["iPhone 13"]`.

## RF-25: la pregunta dejó de ser del navegador

**Las dos corridas de arriba lo verificaron con `window.confirm`**, el diálogo nativo. El review
del `Code-Reviewer` lo marcó y se reemplazó por un diálogo de la aplicación
(`components/ui/confirm-dialog.tsx`, sobre Radix). El motivo no fue estético:

- El `confirm` nativo no formatea nada, así que la fecha a la que se está por mover —el dato sobre
  el que la persona decide— iba pegada en una línea de texto plano.
- Algunos navegadores lo saltean —en un iframe, o con la pestaña sin foco— y devuelven `false` sin
  mostrar nada: el código cree que la persona dijo que no, y nunca se le preguntó.
- Congela el hilo: mientras está abierto no corre el canal en vivo ni el refresco de otra pestaña.

**Lo que ahora sí fija un test** y antes no: que la pregunta nombre el vencimiento y la fecha, que
decir que sí repita la movida con la confirmación puesta, que decir que no no mueva nada, y —lo que
más se rompe de una confirmación— que **cerrar por `Escape` cuente como «no»**
(`frontend/tests/calendar-move.test.tsx`).

**Lo que sigue sin verificarse a mano: cómo se ve el diálogo en un teléfono.** Es un modal sobre un
viewport de 390px, y eso es exactamente lo que ningún test ve. Las capturas de RF-25 de estas dos
corridas ya no muestran lo que la pantalla hace. **Hay que repetir la tarea 45 para ese requisito**,
con el mismo `p.devices["iPhone 13"]` de la sección anterior.
