# 006-due-date-calendar — Consistencia spec ↔ plan ↔ tasks

<!-- ARTEFACTO INTERNO. Hallazgos de `/analyze`. Los registra el Lead; los corrige el rol dueño de cada documento. -->

**Feature:** 006-due-date-calendar · **Corrido el:** 2026-08-31 · **Rol:** Lead

## Veredicto: **consistente** (2.ª corrida, 2026-08-31)

La primera corrida dio **inconsistente** con cinco hallazgos, dos bloqueantes. **Los cinco están
cerrados**: tres corrigiendo documentos, uno con una decisión del humano y uno enmendando un criterio
de aceptación de la spec firmada. El detalle original se conserva abajo, con su cierre.

**Lo que el veredicto significa y lo que no.** Consistente quiere decir que los tres documentos
describen la misma cosa, y ahora sí: la H5 tiene plan. **No** quiere decir que la feature esté lista
—le faltan 22 tareas, siete de ellas la H5 entera— ni que el Artículo VI se cumpla: sigue en Parcial,
con la diferencia de que ahora está incumplido **hasta una fecha** y no para siempre.

## Veredicto original: **inconsistente** (1.ª corrida)

Cinco hallazgos, **dos bloqueantes**. El más grande no es un desacuerdo entre documentos: es que
**para un tercio de la spec firmada no hay plan técnico**, y el desglose lo dejó a la vista al tener
que incluir una tarea cuya skill es `plan`.

**Aclaración de contexto, igual que en la 005.** `/analyze` corre normalmente antes de escribir
código; acá el código ya existe y el `plan.md` se declara a sí mismo *"un acta, no un pronóstico"*.
La corrida sigue valiendo —los tres documentos tienen que describir la misma cosa— pero mide una
implementación ocurrida, no frena una futura.

## Lo que sí cierra

- **Los 42 requisitos firmados tienen fila en la tabla de cobertura de `tasks.md`**, con al menos una
  tarea y al menos un test cada uno, y **los 42 tienen criterio de aceptación** en la spec, sin
  criterios sobrantes.
- **El plan nombra los 42.** Su *Mapa de requisitos* dice dónde vive cada uno y marca con `✗` los que
  no tienen implementación, en lugar de omitirlos. Es lo que hace que este análisis pueda ser corto.
- **Las ocho historias tienen tareas.**
- **El plan declara explícitamente que no hay código sin requisito firmado**, y lo verifiqué: no
  aparece superficie, tabla ni ruta de calendario que la spec no pida.
- **La spec no tiene marcadores pendientes ni decisiones técnicas filtradas**, está en `Estado:
  Aprobado` y firmada el 2026-08-30.
- **La excepción al Artículo V está registrada como la constitución lo exige**: qué se hizo, cuándo,
  quién la aprobó y con qué palabras. Se firmó sobre código ya construido y el plan lo dice sin
  adornos, incluyendo que eso convierte el gate en un registro.
- **El Contexto de traspaso está y es útil**, con sus tres destinatarios, y **le dice al Developer
  qué no tocar** —las tres líneas de `was_overdue`, la guarda de `_sync_due_date`— que es
  exactamente lo que un traspaso tiene que hacer.
- **Ningún módulo nuevo, ningún import cruzado**, y el plan argumenta por qué el calendario **no** es
  un módulo propio: reprogramar un vencimiento cambia el plazo del recibo y la medición del atraso,
  así que serían dos módulos leyéndose todo el tiempo.

## Hallazgos

### B-1 · El plan no resuelve la H5, y el desglose tuvo que pedir que se termine el plan

**Documento a corregir:** `plan.md` · **Rol dueño:** Backend-Architect (el transporte) y
Frontend-Architect (la pantalla) · **Bloquea `/implement`:** sí, para las tareas 32, 35 y 37.

RF-31 a RF-36 están firmados y **no tienen ninguna decisión técnica tomada**. El plan lo dice y lo
delega, en el Contexto de traspaso: *"cerrá dos cosas con el arquitecto: cómo viaja (WebSocket contra
SSE contra polling — nada de eso está decidido, y no lo decide este plan) y quién lo publica"*.

Eso invierte la cadena. **Elegir el transporte de un canal en vivo es arquitectura, y el Developer no
la decide**: el plan es justamente el artefacto donde esa decisión se toma y se justifica. La señal
está en el propio desglose: la **tarea 31 usa la skill `plan`**, y un `tasks.md` que contiene la tarea
de escribir su propio plan es la definición de un plan incompleto.

La decisión no es libre, y eso hace más raro que el plan no la haya tomado: `GEN-09` dice que un
handler corre en la transacción de quien publicó, así que **empujar a un socket dentro de esa
transacción hace que una caída del canal aborte el movimiento del vencimiento**. El plan ya identifica
la restricción y aun así no concluye.

