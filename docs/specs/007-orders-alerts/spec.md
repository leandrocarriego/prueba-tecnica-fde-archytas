# Órdenes de compra y avisos — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Borrador · **Feature:** 007-orders-alerts · **Fecha:** 2026-08-28

<!-- `/approve-spec` completa Aprobada por y Fecha de aprobación, y pasa Estado a Aprobado. -->

## Problema

Resuelve **P6 — El problema de las compras que se pierden** y **P8 — El problema de los avisos que
nadie mira**.

Van juntos porque son el mismo problema con dos caras: **algo pasa y nadie se entera**. Una orden de
compra queda esperando y nadie la sigue; un reclamo del proveedor cae en una bandeja donde nadie
entra. En los dos casos el sistema tiene la información y el equipo no.

En palabras del cliente, sobre las órdenes: *"Cuando pedimos mercadería queda registrado el pedido,
pero después nadie lo sigue. No sé cuáles se recibieron, cuáles siguen esperando y cuáles quedaron
ahí sin que nadie las mire. Me pasa de pedir dos veces lo mismo porque nadie se acordaba del primer
pedido."*

Y sobre los avisos: *"El sistema tiene una bandeja donde caen mensajes: avisos de que algo está por
vencer, y reclamos de los propios proveedores cuando les debemos. El tema es que nadie entra ahí,
así que nos enteramos cuando el proveedor llama enojado. Todos los días entra alguno nuevo.
Necesitaríamos que eso nos llegue de alguna forma que lo veamos, y saber cuáles quedaron sin
resolver."*

**El problema no es la bandeja: es que la bandeja vive dentro de un sistema al que nadie entra.**
Por eso el aviso tiene que salir de la pantalla, no ser otra bandeja más.

El relevamiento midió qué hay: **40 órdenes de compra** —14 pendientes de envío, 5 enviadas, 10
confirmadas y 11 recibidas— y **64 mensajes** en la bandeja —27 de vencimiento próximo, 21 reclamos
de pago y 16 de stock bajo—, de los cuales **30 están sin leer**.

## Objetivo

Que ninguna orden de compra quede sin seguimiento y que ningún reclamo de proveedor se descubra
cuando el proveedor llama: el sistema sigue el estado de cada pedido, junta los mensajes de la
bandeja y hace llegar lo importante fuera del sistema, a un canal que el equipo sí mira.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El sistema | Trae del portal las órdenes de compra y los mensajes, detecta lo que quedó estancado y manda los avisos |
| Marcela — compras | Sigue las órdenes, resuelve las que quedaron sin proveedor identificado y los mensajes que le tocan, y recibe los avisos de reclamos y vencimientos |
| El dueño | Ve todo. Resuelve también las órdenes apartadas, recibe el resumen diario, ve qué quedó sin resolver y de quién es, y ajusta los valores con que trabaja la feature |
| Julián — ventas | No accede a las órdenes de compra ni a la bandeja de mensajes |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que las tres personas aceptan recibir los avisos en su teléfono personal.** El cliente
  eligió números personales por sobre un número del negocio, porque el aviso llega al teléfono que
  la persona ya mira.

- **Se acepta, como límite de esta feature, que a quien no quiera dar su teléfono personal no le
  llegue ningún aviso.** No hay un segundo canal ni un número del negocio que lo reemplace: esa
  persona se entera sólo si entra a la pantalla de mensajes, que es exactamente lo que hoy no pasa
  con la bandeja del portal. Dicho sin vueltas: **para esa persona, P8 — El problema de los avisos
  que nadie mira sigue abierto**, y cerrarlo exige acordar otro canal, que no forma parte de lo que
  se firma acá.

- **Se asume que los valores con que arranca esta funcionalidad son un punto de partida, no una
  decisión del cliente.** El cliente pidió que las órdenes paradas queden señaladas, que el aviso
  salga a un canal que el equipo sí mira y que los números se puedan ajustar. **No eligió estos
  números**: los 15 días para considerar estancada una orden, los 15 días de la ventana de pedido
  repetido, las 8:00 del resumen diario y la franja de lunes a viernes de 8:00 a 18:00. Tampoco
  eligió el reparto inicial de destinatarios —los reclamos y los vencimientos a compras, el resumen
  al dueño—. Los cinco los propone el relevamiento, y el dueño los cambia desde el panel de
  configuración del sistema el día que quiera.

## Historias de usuario

### H1 — Seguir cada pedido hasta que llega *(prioridad más alta)*
Como **Marcela**, quiero ver todas las órdenes de compra con su estado, para saber cuáles se
recibieron, cuáles siguen esperando y cuáles quedaron ahí.

**Cómo se prueba que anda:** se abre la pantalla de órdenes y están las cuarenta, agrupadas por
estado, y se puede pedir ver sólo las que siguen esperando.

