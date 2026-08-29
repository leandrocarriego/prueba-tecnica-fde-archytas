# Calendario de vencimientos — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Borrador · **Feature:** 006-due-date-calendar · **Fecha:** 2026-08-29

<!-- `/approve-spec` completa Aprobada por y Fecha de aprobación, y pasa Estado a Aprobado. -->

## Problema

Resuelve **P11 — El problema de las fechas**.

Los vencimientos existen, pero no hay ningún lugar donde se los vea todos juntos y ordenados en el
tiempo. Y cuando dos personas del equipo miran lo mismo, cada una está mirando su propia foto vieja
de la situación.

En palabras del cliente: *"Necesitamos un calendario visual donde se vea de un vistazo cuándo vence
cada factura, poder agregar un vencimiento nuevo o mover uno si se reprogramó, y que si dos personas
de nuestro equipo lo están mirando al mismo tiempo, ambas vean los cambios en el momento, no que una
tenga que refrescar la página para enterarse."*

Y el mismo calendario tiene que contestar la pregunta que dejó abierta **P12**: *"Nos gustaría que
el calendario nos muestre qué facturas ya tienen su recibo generado y cuáles todavía no."*

## Objetivo

Que el equipo vea en un solo calendario todo lo que vence y cuándo, qué falta pagar y qué recibo
falta emitir; que pueda agregar y reprogramar vencimientos desde la computadora o desde el teléfono;
y que dos personas mirándolo al mismo tiempo vean el mismo estado sin refrescar la pantalla.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El dueño | Ve el calendario completo, agrega vencimientos y reprograma |
| Marcela — compras | Ve el calendario completo, agrega vencimientos y reprograma |
| Julián — ventas | Consulta el calendario. No agrega ni reprograma |
| El sistema | Coloca en el calendario los vencimientos de las facturas y avisa a quienes lo están mirando cuando alguien cambia algo |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que reprogramar un vencimiento es una decisión del negocio y no una corrección de un
  error.** Por eso el sistema lo permite, guarda la fecha original y registra quién lo movió: el
  calendario refleja un acuerdo que cambió, no borra el que había.

- **Se asume que la fecha nueva se acordó antes con el proveedor.** Es lo que justifica que una
  reprogramación hecha **antes** del vencimiento valga a todos los efectos: el plazo del recibo y el
  atraso del proveedor pasan a medirse contra ella. El sistema no tiene forma de verificar ese
  acuerdo: lo hace explicable dejando registrado quién reprogramó, cuándo y desde qué fecha.

- **Se asume que el trabajo del día a día se hace desde la computadora.** El teléfono está
  comprometido para consultar y para reprogramar eligiendo la fecha; la carga de vencimientos
  nuevos y el arrastre con el dedo, no.

## Historias de usuario

### H1 — Ver de un vistazo qué vence y cuándo *(prioridad más alta)*
Como **Marcela**, quiero ver en un calendario todo lo que vence, mes por mes, para saber qué se
viene sin recorrer la lista de facturas.

**Cómo se prueba que anda:** se abre el calendario, se abre en el mes en curso, en cada día están
los vencimientos de ese día con el proveedor y el monto, y se puede pasar al mes siguiente y al
anterior.

### H2 — Cuáles ya tienen su recibo y cuáles no
Como **Marcela**, quiero distinguir en el calendario, sin abrir nada, qué facturas ya tienen su
recibo de recepción emitido y cuáles no, para ver de un golpe qué me falta hacer esta semana.

**Cómo se prueba que anda:** en el calendario se distinguen a simple vista las que tienen recibo de
las que no, y se pueden mostrar sólo las que no lo tienen.

### H3 — Agregar un vencimiento propio
Como **Marcela**, quiero cargar en el calendario un vencimiento que no viene de una factura, para
tener todo lo que hay que pagar en un solo lugar.

**Cómo se prueba que anda:** se carga un vencimiento con su fecha, su descripción y su monto,
aparece en el calendario ese día, queda registrado quién lo cargó, y si el monto estaba mal se lo
puede corregir.

