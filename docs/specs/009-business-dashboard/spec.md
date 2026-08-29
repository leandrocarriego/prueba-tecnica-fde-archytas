# Tablero del negocio — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Borrador · **Feature:** 009-business-dashboard · **Fecha:** 2026-08-28

<!-- `/approve-spec` completa Aprobada por y Fecha de aprobación, y pasa Estado a Aprobado. -->

## Problema

Resuelve **P3 — El problema de no ver nada**.

Los datos existen desde 2023, pero están repartidos y nadie los mira juntos. Y hay una razón por la
que mirarlos juntos hoy sería peor que no mirarlos: **entre esos datos hay ventas cargadas dos veces
y ventas con datos rotos**, y un tablero que las suma como si fueran válidas da un número que el
cliente va a desmentir la primera vez que lo verifique a mano.

En palabras del cliente: *"Tenemos datos de ventas desde 2023 hasta ahora, pero están repartidos y
nadie los mira juntos. Necesitamos poder ver de un vistazo cómo venimos: cuánto facturamos por mes,
cómo evolucionaron los precios, qué pasó con el stock, qué productos son nuevos. El problema es que
en esos datos hay ventas cargadas dos veces por error (cada venta tiene un código, a veces el mismo
código aparece repetido) y otras con datos rotos, necesitamos que se nos avise cuáles son, no que se
sumen como si fueran válidas."*

El relevamiento midió el desorden sobre **588 registros de ventas**: **17 grupos de ventas
repetidas** comparando el código tal cual viene y **27 si primero se normaliza el código**, de los
cuales **6 tienen datos en conflicto** (mismo código, cantidades distintas). Además, **3 ventas sin
fecha, 3 con una fecha que no existe (31/02/2025), 3 sin total, 3 con cantidad negativa, 2 con el
total inflado diez veces y 1 apuntando a un producto que no existe**.

## Objetivo

Que el cliente vea de un vistazo cómo viene el negocio desde 2023, con la certeza de que ningún
número está inflado por una venta contada dos veces o por un dato roto, y sabiendo siempre cuántos
registros quedaron afuera de cada número y por qué.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El sistema | Trae las ventas del portal, unifica las repetidas que son idénticas, aparta las que necesitan una decisión y las rotas, y calcula los indicadores con lo que queda |
| Julián — ventas | Mira el tablero y resuelve las ventas apartadas: decide qué hacer con cada repetida y con cada dato roto |
| El dueño | Mira el tablero completo, y también puede resolver ventas apartadas |
| Marcela — compras | No accede al tablero comercial ni a las ventas |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que el histórico relevante arranca en 2023**, como indicó el cliente.

- **Se asume que este tablero se construye sobre las ventas.** El gasto por rubro y todo lo que
  venga de compras tiene su propio problema (**P7**) y su propia pregunta abierta sobre de dónde
  sale el dato.

- **Se asume que el stock de cada producto se puede reconstruir a partir de lo que el origen publica
  cada día.** El corte de stock compara la foto del inicio del período con la del final. Si el
  origen dejara de publicar el stock, ese corte no se puede sostener, y se avisaría antes de que el
  cliente lo note.

- **Se asume que un producto está "dado de alta" el día que aparece por primera vez en el sistema.**
  El origen no informa una fecha de alta; lo que se sabe es cuándo se lo vio por primera vez. Para
  los productos que ya existían cuando arranca el sistema, esa fecha es la de la primera lectura, y
  por eso el corte de altas empieza a ser fiel recién desde ahí.

## Historias de usuario

### H1 — Cuánto facturamos, mes por mes *(prioridad más alta)*
Como **Julián**, quiero ver cuánto se facturó cada mes desde 2023, para saber cómo viene el negocio
sin armar la planilla a mano.

**Cómo se prueba que anda:** se abre el tablero, lo primero que se lee es la facturación del período
con cuántas ventas dejó afuera, está la facturación mes a mes desde 2023, y el total de un mes
cualquiera coincide con la suma de sus ventas válidas hecha a mano.

### H2 — Las repetidas no se suman
Como **dueño**, quiero que una venta cargada dos veces no se cuente dos veces, para que el número no
esté inflado.