### H2 — Las que quedaron ahí, señaladas
Como **dueño**, quiero que el sistema me marque las órdenes que llevan demasiado tiempo sin avanzar,
para mirar sólo esas en lugar de recorrer las cuarenta.

**Cómo se prueba que anda:** el primer día no hay ninguna orden señalada; quince días después
quedan señaladas exactamente las que no se movieron en ese lapso, y ninguna de las ya recibidas.

### H3 — Avisar si ya pedimos lo mismo
Como **Marcela**, quiero que el sistema me avise si aparece un pedido del mismo producto que ya le
hicimos al mismo proveedor hace poco, para no pedir dos veces lo mismo.

**Cómo se prueba que anda:** aparece un segundo pedido del mismo producto al mismo proveedor dentro
de los 15 días, y el sistema lo señala mostrando el pedido anterior.

### H4 — Los mensajes salen de la bandeja del portal
Como **Marcela**, quiero ver en mi sistema los mensajes que hoy caen en la bandeja del portal,
ordenados por tipo y con el proveedor identificado, para dejar de entrar a un lugar donde nadie
entra.

**Cómo se prueba que anda:** se abre la pantalla de mensajes y están los sesenta y cuatro,
separados entre reclamos de pago, avisos de vencimiento y avisos de stock, cada uno con el
proveedor que lo mandó.

### H5 — Saber cuáles quedaron sin resolver y de quién son
Como **dueño**, quiero que cada mensaje tenga un estado y un responsable, para saber qué quedó
pendiente y quién lo tiene.

**Cómo se prueba que anda:** se asigna un reclamo a Marcela, ella lo marca resuelto, y la pantalla
pasa a mostrar un pendiente menos con el registro de quién lo resolvió.

### H6 — Que el aviso salga del sistema
Como **dueño**, quiero que los reclamos y los vencimientos le lleguen por WhatsApp a quien los tiene
que resolver, y recibir yo un resumen diario del resto, para que el equipo se entere sin tener que
acordarse de entrar a mirar y sin que suene el teléfono de madrugada.

**Cómo se prueba que anda:** entra un reclamo de pago un martes a las 10 y le llega el mensaje a
Marcela en el momento; el mismo reclamo entrado un sábado le llega el lunes a las 8; a la hora
configurada le llega al dueño un resumen con lo que quedó pendiente.

### H7 — Que no me avisen dos veces lo mismo
Como **Marcela**, quiero que un mensaje del que ya me enteré no me vuelva a avisar, para que el
canal siga sirviendo en lugar de convertirse en ruido que se ignora.

**Cómo se prueba que anda:** el mismo reclamo se procesa tres veces y llega un solo aviso inmediato;
una vez marcado como resuelto, deja de aparecer en el resumen diario.

### H8 — La orden que quedó sin proveedor se resuelve una sola vez y vuelve a la lista
Como **Marcela**, quiero decir a qué proveedor del padrón corresponde una orden que el sistema no
pudo identificar, para que vuelva a contarse con las demás en lugar de quedar en un limbo **y para
no tener que decidir dos veces lo mismo**.