### H4 — Reprogramar arrastrando, sin perder la fecha original
Como **Marcela**, quiero mover un vencimiento a otro día arrastrándolo, y que quede guardado cuándo
vencía antes, para que el cambio sea rápido y siga siendo explicable.

**Cómo se prueba que anda:** se arrastra un vencimiento del 10 al 20, el calendario lo muestra el
20, y al abrirlo se ve que originalmente vencía el 10 y quién lo movió.

### H5 — Dos personas, el mismo calendario
Como **dueño**, quiero que cuando Marcela mueva un vencimiento, yo lo vea en el momento sin
refrescar, para que no tomemos decisiones sobre dos versiones distintas de la misma semana.

**Cómo se prueba que anda:** dos personas abren el calendario en dos pantallas; una mueve un
vencimiento y la otra lo ve moverse sin tocar nada.

### H6 — Ventas mira, no toca
Como **dueño**, quiero que Julián pueda consultar el calendario pero no cambiarlo, para que sepa qué
se viene sin poder mover fechas que no le corresponden.

**Cómo se prueba que anda:** Julián abre el calendario y lo ve completo; intenta arrastrar un
vencimiento y el sistema no lo permite.

### H7 — Qué falta pagar, sin salir del calendario
Como **dueño**, quiero ver en el calendario cuáles facturas están saldadas, cuáles van por la mitad
y cuáles no se tocaron, y poder sacar de la vista las saldadas, para que el calendario muestre lo
que todavía hay que resolver.

**Cómo se prueba que anda:** cada factura del calendario se ve saldada, parcial o sin pagos, y al
pedir ocultar las saldadas el calendario deja de mostrarlas.

### H8 — El calendario en el teléfono
Como **Marcela**, quiero abrir el calendario desde el teléfono y mover un vencimiento eligiendo la
fecha nueva, para no depender de estar frente a la computadora cuando el proveedor me avisa un
cambio.