**Corrección:** el Backend-Architect cierra en `plan.md` el transporte, quién publica y cómo se
sostiene `GEN-09`; el Frontend-Architect agrega la pantalla al plan. Recién entonces las tareas 32 y
35 se pueden escribir como tareas y la 31 desaparece.


> ✅ **Cerrado el 2026-08-31.** El humano decidió **construir la H5**, y el plan técnico se cerró el
> mismo día en `plan.md` → *La H5: el canal en vivo*: **SSE** sobre `GET /calendar/stream`,
> **`LISTEN`/`NOTIFY` de Postgres** para cruzar los dos workers de uvicorn (`docker-compose.yml:163`
> — el dato que descartaba cualquier canal en memoria), y un **Route Handler de Next** que pone el
> `Bearer` desde la cookie, porque `EventSource` no manda headers y un token no va en una query
> string. `GEN-09` se cumple sin acoplar nada: `NOTIFY` es transaccional, así que una transacción que
> aborta no notifica a nadie y la caída del canal de una persona no puede abortar el movimiento de
> otra. **La tarea que pedía escribir el plan desapareció** del desglose, que es la señal de que el
> hallazgo se cerró de verdad.
### B-2 · El Constitution Check declara el Artículo VI "Parcial" y no registra ninguna excepción

**Documento a corregir:** `plan.md`, y la decisión es del **humano** · **Rol dueño:** Backend-Architect
propone, el humano aprueba · **Bloquea `/implement`:** no por sí solo; va junto con B-1.

El Check marca **VI — Lo que no está tipado y testeado no está terminado** como **Parcial**, con el
motivo correcto —la H5 no existe, y ocho tests de integración no cubren ni las rutas ni los permisos
por comportamiento—. Pero la línea de cierre dice: *"Excepciones solicitadas: la del Artículo V, ya
registrada arriba. **Ninguna otra**"*.

Un artículo en Parcial sin excepción registrada es un artículo incumplido sin que nadie lo haya
aprobado. Es el mismo patrón que el hallazgo A-1 de la 005, y tiene las mismas dos salidas, las dos
del humano: registrar la excepción con su justificación, o tratar la brecha como bloqueante.

Con B-1 abierto, la salida honesta probablemente sea la segunda: **VI está en Parcial porque falta la
H5**, así que cerrar la H5 cierra el artículo, y no hace falta ninguna excepción.


> ✅ **Cerrado el 2026-08-31.** No se solicitó ninguna excepción, y era la salida correcta: la
> brecha del Artículo VI **es** la H5, y la H5 se construye. El Check dice ahora «Parcial, sin
> excepción solicitada» y nombra la condición de cierre: las tareas 31 a 36. Un artículo incumplido
> hasta una fecha es distinto de uno incumplido para siempre, y sólo el segundo necesita excepción.
### B-3 · La tarea 36 construye superficie que el cliente no firmó

**Documento a corregir:** `spec.md` si se acepta, `tasks.md` si se descarta · **Rol dueño:**
Solution-Designer, con el cliente · **Bloquea `/implement`:** sí, para esa tarea.

La tarea 36 pide que **la pantalla diga que no se actualiza sola** mientras la H5 no exista. Sale de
la sección *Riesgos* del plan, no de ningún requisito: RF-35 pide avisar cuando **se corta** una
conexión en vivo que existe, y esto es un cartel permanente que dice que esa conexión **nunca
existió**. No son lo mismo.

Y probablemente sea lo correcto: la propia spec llama peligrosa la confianza falsa, y hoy dos personas
pueden decidir sobre fotos distintas sin enterarse. Pero **el Lead no agrega superficie que el cliente
no firmó**, y un agente tampoco. Dos salidas, las dos del Solution-Designer:

1. **Entra a la spec** como requisito propio —el mínimo acordado de H5 mientras el canal no exista—.
2. **Sale de `tasks.md`**, y la brecha queda sólo documentada en el plan.

Es una decisión barata y urgente: mientras esté abierta, la pantalla sigue prometiendo en silencio
algo que no hace.


> ✅ **Cerrado el 2026-08-31.** El humano decidió **no construir el cartel**. La tarea se dio de
> baja y la spec no se toca. El riesgo queda aceptado explícitamente en `plan.md` → *Riesgos*,
> durante la ventana en que se construye el canal: es una ventana con fecha, no un estado
> permanente.
### B-4 · El criterio de aceptación de RF-30 pasa mientras el requisito falla

**Documento a corregir:** `spec.md` · **Rol dueño:** Solution-Designer · **Bloquea `/implement`:** no.