**Cómo se prueba que anda:** llega una orden con el nombre del proveedor escrito de una forma que el
sistema no reconoce; queda en la lista señalada como sin identificar y contada aparte. Marcela pide
ver sólo esas, le asigna uno de los ocho proveedores del padrón, y la orden queda con ese proveedor,
con el nombre de quien lo decidió y la fecha, y deja de figurar entre las apartadas. Las otras
órdenes que estaban apartadas con el nombre escrito de esa misma forma quedan resueltas con esa
misma decisión, y la orden que llegue después escrita así entra ya identificada, sin pasar por
revisión.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe obtener del portal las órdenes de compra con la frecuencia configurada. | H1 |
| RF-02 | El sistema debe mostrar cada orden de compra con su proveedor, su fecha, su monto y su estado. | H1 |
| RF-03 | El sistema debe mostrar en qué estado está cada orden dentro del recorrido que va del pedido a la recepción. | H1 |
| RF-04 | Cuando una orden cambie de estado en el portal, el sistema debe actualizar su estado. | H1 |
| RF-05 | El sistema debe mostrar, para cada orden, desde cuándo la viene observando en su estado actual. | H1 |
| RF-06 | El sistema debe permitir filtrar las órdenes de compra por estado y por proveedor. | H1 |
| RF-07 | El sistema debe mostrar cuántas órdenes hay en cada estado. | H1 |
| RF-08 | Si el proveedor de una orden de compra no se puede identificar con certeza, entonces el sistema debe apartarla para revisión. | H1 |
| RF-09 | El sistema debe impedir al rol ventas el acceso a las órdenes de compra. | H1 |
| RF-10 | El sistema debe señalar como estancada toda orden que, en un estado anterior a la recepción, lleve observada en ese estado más días que el límite configurado. | H2 |
| RF-11 | El sistema debe tomar el límite de días de estancamiento del panel de configuración del sistema, cuyo valor inicial es de 15 días. | H2 |
| RF-12 | El sistema debe permitir mostrar únicamente las órdenes estancadas. | H2 |
| RF-13 | El sistema debe mostrar cuántas órdenes están estancadas. | H2 |
| RF-14 | Cuando una orden estancada avance de estado, el sistema debe dejar de señalarla como estancada. | H2 |
| RF-15 | Si aparece una orden por un producto que ya se le pidió al mismo proveedor dentro de la ventana configurada, entonces el sistema debe señalarla como posible pedido repetido. | H3 |
| RF-16 | El sistema debe mostrar, junto a una orden señalada como posible pedido repetido, la orden anterior con la que coincide. | H3 |
| RF-17 | El sistema debe tomar la ventana de días de pedido repetido del panel de configuración del sistema, cuyo valor inicial es de 15 días. | H3 |
| RF-18 | El sistema debe permitir al dueño y al rol compras descartar el señalamiento de pedido repetido. | H3 |
| RF-19 | El sistema debe registrar quién descartó un señalamiento de pedido repetido y cuándo. | H3 |
| RF-20 | El sistema debe impedir que un señalamiento de pedido repetido bloquee el registro de la orden. | H3 |
| RF-21 | El sistema debe obtener del portal los mensajes de la bandeja de modo que entre la aparición de un mensaje y su obtención no pase más de una hora. | H4 |
| RF-22 | El sistema debe clasificar cada mensaje según su tipo. | H4 |
| RF-23 | El sistema debe identificar al proveedor que envía cada mensaje contra el padrón de proveedores. | H4 |
| RF-24 | Si el proveedor que envía un mensaje no se puede identificar con certeza, entonces el sistema debe mostrar el mensaje señalando que su remitente quedó sin identificar. | H4 |
| RF-25 | Si el tipo de un mensaje no se puede determinar, entonces el sistema debe mostrarlo como sin clasificar en lugar de descartarlo. | H4 |
| RF-26 | El sistema debe permitir filtrar los mensajes por tipo, por proveedor y por estado. | H4 |
| RF-27 | El sistema debe asignar a cada mensaje el estado pendiente al momento de obtenerlo. | H5 |
| RF-28 | El sistema debe permitir al dueño y al rol compras marcar un mensaje como resuelto. | H5 |
| RF-29 | Cuando alguien marque un mensaje como resuelto, el sistema debe registrar quién lo resolvió y cuándo. | H5 |
| RF-30 | El sistema debe permitir asignar como responsable de un mensaje al dueño o a una persona del rol compras. | H5 |
| RF-31 | El sistema debe mostrar cuántos mensajes están pendientes. | H5 |
| RF-32 | El sistema debe permitir al dueño y al rol compras escribir una nota sobre un mensaje. | H5 |
| RF-33 | Cuando entre, dentro de la franja de avisos, un mensaje clasificado como reclamo de pago, el sistema debe avisar por WhatsApp en el momento a quien tenga configurado ese tipo de aviso. | H6 |
| RF-34 | Cuando entre, dentro de la franja de avisos, un mensaje clasificado como vencimiento próximo, el sistema debe avisar por WhatsApp en el momento a quien tenga configurado ese tipo de aviso. | H6 |
| RF-35 | El sistema debe enviar por WhatsApp, a la hora configurada, un resumen de los mensajes pendientes y de las órdenes estancadas. | H6 |
| RF-36 | El sistema debe tomar la hora del resumen diario del panel de configuración del sistema, cuyo valor inicial es las 8:00. | H6 |
| RF-37 | El sistema debe permitir al dueño definir quién recibe cada tipo de aviso, con los reclamos y los vencimientos hacia el rol compras y el resumen diario hacia el dueño como valores iniciales. | H6 |
| RF-38 | Si un aviso no se puede entregar, entonces el sistema debe registrar el fallo y señalarlo en la pantalla de mensajes. | H6 |
| RF-39 | Mientras un mensaje siga siendo el mismo, el sistema debe enviar un solo aviso inmediato por él. | H7 |
| RF-40 | Si un mensaje está marcado como resuelto, entonces el sistema no debe incluirlo en el resumen diario. | H7 |
| RF-41 | Mientras una orden siga estancada, el sistema debe incluirla en el resumen diario una vez por día como máximo. | H7 |
| RF-42 | Si la causa de un aviso inmediato entra fuera de la franja de avisos, entonces el sistema debe enviar ese aviso al comenzar la franja siguiente. | H6 |
| RF-43 | El sistema debe tomar la franja horaria de avisos inmediatos del panel de configuración del sistema, cuyo valor inicial es de lunes a viernes de 8:00 a 18:00. | H6 |
| RF-44 | El sistema debe enviar cada aviso al número de WhatsApp registrado para la persona que lo recibe. | H6 |
| RF-45 | Cuando una persona pierda el acceso al sistema, el sistema debe dejar de enviarle avisos. | H6 |
| RF-46 | El sistema debe impedir al rol ventas el acceso a la bandeja de mensajes. | H4 |
| RF-47 | El sistema debe registrar como pendientes los mensajes que ya estaban en la bandeja del portal al ponerse en marcha, sin enviar ningún aviso por ellos. | H7 |
| RF-48 | Cuando el sistema observe una orden en un estado distinto del que tenía registrado, debe registrar la fecha de esa observación. | H2 |
| RF-49 | El sistema debe mostrar, para cada orden anterior a su puesta en marcha, cuántos días pasaron desde la fecha del pedido. | H1 |
| RF-50 | Mientras el proveedor de una orden no esté identificado, el sistema debe mostrarla en la lista con el nombre del proveedor tal como llegó escrito y señalada como sin identificar. | H1 |
| RF-51 | El sistema debe mostrar cuántas órdenes de compra están apartadas para revisión. | H8 |
| RF-52 | El sistema debe permitir mostrar únicamente las órdenes apartadas para revisión. | H8 |
| RF-53 | El sistema debe habilitar únicamente al dueño y al rol compras a resolver una orden apartada. | H8 |
| RF-54 | Cuando el dueño o el rol compras asigne a una orden apartada un proveedor del padrón, el sistema debe asociarla a ese proveedor. | H8 |
| RF-55 | Si una orden corresponde a un proveedor que no está en el padrón, entonces el sistema debe apartarla indicando ese motivo, sin dar de alta un proveedor ni permitir darlo de alta desde la revisión. | H8 |
| RF-56 | Cuando alguien resuelva una orden apartada, el sistema debe registrar quién la resolvió y cuándo. | H8 |
| RF-57 | Cuando una orden apartada quede resuelta, el sistema debe dejar de mostrarla entre las apartadas para revisión. | H8 |
| RF-58 | Si una orden trae una forma de escribir el nombre del proveedor ya asignada a un proveedor del padrón, entonces el sistema debe asociarla a ese proveedor sin apartarla. | H8 |
| RF-59 | Mientras el proveedor de una orden no esté identificado, el sistema no debe señalarla como posible pedido repetido. | H3 |
| RF-60 | Cuando una orden apartada quede resuelta, el sistema debe evaluar si repite un pedido anterior al proveedor que se le asignó. | H3 |
| RF-61 | Cuando el dueño o el rol compras asigne a una orden apartada un proveedor del padrón, el sistema debe guardar esa forma de escribir el nombre como criterio. | H8 |
| RF-62 | Cuando esa asignación quede guardada, el sistema debe aplicarla también a las órdenes ya apartadas que traían esa misma forma de escribir el nombre. | H8 |