**Cómo se prueba que anda:** se abre el calendario desde un teléfono, se ve qué vence, y se
reprograma un vencimiento eligiendo la fecha nueva de un selector, sin arrastrarlo.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe mostrar un calendario con los vencimientos ubicados en su fecha. | H1 |
| RF-02 | El sistema debe mostrar, para cada vencimiento del calendario, su descripción, su monto y su proveedor cuando lo tenga. | H1 |
| RF-03 | El sistema debe colocar en el calendario el vencimiento de cada factura registrada. | H1 |
| RF-04 | El sistema debe abrir el calendario en el mes en curso. | H1 |
| RF-05 | El sistema debe permitir avanzar y retroceder de mes en el calendario. | H1 |
| RF-06 | El sistema debe distinguir en el calendario los vencimientos ya pasados de los que están por venir. | H1 |
| RF-07 | El sistema debe permitir abrir un vencimiento del calendario y llegar a la factura que lo originó. | H1 |
| RF-08 | Si un día tiene más vencimientos de los que entran en pantalla, entonces el sistema debe indicar cuántos hay y permitir verlos todos. | H1 |
| RF-09 | El sistema debe distinguir en el calendario las facturas con su recibo de recepción emitido de las que no lo tienen. | H2 |
| RF-10 | El sistema debe permitir mostrar en el calendario únicamente las facturas sin su recibo de recepción emitido. | H2 |
| RF-11 | El sistema debe señalar en el calendario las facturas vencidas sin su recibo de recepción emitido. | H2 |
| RF-12 | El sistema debe permitir al dueño y al rol compras agregar un vencimiento indicando su fecha, su descripción y su monto. | H3 |
| RF-13 | Cuando alguien agregue un vencimiento, el sistema debe registrar quién lo agregó y cuándo. | H3 |
| RF-14 | El sistema debe distinguir los vencimientos cargados a mano de los que provienen de una factura. | H3 |
| RF-15 | El sistema debe permitir al dueño y al rol compras corregir la descripción y el monto de un vencimiento cargado a mano. | H3 |
| RF-16 | Cuando alguien corrija un vencimiento cargado a mano, el sistema debe registrar quién lo corrigió, cuándo y cuál era el valor anterior. | H3 |
| RF-17 | El sistema debe permitir al dueño y al rol compras eliminar un vencimiento cargado a mano. | H3 |
| RF-18 | El sistema debe impedir eliminar del calendario un vencimiento que proviene de una factura. | H3 |
| RF-19 | El sistema debe permitir al dueño y al rol compras mover un vencimiento a otra fecha arrastrándolo. | H4 |
| RF-20 | Cuando alguien mueva un vencimiento, el sistema debe conservar su fecha anterior. | H4 |
| RF-21 | Cuando alguien mueva un vencimiento, el sistema debe registrar quién lo movió y cuándo. | H4 |
| RF-22 | Cuando alguien mueva un vencimiento, el sistema debe ofrecer escribir un motivo, sin exigirlo. | H4 |
| RF-23 | El sistema debe mostrar, al abrir un vencimiento reprogramado, su fecha original, todas sus reprogramaciones y los motivos que se hayan escrito. | H4 |
| RF-24 | El sistema debe señalar en el calendario los vencimientos que fueron reprogramados. | H4 |
| RF-25 | Si un vencimiento se mueve a una fecha anterior a la de hoy, entonces el sistema debe pedir confirmación antes de aplicar el cambio. | H4 |
| RF-26 | Cuando se reprograme el vencimiento de una factura antes de que venza, el sistema debe tomar la fecha nueva como plazo para emitir su recibo de recepción. | H4 |
| RF-27 | Cuando se reprograme el vencimiento de una factura antes de que venza, el sistema debe medir el atraso de su proveedor contra la fecha nueva. | H4 |
| RF-28 | Si se reprograma una factura que ya venció sin su recibo de recepción, entonces el sistema debe mantener impedida su emisión. | H4 |
| RF-29 | Si se reprograma una factura que ya venció, entonces el sistema debe medir el atraso de su proveedor contra su fecha original. | H4 |
| RF-30 | Si se reprograma una factura que ya venció sin su recibo de recepción, entonces el sistema debe seguir señalándola como vencida sin recibo. | H4 |
| RF-31 | Cuando alguien agregue, mueva, corrija o elimine un vencimiento, el sistema debe reflejar el cambio en las pantallas de las demás personas que estén mirando el calendario. | H5 |
| RF-32 | El sistema debe reflejar ese cambio sin que la persona que mira tenga que recargar la pantalla. | H5 |
| RF-33 | El sistema debe indicar, junto a un cambio recibido, quién lo hizo. | H5 |
| RF-34 | Si dos personas mueven el mismo vencimiento, entonces el sistema debe aplicar el último cambio y conservar el anterior en el historial. | H5 |
| RF-35 | Si la conexión en vivo se interrumpe, entonces el sistema debe avisar a quien mira que el calendario puede estar desactualizado. | H5 |
| RF-36 | Cuando la conexión en vivo se restablezca, el sistema debe mostrar el estado actualizado del calendario. | H5 |
| RF-37 | El sistema debe permitir al rol ventas consultar el calendario. | H6 |
| RF-38 | El sistema debe impedir al rol ventas agregar, corregir, mover o eliminar un vencimiento. | H6 |
| RF-39 | El sistema debe mostrar, para cada vencimiento que provenga de una factura, si está saldada, parcialmente pagada o sin pagos. | H7 |
| RF-40 | El sistema debe permitir ocultar del calendario las facturas saldadas. | H7 |
| RF-41 | El sistema debe permitir consultar el calendario desde un teléfono. | H8 |
| RF-42 | El sistema debe permitir al dueño y al rol compras mover un vencimiento eligiendo su fecha nueva, sin arrastrarlo. | H8 |

## Reglas de negocio