**Cómo se prueba que anda:** el mes que tiene ventas repetidas muestra el total sin contarlas dos
veces, dice cuántas unificó solo por ser idénticas, y cuántas quedaron esperando una decisión.

### H3 — Las rotas tampoco
Como **dueño**, quiero que una venta sin fecha, sin total, con una cantidad imposible o con un monto
que se sale de lo habitual quede afuera del número y señalada, para no decidir sobre un total que
arrastra basura.

**Cómo se prueba que anda:** las ventas sin total, las que tienen fecha 31/02/2025 y las que tienen
un monto muy por encima de lo habitual para su producto no entran en ningún indicador, y aparecen en
la pantalla de revisión con el motivo por el que se apartaron.

### H4 — Cada número dice qué dejó afuera
Como **dueño**, quiero que junto a cada número me diga cuántos registros excluyó y pueda ir a
verlos, para saber cuánta confianza tenerle.

**Cómo se prueba que anda:** al lado del total de un mes se lee cuántas ventas quedaron excluidas, y
haciendo un clic se ve cuáles son.

### H5 — Decidir sobre las repetidas
Como **Julián**, quiero ver las dos versiones de una venta repetida lado a lado y decidir cuál vale,
para que el sistema no elija por mí cuando no hay forma honesta de saberlo.

**Cómo se prueba que anda:** se abre uno de los casos con cantidades distintas, se ven las dos
versiones enfrentadas, se elige una, el total del mes se recalcula incluyéndola, la versión
descartada se sigue viendo, y la decisión se puede deshacer.

### H6 — Cómo se movieron los precios, el stock y las altas
Como **Julián**, quiero ver cómo evolucionaron los precios del proveedor, cuánto se movió el stock y
qué productos son nuevos, para entender el movimiento del negocio más allá de la facturación.