## Reglas de negocio

- **El aviso sale del sistema o no sirve.** La bandeja del portal ya demostró que una pantalla a la
  que hay que acordarse de entrar no se mira. Por eso lo importante llega a un canal de afuera, y la
  pantalla de mensajes es el lugar donde se resuelve, no donde uno se entera.
- **El canal es WhatsApp, a los teléfonos de cada persona.** Es donde el equipo ya mira, y por eso
  el que más chance tiene de que el aviso se vea de verdad. Un aviso a un número compartido vuelve a
  ser de todos y de nadie, que es exactamente lo que le pasa hoy a la bandeja.
- **Dos urgencias, dos ritmos.** Un reclamo de un proveedor y un vencimiento próximo avisan en el
  momento; el resto se junta en un resumen diario. Avisar todo con la misma urgencia es no avisar
  nada.
- **Lo urgente le llega a quien lo resuelve; la foto diaria, al dueño.** Los reclamos y los
  vencimientos van a compras, que es quien los trabaja; el resumen va al dueño, que es quien
  necesita saber qué quedó sin resolver.
- **El aviso urgente no suena de madrugada.** Fuera de la franja acordada el aviso espera al
  comienzo de la siguiente. Un canal que despierta a alguien por algo que se resuelve a las 9 se
  silencia, y silenciado deja de existir.
- **La franja es de los avisos inmediatos.** El resumen diario sale a su hora configurada, todos los
  días, y no la espera: son dos avisos distintos, con dos valores distintos, y el dueño ajusta cada
  uno por su lado. Consecuencia a tener presente: un reclamo que entra fuera de la franja no suena
  en el momento, pero figura entre los pendientes del resumen siguiente.
- **Un aviso inmediato no se repite mientras la causa siga siendo la misma.** El mismo reclamo genera
  un aviso inmediato, no uno por cada vez que el sistema lo procesa. Un canal que repite se silencia,
  y silenciado deja de existir. Lo que sí se repite, por diseño, es el resumen: mientras algo siga
  pendiente se cuenta ahí, una vez por día.