- **Mover un vencimiento mueve la fecha, no la deuda.** La fecha nueva no cambia el monto de la
  factura, ni su estado de pago, ni lo que se le debe al proveedor.
- **Reprogramar nunca borra la fecha original.** Un vencimiento movido conserva de dónde venía, quién
  lo movió y cuándo: si mañana hay que explicar por qué se pagó tarde, la explicación tiene que
  estar.
- **Reprogramar a tiempo mueve todo; reprogramar tarde mueve sólo la fecha de pago.** Si el acuerdo
  con el proveedor se hace antes de que la factura venza, la fecha nueva vale a todos los efectos:
  hasta ahí se puede emitir el recibo y contra ella se mide el atraso. Si la factura ya se venció, la
  fecha nueva dice cuándo se va a pagar, pero no destraba el recibo ni borra el atraso: eso ya pasó y
  el sistema no lo reescribe.
- **Del vencimiento que viene de una factura, en el calendario sólo se cambia la fecha.** El monto y
  la descripción son de la factura y se corrigen ahí. Los vencimientos cargados a mano sí se corrigen
  desde el calendario, guardando el valor anterior.
- **Un vencimiento que viene de una factura no se elimina del calendario.** La factura existe y vence:
  se puede reprogramar, no hacer desaparecer. Los vencimientos cargados a mano sí se pueden eliminar,
  porque los puso una persona.
- **Cuando dos personas cambian lo mismo, vale el último cambio y los dos quedan registrados.** El
  sistema no elige cuál tenía razón: deja ver qué pasó y quién lo hizo.
- **Ventas consulta, no edita.** Saber qué se viene le sirve; mover fechas de compras no es su
  trabajo.
- **El calendario en vivo es una promesa que se cumple o se avisa.** Si la conexión en vivo se cae,
  el sistema lo dice: es peor mirar un calendario quieto creyéndolo al día que saber que hay que
  recargarlo.

## Criterios de aceptación