**Cómo se prueba que anda:** el tablero muestra la evolución de los precios del proveedor, cuánto
stock había al inicio y al final del período con los productos que quedaron en cero señalados, y los
productos dados de alta, cada corte con su propio período elegible.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe obtener del portal los registros de ventas con la frecuencia configurada. | H1 |
| RF-02 | Cuando el sistema obtenga un registro de venta, debe conservarlo tal como llegó del portal. | H1 |
| RF-03 | El sistema debe mostrar el total facturado por mes desde 2023. | H1 |
| RF-04 | El sistema debe calcular los indicadores del tablero únicamente con las ventas que no están apartadas. | H1 |
| RF-05 | El sistema debe permitir elegir el período de cada corte del tablero por separado, sin que eso cambie el período de los demás. | H1 |
| RF-06 | El sistema debe mostrar la cantidad de ventas registradas en el período elegido. | H1 |
| RF-07 | El sistema debe mostrar el total facturado, con la cantidad de registros que excluyó, como primer contenido del tablero. | H1 |
| RF-08 | El sistema debe impedir al rol compras el acceso al tablero y a las ventas. | H1 |
| RF-09 | Si dos o más ventas comparten el mismo código, entonces el sistema debe tratarlas como repetidas. | H2 |
| RF-10 | El sistema debe comparar los códigos de venta ignorando las diferencias de escritura que no cambian el código. | H2 |
| RF-11 | Si las ventas que comparten código no difieren en ningún dato, entonces el sistema debe contarlas una sola vez sin esperar una decisión humana. | H2 |
| RF-12 | Cuando el sistema unifique ventas repetidas idénticas, debe informar cuántas unificó. | H2 |
| RF-13 | Si las ventas que comparten código difieren en algún dato, entonces el sistema debe apartarlas hasta que una persona las resuelva. | H2 |
| RF-14 | El sistema debe mostrar cuántos grupos de ventas repetidas hay pendientes de resolver. | H2 |
| RF-15 | El sistema debe impedir que una venta apartada como repetida sume en un indicador. | H2 |
| RF-16 | Si una venta no tiene fecha, entonces el sistema debe apartarla. | H3 |
| RF-17 | Si la fecha de una venta no corresponde a un día que existe, entonces el sistema debe apartarla. | H3 |
| RF-18 | Si una venta no tiene total, entonces el sistema debe apartarla. | H3 |
| RF-19 | Si una venta tiene una cantidad negativa, entonces el sistema debe apartarla. | H3 |
| RF-20 | Si una venta referencia un producto que no existe, entonces el sistema debe apartarla. | H3 |
| RF-21 | Si el total de una venta se aleja de lo habitual para ese producto más de lo tolerado, entonces el sistema debe apartarla como monto atípico. | H3 |
| RF-22 | El sistema debe permitir configurar a partir de qué diferencia el total de una venta se considera atípico. | H3 |
| RF-23 | El sistema debe mostrar, para cada venta apartada, el motivo por el que se apartó. | H3 |
| RF-24 | El sistema debe impedir completar por suposición un dato faltante de una venta. | H3 |
| RF-25 | El sistema debe mostrar, junto a cada indicador, cuántos registros quedaron excluidos de su cálculo. | H4 |
| RF-26 | El sistema debe permitir ver, desde cada indicador, cuáles son los registros que excluyó. | H4 |
| RF-27 | Si un indicador no excluyó ningún registro, entonces el sistema debe informarlo. | H4 |
| RF-28 | El sistema debe mostrar cuántas ventas están apartadas en total. | H4 |
| RF-29 | El sistema debe permitir resolver las ventas apartadas al rol ventas y al dueño, y a nadie más. | H5 |
| RF-30 | El sistema debe mostrar las dos o más versiones de una venta repetida enfrentadas, con sus diferencias señaladas. | H5 |
| RF-31 | El sistema debe permitir elegir cuál de las versiones de una venta repetida es la válida. | H5 |
| RF-32 | El sistema debe permitir declarar que las versiones de una venta repetida son ventas distintas. | H5 |
| RF-33 | Cuando alguien resuelva una venta repetida, el sistema debe incluir en los indicadores lo que esa persona declaró válido. | H5 |
| RF-34 | Cuando una venta repetida quede resuelta, el sistema debe seguir mostrando la versión descartada junto a la elegida. | H5 |
| RF-35 | El sistema debe permitir deshacer la resolución de una venta repetida, y al hacerlo debe volver a dejarla pendiente y recalcular los indicadores. | H5 |
| RF-36 | Cuando alguien resuelva una venta apartada, el sistema debe registrar qué decidió, quién lo decidió y cuándo. | H5 |
| RF-37 | Cuando una venta apartada quede resuelta, el sistema debe dejar de mostrarla entre las pendientes de revisión. | H5 |
| RF-38 | El sistema debe permitir corregir la fecha, el total, la cantidad y el producto de una venta apartada. | H5 |
| RF-39 | Si el dato correcto de una venta no se puede conocer, entonces el sistema debe permitir cargar el valor que la persona estime, y debe señalar ese valor como estimado. | H5 |
| RF-40 | El sistema debe informar, junto a cada indicador, si alguno de los valores que lo componen es estimado. | H5 |
| RF-41 | Cuando alguien corrija o estime el dato de una venta, el sistema debe conservar el valor que informó el portal. | H5 |
| RF-42 | El sistema debe mostrar la evolución de los precios que informa el proveedor, en el período elegido para ese corte. | H6 |
| RF-43 | El sistema debe mostrar, para cada producto, cuánto stock había al inicio y cuánto al final del período elegido para ese corte. | H6 |
| RF-44 | El sistema debe señalar los productos que quedaron sin stock al final del período. | H6 |
| RF-45 | El sistema debe mostrar los productos dados de alta en el período elegido para ese corte. | H6 |
| RF-46 | El sistema debe informar, junto a cada uno de esos cortes, cuántos registros quedaron excluidos. | H6 |

## Reglas de negocio

- **Un número del tablero no miente por omisión.** Todo indicador declara cuántos registros dejó
  afuera, si alguno de sus valores es estimado, y permite ir a verlos. Un total sin esa aclaración
  es un total en el que no se puede confiar.
- **Lo dudoso no suma.** Una venta repetida con diferencias, o con un dato roto, queda afuera del
  número hasta que una persona decida qué hacer con ella. Es preferible un total que dice "faltan
  doce" a uno que está inflado y no lo dice.
- **Lo idéntico no necesita a una persona.** Cuando dos ventas comparten el código y no difieren en
  ningún dato, no hay nada que decidir: el sistema cuenta una sola y dice cuántas unificó. La
  decisión humana se reserva para donde hay una decisión de verdad.