- **El reloj del estancamiento es del sistema, no del portal.** El sistema viejo dice en qué estado
  está una orden, pero no desde cuándo. Así que el tiempo se cuenta desde que el sistema lo ve por
  sí mismo: el día uno no hay nada señalado, y a los quince días aparece lo que de verdad no se
  movió. Contar desde la fecha del pedido señalaría las veintinueve órdenes en curso el primer día,
  y señalar todo es no señalar nada.
- **Lo que viene del sistema viejo se ve, pero no grita.** Las órdenes anteriores a la puesta en
  marcha —algunas de más de doscientos días— se listan con su antigüedad a la vista para que el
  equipo decida cuáles siguen vivas. Es el mismo criterio que con los treinta mensajes sin leer.
- **Un pedido es un producto.** Así los registra el sistema viejo, y por eso el aviso de pedido
  repetido puede comparar producto contra producto sin que nadie cargue nada a mano.
- **Una orden recibida ya llegó y no se estanca.** El señalamiento existe para las órdenes que
  siguen esperando; marcar las once ya recibidas sería ruido desde el primer día.
- **El sistema avisa, no bloquea.** Un pedido que parece repetido se señala mostrando el anterior; la
  decisión de pedirlo igual es del negocio.
- **Nada se descarta.** Un mensaje cuyo tipo no se puede determinar, o cuyo remitente no se puede
  identificar, se muestra como tal: no se esconde en un cajón de "otros" ni se tira.
- **Una orden sin proveedor tampoco se descarta ni se adivina.** Si el nombre no alcanza para decir
  con certeza de quién es, la orden entra igual y queda apartada: se ve en la lista con el nombre tal
  como llegó, se cuenta aparte y espera a que una persona diga a cuál de los ocho proveedores
  corresponde. Es el mismo criterio con el que ya se tratan las facturas.
- **La orden apartada se resuelve donde se la mira.** No hay una bandeja aparte: se la pide desde la
  misma lista de órdenes, se le asigna el proveedor y vuelve a contarse con las demás, quedando
  registrado quién lo decidió y cuándo. La resuelven el dueño y compras, que son quienes trabajan
  las órdenes.
- **Resolver una orden no da de alta un proveedor.** El padrón son los ocho del portal; si la orden
  es de alguien que no está, queda apartada con ese motivo hasta que sumar un proveedor se decida
  como lo que es: una decisión del negocio.
- **Una decisión sobre una forma de escribir un nombre se toma una sola vez y sirve para todo.**
  Resolver una orden apartada no arregla sólo esa orden: la decisión queda guardada como criterio,
  alcanza a las otras órdenes que estaban apartadas escritas de esa misma forma, y la que llegue
  después escrita así entra identificada sin que nadie vuelva a preguntar. Es el mismo criterio con
  el que ya se resuelven las facturas. Sin esto la cuenta no cierra: el relevamiento midió veinte
  formas distintas de escribir el nombre del proveedor sólo en las órdenes de compra, y decidir la
  misma una y otra vez es exactamente la cola de revisión que un equipo de tres personas termina
  abandonando.
- **Mientras no se sepa de quién es una orden, no se la compara con ninguna otra.** Un pedido
  repetido se mide contra el mismo proveedor: sin proveedor no hay con qué comparar, y señalarla
  igual sería adivinar. Resuelta la orden, la comparación se hace y el señalamiento aparece si
  corresponde.
- **Cada pendiente tiene un dueño.** Un mensaje sin responsable es un mensaje que nadie va a
  resolver: por eso el estado y el responsable son parte del mensaje, no una anotación aparte.
- **Resolver un caso tiene que costar segundos.** Si revisar cada mensaje cuesta trabajo, el equipo
  deja de entrar — que es exactamente lo que ya pasó con la bandeja del portal.
- **El sistema no le contesta al proveedor.** Los mensajes se leen del portal y se resuelven del lado
  nuevo; el portal es de sólo lectura y por él no sale nada.
- **Los valores ajustables de esta feature viven en el panel de configuración del sistema**, junto a
  los del resto: los días para considerar estancada una orden, la ventana de pedido repetido, la
  hora del resumen diario y la franja en la que puede sonar un aviso. No hay valores escondidos en
  las pantallas de órdenes ni de mensajes.
- **Ni las órdenes de compra ni la bandeja de mensajes las ve ventas**, tampoco los mensajes de
  stock bajo.

## Criterios de aceptación