Es el hallazgo más fino de la corrida y el que más caro sale si nadie lo mira. El plan ya lo detectó
como deriva D1 y lo dijo con precisión; lo que agrego es qué documento hay que corregir.

RF-30 pide que una factura vencida sin recibo **siga señalada como tal aunque se la reprograme**. El
código busca los datos de la factura en la ventana de fechas pedida, no en las facturas de las
entradas que va a mostrar, así que una vencida reprogramada **a otro mes** vuelve sin proveedor, sin
estado de pago y sin la marca de vencida.

El criterio firmado es: *"Esa factura sigue apareciendo señalada como vencida sin recibo, aunque su
fecha ahora sea el 20"* — venció el 10, se reprogramó el 12 para el 20. **Los tres días caen en el
mismo mes, así que el criterio pasa y el requisito falla.** Un criterio verde que no prueba su
requisito es peor que no tener criterio: da por verificado lo que no se verificó.

**Corrección:** el criterio tiene que mover la fecha nueva **al mes siguiente**. Es un cambio de una
línea en la spec, y no cambia el alcance —cambia qué prueba el ejemplo—. La corrección del código es
la tarea 13 y su test es la 14, que hoy falla a propósito.


> ✅ **Cerrado el 2026-08-31.** El criterio ahora mueve la fecha **al mes siguiente**, que es donde
> el defecto aparece. Va con una nota de enmienda en `spec.md`, arriba de los criterios, diciendo qué
> se cambió y por qué. **No cambia el alcance** —RF-30 dice lo mismo que se firmó— pero toca un
> documento firmado, así que la enmienda queda a la vista para la próxima revisión con el cliente. La
> corrección del código sigue siendo la tarea 13, y su test, la 14.
### B-5 · RF-41 no tiene tarea que lo construya, y eso está bien dicho pero mal terminado

**Documento a corregir:** ninguno · **Rol dueño:** Tester · **Bloquea `/implement`:** no.

*"El sistema debe permitir consultar el calendario desde un teléfono"* no tiene código propio: la
pantalla usa utilidades responsive y **nunca se abrió en un teléfono**. Su única tarea, la 45, es una
verificación a mano, y la tabla de cobertura lo dice así en lugar de disimularlo.

La consecuencia hay que decirla: **si al abrirlo en un teléfono no anda, aparece trabajo que ninguna
tarea previó**. No es un error de los documentos —no se puede planificar la corrección de un defecto
que todavía no se observó— pero sí obliga a un orden: la tarea 45 se corre **antes** de declarar la
feature terminada, no después. Queda asignada al Tester con esa condición.


> ✅ **Cerrado el 2026-08-31**, sin cambios en los documentos: no había nada que corregir, sí algo
> que ordenar. La tarea 45 —abrir el calendario en un teléfono— **se corre antes de declarar la
> feature terminada, no después**, y queda asignada al Tester con esa condición. Si el teléfono
> muestra un problema, aparece trabajo que ninguna tarea previó: eso es esperable y no es una falla
> de los documentos.
## Qué le pasa a la cadena

**Actualizado el 2026-08-31, con los cinco hallazgos cerrados.** La H5 ya se puede implementar: tiene
plan, tiene contrato y tiene siete tareas que no deciden nada. El orden dentro de la historia importa
y está escrito: **primero D8 y D9** —que agregar y corregir publiquen su evento, y que borrar mande el
nombre de quien fue— y recién después el transporte. Con el canal andando y esas dos sin cerrar, la
mitad de los cambios no llegaría y ninguno diría quién lo hizo, y se vería como un bug del canal.

Lo que **sí** puede avanzar sin esperar ninguna decisión: las quince tareas pendientes que no son de
la H5 —empezando por la 13 y la 14 (la deriva D1, que es un defecto real con un test que hoy falla),
la 44 (el selector de fecha, la deriva más barata de toda la lista) y la 39 (el primer test que
verifica por comportamiento que ventas no escribe)—.

## Preguntas elevadas al humano — contestadas el 2026-08-31

| Pregunta | Respuesta |
|---|---|
| ¿Se construye la H5 o se difiere? (B-1, B-2) | **Se construye.** La spec firmada no se toca y RF-34 nunca estuvo en juego |
| ¿La pantalla dice que no se actualiza sola mientras tanto? (B-3) | **No.** El cartel se dio de baja: es superficie que el cliente no firmó |

**Nada quedó abierto**, salvo un hallazgo sin `RF` que no es alcance y que decide el Lead: si el test
de arquitectura que obliga a leer con `readFromApi` —hoy limitado a las pantallas de la 003— se
extiende al calendario, que hoy confunde una caída del backend con una negativa de permiso.