- **Nada se descarta.** Ninguna venta se borra ni se corrige sola: queda apartada, contada y visible.
- **Cuando no hay forma honesta de elegir, el sistema no elige.** Ante dos versiones de la misma
  venta con cantidades distintas, muestra las dos enfrentadas y espera la decisión de una persona.
- **Un dato estimado se ve como estimado.** Cuando el valor correcto no se puede conocer, una
  persona carga el que estima, y todo número que lo use lo declara. Estimar no es saber, y el
  tablero no las confunde.
- **Una decisión se puede deshacer.** Resolver una repetida no es definitivo: la versión descartada
  queda a la vista, la decisión se revierte y los números se recalculan. Quien decide sin miedo a
  equivocarse decide más rápido.
- **Lo que informó el portal se conserva siempre.** Una corrección se muestra encima; el dato
  original queda para poder explicar cualquier diferencia.
- **El tablero se mira desde el primer día.** El histórico no se limpia antes de mostrarlo: el
  tablero arranca declarando cuántas ventas dejó afuera y por qué, y sus números mejoran a medida
  que la revisión avanza. Un tablero que se habilita recién cuando no queda nada pendiente es un
  tablero que no se ve nunca.
- **El tablero no es la fuente de nada.** Muestra lo que hay: si un número no cierra, se corrige el
  dato en su lugar, no el tablero.
- **El tablero comercial y las ventas no los ve compras.**
- **El tablero se construye al final por una razón.** Muestra datos que primero tienen que estar
  limpios: hacerlo antes sería mostrar prolijamente números que todavía no cierran.

## Criterios de aceptación

- [ ] **RF-01** — Sin que nadie lo dispare, las ventas nuevas del portal aparecen en el sistema.
- [ ] **RF-02** — De cualquier venta se puede recuperar lo que informó el portal.
- [ ] **RF-03** — El tablero muestra la facturación mes a mes desde 2023.
- [ ] **RF-04** — El total de un mes coincide con la suma a mano de sus ventas no apartadas.
- [ ] **RF-05** — Se cambia el período del corte de precios y la facturación sigue mostrando el suyo.
- [ ] **RF-06** — El tablero dice cuántas ventas hay en el período elegido.
- [ ] **RF-07** — Al abrir el tablero, sin desplazarse, se leen el total facturado y cuántas ventas quedaron excluidas.
- [ ] **RF-08** — Marcela no llega al tablero ni pegando su dirección.
- [ ] **RF-09** — Las ventas con el mismo código se reconocen como un grupo repetido.
- [ ] **RF-10** — Dos códigos que sólo difieren en cómo están escritos se reconocen como el mismo, y aparecen los 27 grupos, no 17.
- [ ] **RF-11** — Los grupos cuyas versiones no difieren en ningún dato —21 de los 27, según el relevamiento— se cuentan una sola vez sin que nadie intervenga.
- [ ] **RF-12** — El tablero dice cuántas ventas repetidas unificó solo.
- [ ] **RF-13** — Los 6 grupos con cantidades distintas quedan apartados y esperando una decisión.
- [ ] **RF-14** — La pantalla dice cuántos grupos de repetidas están pendientes.
- [ ] **RF-15** — El total del mes que tiene repetidas no las cuenta dos veces.
- [ ] **RF-16** — Las 3 ventas sin fecha quedan apartadas.
- [ ] **RF-17** — Las 3 ventas con fecha 31/02/2025 quedan apartadas.
- [ ] **RF-18** — Las 3 ventas sin total quedan apartadas.
- [ ] **RF-19** — Las 3 ventas con cantidad negativa quedan apartadas.
- [ ] **RF-20** — La venta que apunta a un producto inexistente queda apartada.
- [ ] **RF-21** — Con la tolerancia acordada, las 2 ventas con el total inflado diez veces quedan apartadas por monto atípico.
- [ ] **RF-22** — Cambiada la tolerancia, la cantidad de ventas apartadas por monto cambia en consecuencia.
- [ ] **RF-23** — Cada venta apartada muestra por qué se apartó.
- [ ] **RF-24** — Ninguna venta apartada aparece con un dato que el sistema haya completado.
- [ ] **RF-25** — Al lado del total de un mes se lee cuántas ventas quedaron excluidas.
- [ ] **RF-26** — Desde ese número se llega a la lista de las ventas excluidas.
- [ ] **RF-27** — Un mes sin ventas apartadas lo dice explícitamente.
- [ ] **RF-28** — El tablero dice cuántas ventas están apartadas en total.
- [ ] **RF-29** — Julián resuelve un caso y el dueño resuelve otro; Marcela no puede resolver ninguno.
- [ ] **RF-30** — Abierto un caso repetido, se ven las versiones enfrentadas con las diferencias marcadas.
- [ ] **RF-31** — Elegida una versión como válida, queda esa.
- [ ] **RF-32** — Declaradas como ventas distintas, las dos entran a los indicadores.
- [ ] **RF-33** — Resuelto el caso, el total del mes se recalcula.
- [ ] **RF-34** — En el caso ya resuelto se sigue viendo la versión que se descartó.
- [ ] **RF-35** — Deshecha la decisión, el caso vuelve a pendientes y el total del mes vuelve a su valor anterior.
- [ ] **RF-36** — Cada caso resuelto muestra qué se decidió, quién y cuándo.
- [ ] **RF-37** — Resuelto un caso, la pantalla de revisión tiene uno menos pendiente.
- [ ] **RF-38** — Julián carga la fecha que faltaba y la venta entra a los indicadores; lo mismo con el total, la cantidad y el producto.
- [ ] **RF-39** — Cargado un total estimado, la venta queda señalada como estimada.
- [ ] **RF-40** — El mes que incluye esa venta avisa que uno de sus valores es estimado.
- [ ] **RF-41** — Esa venta sigue mostrando que el portal la informó sin fecha.
- [ ] **RF-42** — El tablero muestra cómo evolucionaron los precios del proveedor en el período.
- [ ] **RF-43** — El corte de stock muestra, por producto, cuánto había al inicio y cuánto al final del período.
- [ ] **RF-44** — Los productos que terminaron el período sin stock aparecen señalados.
- [ ] **RF-45** — El tablero muestra los productos dados de alta en el período.
- [ ] **RF-46** — Cada uno de esos cortes dice cuántos registros excluyó.