- [ ] **RF-01** — Sin que nadie lo dispare, las órdenes nuevas del portal aparecen en el sistema.
- [ ] **RF-02** — Cada orden se lee con proveedor, fecha, monto y estado.
- [ ] **RF-03** — Se ve en qué punto del recorrido está cada orden, del pedido a la recepción.
- [ ] **RF-04** — Una orden que pasa a recibida en el portal aparece como recibida en el sistema.
- [ ] **RF-05** — Cada orden muestra desde cuándo el sistema la viene viendo en el estado en que está.
- [ ] **RF-06** — Se pueden pedir las órdenes pendientes de un proveedor y salen sólo esas.
- [ ] **RF-07** — La pantalla dice cuántas hay en cada estado, y coincide con el conteo a mano.
- [ ] **RF-08** — Una orden cuyo proveedor no se reconoce queda apartada, no asignada al que más se le parece.
- [ ] **RF-09** — Julián no llega a la pantalla de órdenes ni pegando su dirección.
- [ ] **RF-10** — Con el límite en 15 días, queda señalada la orden que el sistema viene viendo hace 16 en el mismo estado y no la que lleva 14; una recibida hace 200 días no queda señalada. El día de la puesta en marcha no hay ninguna señalada.
- [ ] **RF-11** — Recién instalado y sin que nadie toque nada, una orden se considera estancada a los 15 días; el dueño cambia ese valor en el panel del sistema y cambia qué órdenes quedan señaladas.
- [ ] **RF-12** — Se pueden pedir sólo las órdenes estancadas.
- [ ] **RF-13** — La pantalla dice cuántas órdenes están estancadas.
- [ ] **RF-14** — Una orden estancada que avanza deja de estar señalada.
- [ ] **RF-15** — Aparecido un segundo pedido del mismo producto al mismo proveedor dentro de la ventana, queda señalado; el mismo producto a otro proveedor, no.
- [ ] **RF-16** — Ese señalamiento muestra cuál era el pedido anterior.
- [ ] **RF-17** — Recién instalado, dos pedidos separados por 14 días quedan señalados y dos separados por 16 no; el dueño cambia la ventana en el panel del sistema y cambia el resultado.
- [ ] **RF-18** — Marcela descarta el señalamiento y la orden deja de aparecer como repetida.
- [ ] **RF-19** — Ese descarte figura con su nombre y la fecha.
- [ ] **RF-20** — La orden señalada como repetida está igual en la lista, con su estado y su seguimiento.
- [ ] **RF-21** — Un mensaje que aparece en la bandeja del portal está en el sistema antes de que pase una hora.
- [ ] **RF-22** — Los sesenta y cuatro mensajes quedan separados por tipo, y los conteos coinciden con el relevamiento.
- [ ] **RF-23** — Cada mensaje muestra a qué proveedor del padrón corresponde su remitente.
- [ ] **RF-24** — Un mensaje cuyo remitente no se reconoce se muestra igual, señalando que el remitente quedó sin identificar.
- [ ] **RF-25** — Un mensaje de un tipo desconocido aparece como sin clasificar, no desaparece.
- [ ] **RF-26** — Se pueden pedir los reclamos pendientes de un proveedor y salen sólo esos.
- [ ] **RF-27** — Un mensaje recién traído figura como pendiente.
- [ ] **RF-28** — Marcela marca un reclamo como resuelto y deja de figurar entre los pendientes.
- [ ] **RF-29** — Ese mensaje muestra quién lo resolvió y cuándo.
- [ ] **RF-30** — Un mensaje se puede asignar al dueño o a Marcela y muestra su nombre; Julián no figura entre los asignables.
- [ ] **RF-31** — La pantalla dice cuántos mensajes están pendientes.
- [ ] **RF-32** — Se puede dejar una nota en un mensaje y queda visible con su autor.
- [ ] **RF-33** — Entra un reclamo de pago un martes a las 10 y llega el aviso al WhatsApp de Marcela en el momento.
- [ ] **RF-34** — Entra un aviso de vencimiento próximo dentro de la franja y llega el aviso al WhatsApp en el momento.
- [ ] **RF-35** — A la hora configurada llega un resumen con los pendientes y las órdenes estancadas.
- [ ] **RF-36** — Recién instalado, el resumen sale a las 8:00; el dueño cambia la hora en el panel del sistema y el resumen siguiente llega a la hora nueva.
- [ ] **RF-37** — Sin que nadie configure nada, los reclamos y los vencimientos llegan a compras y el resumen al dueño; el dueño cambia los destinatarios y los avisos siguientes llegan a quien indicó.
- [ ] **RF-38** — Fallado el envío de un aviso, queda registrado y se ve en la pantalla de mensajes.
- [ ] **RF-39** — El mismo reclamo procesado tres veces genera un solo aviso inmediato.
- [ ] **RF-40** — Un mensaje resuelto no aparece en el resumen del día siguiente.
- [ ] **RF-41** — Una orden estancada cinco días aparece en cinco resúmenes, uno por día, y no cinco veces en el mismo.
- [ ] **RF-42** — Un reclamo que entra el sábado a las 22 no suena el sábado: el aviso llega el lunes a las 8.
- [ ] **RF-43** — Recién instalado, la franja va de lunes a viernes de 8:00 a 18:00; el dueño la cambia en el panel del sistema y cambia cuándo suenan los avisos.
- [ ] **RF-44** — El aviso llega al número registrado de la persona que corresponde, y no al de otra.
- [ ] **RF-45** — Dada de baja una persona del sistema, el aviso siguiente no le llega.
- [ ] **RF-46** — Julián no llega a la pantalla de mensajes ni pegando su dirección, ni ve los mensajes de stock bajo.
- [ ] **RF-47** — El primer día los treinta mensajes sin leer figuran como pendientes y no se envió ningún aviso por ellos.
- [ ] **RF-48** — Una orden que pasa de enviada a confirmada queda con la fecha en que el sistema vio el cambio, y su antigüedad en el estado vuelve a cero.
- [ ] **RF-49** — Las veintinueve órdenes en curso que vienen del sistema viejo se listan mostrando su antigüedad, sin quedar señaladas el primer día.
- [ ] **RF-50** — Una orden apartada sigue en la lista, con el nombre del proveedor tal como vino y la marca de que quedó sin identificar.
- [ ] **RF-51** — La pantalla dice cuántas órdenes están apartadas para revisión.
- [ ] **RF-52** — Se pueden pedir sólo las órdenes apartadas.
- [ ] **RF-53** — Julián no puede resolver una orden apartada; el dueño y Marcela sí.
- [ ] **RF-54** — Marcela le asigna a una orden apartada uno de los ocho proveedores del padrón y la orden queda con ese proveedor.
- [ ] **RF-55** — Una orden a nombre de alguien que no está en el padrón no crea un proveedor nuevo ni deja darlo de alta desde la revisión: queda apartada, y el motivo dice que el proveedor no está en el padrón.
- [ ] **RF-56** — Esa orden resuelta figura con el nombre de quien la resolvió y la fecha.
- [ ] **RF-57** — Resuelta una orden, la lista de apartadas tiene una menos.
- [ ] **RF-58** — Asignada ya una forma de escribir el nombre a un proveedor, la orden siguiente que llegue escrita así entra con ese proveedor y sin pasar por revisión.
- [ ] **RF-59** — Una orden apartada no aparece señalada como posible pedido repetido de ninguna otra.
- [ ] **RF-60** — Resuelta una orden apartada, si ese mismo producto ya se le había pedido a ese proveedor dentro de la ventana, queda señalada como posible pedido repetido mostrando el pedido anterior.
- [ ] **RF-61** — Asignado un proveedor a una orden apartada, esa forma de escribir el nombre queda guardada como criterio.
- [ ] **RF-62** — Con tres órdenes apartadas que traían el nombre escrito igual, resuelta una las tres quedan con ese proveedor y la lista de apartadas tiene tres menos.