- [ ] **RF-01** — El calendario muestra cada vencimiento en el día que le corresponde.
- [ ] **RF-02** — Cada vencimiento se lee con su descripción, su monto y su proveedor.
- [ ] **RF-03** — Cargada una factura con vencimiento, aparece en el calendario sin que nadie la agregue.
- [ ] **RF-04** — Al abrirlo, el calendario muestra el mes en curso.
- [ ] **RF-05** — Se pasa al mes siguiente y al anterior desde el propio calendario.
- [ ] **RF-06** — Lo que ya venció se distingue a simple vista de lo que está por venir.
- [ ] **RF-07** — Desde un vencimiento del calendario se llega a la factura que lo originó.
- [ ] **RF-08** — Un día con ocho vencimientos indica que hay ocho y permite verlos todos.
- [ ] **RF-09** — Las facturas con recibo emitido se distinguen a simple vista de las que no lo tienen.
- [ ] **RF-10** — Se puede pedir ver sólo las facturas sin recibo, y el calendario muestra sólo esas.
- [ ] **RF-11** — Las facturas vencidas sin recibo aparecen señaladas en el calendario.
- [ ] **RF-12** — Marcela carga un vencimiento propio y aparece en su fecha.
- [ ] **RF-13** — Ese vencimiento figura con el nombre de Marcela y la fecha en que lo cargó.
- [ ] **RF-14** — En el calendario se distingue un vencimiento cargado a mano de uno que viene de una factura.
- [ ] **RF-15** — Un vencimiento cargado a mano con el monto equivocado se corrige sin borrarlo.
- [ ] **RF-16** — Esa corrección muestra quién la hizo, cuándo, y cuál era el monto anterior.
- [ ] **RF-17** — Un vencimiento cargado a mano se puede eliminar.
- [ ] **RF-18** — Un vencimiento que viene de una factura no ofrece la opción de eliminarlo.
- [ ] **RF-19** — Se arrastra un vencimiento del 10 al 20 y queda en el 20.
- [ ] **RF-20** — Ese vencimiento sigue mostrando que originalmente vencía el 10.
- [ ] **RF-21** — Figura quién lo movió y cuándo.
- [ ] **RF-22** — Se puede mover un vencimiento sin escribir nada, y también escribiendo el motivo.
- [ ] **RF-23** — Un vencimiento movido tres veces muestra las tres fechas por las que pasó y los motivos escritos.
- [ ] **RF-24** — Los vencimientos reprogramados se distinguen en el calendario de los que nunca se movieron.
- [ ] **RF-25** — Al arrastrar un vencimiento a una fecha ya pasada, el sistema pide confirmación, y sin ella el vencimiento no se mueve.
- [ ] **RF-26** — Reprogramada del 10 al 20 una factura que todavía no venció, su recibo se puede emitir hasta el 20.
- [ ] **RF-27** — Esa misma factura, pagada el 18, no cuenta como atraso de su proveedor.
- [ ] **RF-28** — Una factura que venció el 10 sin recibo, reprogramada el 12 para el 20, sigue sin permitir emitirlo.
- [ ] **RF-29** — Esa factura, pagada el 18, cuenta ocho días de atraso: los que corren desde el 10.
- [ ] **RF-30** — Esa factura sigue apareciendo señalada como vencida sin recibo, aunque su fecha ahora sea el 20.
- [ ] **RF-31** — Marcela mueve un vencimiento y el dueño, que está mirando, lo ve moverse.
- [ ] **RF-32** — El dueño no tocó nada para verlo: no recargó la pantalla.
- [ ] **RF-33** — El dueño ve que ese cambio lo hizo Marcela.
- [ ] **RF-34** — Movido el mismo vencimiento por dos personas casi a la vez, queda la última fecha y el historial muestra los dos movimientos.
- [ ] **RF-35** — Cortada la conexión, la pantalla avisa que el calendario puede estar desactualizado.
- [ ] **RF-36** — Restablecida la conexión, el calendario se pone al día solo.
- [ ] **RF-37** — Julián abre el calendario y lo ve completo.
- [ ] **RF-38** — Julián intenta arrastrar un vencimiento y no puede.
- [ ] **RF-39** — Cada factura del calendario se ve saldada, parcial o sin pagos.
- [ ] **RF-40** — Pedido ocultar las saldadas, el calendario deja de mostrarlas y sigue mostrando el resto.
- [ ] **RF-41** — El calendario se abre desde un teléfono y se ve qué vence cada día.
- [ ] **RF-42** — Desde el teléfono se reprograma un vencimiento eligiendo la fecha nueva, sin arrastrarlo.

## Fuera de alcance

- **Emitir el recibo de recepción desde el calendario.** El calendario muestra cuáles lo tienen y
  cuáles no; emitirlo es **P12 — El problema de los recibos**.
- **Registrar un pago desde el calendario.** El calendario muestra si una factura está saldada,
  parcial o sin tocar; registrar el pago es **P5 — El problema de los pagos a medias**.
- **Los avisos por vencimiento próximo.** El calendario se mira; el aviso que sale del sistema
  —para que no haya que acordarse de mirarlo— es **P12** y comparte canal con **P8**.
- **Un calendario de ventas o de entregas.** Acá entran vencimientos de pago.
- **Vencimientos que se repiten solos.** Alquileres, sueldos e impuestos se cargan de a uno, cada
  vez. Que el sistema los repita mes a mes no está comprometido.
- **Cargar un vencimiento nuevo desde el teléfono.** Desde el teléfono se consulta y se reprograma;
  la carga se hace desde la computadora.
- **Arrastrar con el dedo.** En el teléfono se reprograma eligiendo la fecha, no arrastrando.
- **Sincronizar con un calendario externo** (el del correo, el del teléfono). No se pidió.
- **Escribir la reprogramación en el portal del proveedor.** El origen es de sólo lectura: la fecha
  reprogramada vive del lado nuevo.