## Fuera de alcance

- **Predicción de demanda o sugerencia automática de compra.** No se apoya un pronóstico sobre datos
  de ventas que todavía tienen repetidas sin resolver. Se puede reconsiderar cuando la revisión esté
  vacía y haya histórico limpio.
- **Que el sistema decida solo cuál de dos ventas repetidas es la válida** cuando tienen datos en
  conflicto. Muestra las dos y espera.
- **La evolución del precio de venta de la empresa, y su comparación con el del proveedor.** El
  origen publica el precio del proveedor y no el de venta: sostener esa comparación exigiría cargar
  los precios de venta a mano o deducirlos, y es trabajo permanente que hoy no se abre. Se puede
  reconsiderar cuando exista de dónde sacarlos.
- **El detalle de las entradas y salidas de stock.** El tablero compara cuánto había al inicio y
  cuánto al final del período; no reconstruye movimiento por movimiento, porque el origen no informa
  cada movimiento y deducirlos daría un número que nadie puede verificar.
- **Avisar fuera del sistema cuando aparecen ventas apartadas nuevas.** El tablero y la pantalla de
  revisión lo muestran al entrar. Los avisos por fuera son **P8 y P12**, tienen su propia feature y
  su canal todavía se está confirmando con el cliente: prometerlos acá sería comprometer dos veces
  lo mismo. Si más adelante el cliente quiere un resumen periódico de lo que quedó pendiente, se
  agrega ahí.
- **El gasto por rubro.** Es **P7 — El problema de los rubros**, y depende de una pregunta que sigue
  abierta.
- **La deuda con proveedores y el estado de los pagos.** Son **P4 y P5**, y no entran al tablero
  comercial: compras y ventas están separadas a propósito.
- **Márgenes, rentabilidad y costo de la mercadería vendida.** El origen no publica el costo de
  venta.
- **Exportar el tablero a una planilla o a un informe.** No se pidió.
- **Corregir una venta en el portal del proveedor.** El origen es de sólo lectura; la corrección vive
  del lado nuevo.