## Fuera de alcance

- **Registrar un pedido nuevo desde este sistema.** Los pedidos se hacen en el sistema viejo, que es
  de un tercero y de sólo lectura; acá se siguen. Como consecuencia, el aviso de pedido repetido
  llega cuando el pedido aparece en el sistema, no mientras alguien lo está escribiendo.
- **Contestar un mensaje o un reclamo desde el sistema.** El portal es de sólo lectura: el reclamo se
  resuelve por fuera y acá se registra que se resolvió.
- **El detalle de artículos de cada orden de compra más allá de lo que publica el portal.**
- **Los avisos de vencimiento de facturas sin recibo.** Comparten canal con esta feature, pero se
  definen en **P12 — El problema de los recibos**.
- **Los avisos de stock bajo hacia afuera.** Los mensajes de stock entran a la bandeja y se ven, pero
  no generan aviso por WhatsApp: el cliente pidió que salieran del sistema los reclamos y los
  vencimientos.
- **Un canal de aviso que no sea WhatsApp al teléfono de cada persona.** Ni un número del negocio,
  ni correo, ni un mensaje a un grupo. Quien no dé su teléfono no recibe avisos y sigue enterándose
  sólo si entra a mirar: es un límite acordado de esta feature, no algo que quede para después.
- **La pantalla donde el dueño ajusta los valores de esta feature.** Los cuatro parámetros se
  publican en el panel de configuración del sistema, que se define en **P9 — El problema de no
  tener control**.
- **Un tablero de compras por proveedor o por rubro.** Eso es **P7** y **P3**.
- **Dar de alta un proveedor nuevo desde la revisión de una orden.** El padrón es el del portal
  —ocho proveedores, confirmados por el cliente—; una orden a nombre de alguien que no está queda
  apartada con ese motivo, y sumar un proveedor se decide aparte, igual que en **P2 y P4 — Las
  facturas y los proveedores**.
- **Asignarle un responsable a una orden apartada.** El responsable existe para los mensajes, que
  entran de a uno todos los días; las órdenes apartadas las trabajan el dueño y compras desde la
  misma lista, sin repartirlas de a una.

## Preguntas abiertas

<!--
  Ninguna de estas frena la firma: no hay marcadores de aclaración pendientes en el documento.
  Es la lista de lo que se decidió con lo ya acordado para poder cerrarlo, puesta a la vista.
-->

### Para confirmar al firmar

Estas cosas se decidieron con lo que ya está acordado en otro lado o con lo que el sistema ya hace,
para que la spec quede completa. **Ninguna la eligió el cliente**, y por eso están acá y no
escondidas en el cuerpo del documento: si alguna no es lo que quiere, se cambia antes de firmar.

- **Una orden cuyo proveedor no se puede identificar se resuelve asignándole uno de los ocho
  proveedores del padrón, y la resuelven el dueño y compras** (RF-53, RF-54). *De dónde sale:* es
  exactamente lo que se firmó para las facturas en **P2 y P4**, que es el mismo problema del mismo
  lado del negocio. *Si el cliente quiere otra cosa:* cambia quién puede resolverlas, no el
  mecanismo.

- **Resolver una orden apartada guarda esa forma de escribir el nombre como criterio, y con eso
  quedan resueltas de una vez las otras órdenes apartadas que venían escritas igual** (RF-61,
  RF-62). *De dónde sale:* del brief, que promete para la cola de revisión que *"cada decisión que
  toma una persona queda como criterio para que el mismo caso no se pregunte dos veces"*, y de lo ya
  firmado para las facturas en **P2 y P4**, donde son dos requisitos con esas mismas palabras. Es
  además lo único que produce las asignaciones que RF-58 ya da por existentes. *Consecuencia
  práctica que conviene mirar:* el criterio es uno solo para las facturas y las órdenes, así que una
  decisión tomada resolviendo una orden también identifica las facturas que estaban esperando esa
  misma forma de escribir el nombre, y al revés. *Lo que no se trajo de facturas:* ahí el sistema
  avisa, antes de guardar, a cuántas alcanza la decisión; acá la decisión se toma sobre una orden
  concreta y el efecto se ve al resolverla. Si se quiere también ese aviso previo en las órdenes,
  hay que pedirlo antes de firmar. *Si el cliente prefiere otra cosa:* que resolver una orden
  arregle sólo esa orden es sacar RF-61 y RF-62, y entonces la misma forma de escribir un nombre se
  decide orden por orden, veinte veces según lo que midió el relevamiento.

- **La orden apartada se resuelve desde la misma lista de órdenes, filtrando por las apartadas, y no
  en una pantalla de revisión aparte** (RF-50, RF-51, RF-52). *De dónde sale:* es como el sistema ya
  las muestra —la orden sigue en la lista, con el nombre tal como llegó— y responde a la advertencia
  del propio relevamiento: una cola que cuesta tiempo se abandona. *Si el cliente quiere otra cosa:*
  una pantalla propia es una pantalla más, no un alcance distinto.

- **Una orden apartada no lleva responsable asignado.** *De dónde sale:* en esta funcionalidad el
  responsable existe para los mensajes, que entran de a uno todos los días (RF-30), y las facturas
  apartadas tampoco lo llevan. *Si el cliente quiere otra cosa:* repartir también las órdenes de a
  una se agrega, y hay que decirlo antes de firmar.

- **Resolver una orden no da de alta un proveedor nuevo** (RF-55). *De dónde sale:* es la misma regla
  ya firmada para las facturas. *Si el cliente quiere otra cosa:* implica mover el padrón de ocho,
  que es una decisión del negocio y se conversa aparte.

- **Una orden apartada no se señala como posible pedido repetido, y sí se la evalúa cuando se
  resuelve** (RF-59, RF-60). *De dónde sale:* lo primero es lo que el sistema hace hoy —sin proveedor
  no hay contra qué comparar—; lo segundo es lo único que evita que esa orden pierda para siempre el
  aviso de H3, y sigue el criterio ya firmado en facturas de que una decisión alcanza también a lo
  que estaba esperando. *Si el cliente prefiere otra cosa:* que una orden resuelta tarde no vuelva a
  compararse es sacar RF-60.

- **El resumen diario sale todos los días a su hora, también sábado y domingo; la franja horaria rige
  sólo los avisos inmediatos** (RF-35, RF-42, RF-43). *De dónde sale:* es lo que dicen los tres
  requisitos leídos juntos, y lo que el sistema hace. *Consecuencia práctica que conviene mirar:* un
  reclamo que entra un sábado a la noche no suena en el momento —el aviso inmediato espera al
  lunes— pero aparece en el resumen del domingo a las 8:00. *Si el cliente prefiere otra cosa:* que
  el resumen respete la franja, o que no salga los fines de semana, hay que decidirlo antes de
  firmar.

- **Un mismo mensaje genera un solo aviso inmediato, pero se cuenta en el resumen todos los días
  hasta que alguien lo resuelve** (RF-39, RF-40). *De dónde sale:* es lo que ya decían RF-40 y RF-41
  y lo que el sistema hace; RF-39 decía "una sola vez" sin aclarar de qué aviso hablaba, y quedaba
  contradiciendo al resumen. *Si el cliente prefiere otra cosa:* que el resumen no repita lo que ya
  se avisó una vez es un cambio de alcance del resumen.
