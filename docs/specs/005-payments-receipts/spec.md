# Pagos y recibos de recepción — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Aprobado · **Feature:** 005-payments-receipts · **Fecha:** 2026-08-29
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-29

## Problema

Resuelve **P5 — El problema de los pagos a medias** y **P12 — El problema de los recibos**.

Van juntos porque son la misma factura mirada en dos momentos: cuando se la recibe y hay que emitir
su recibo, y cuando se la paga —entera o en pedazos— y hay que saber cuánto queda debiendo.

En palabras del cliente, sobre los pagos: *"Muchas veces no pagamos toda la factura junta: le damos
algo a cuenta y el resto más adelante. En el sistema eso queda registrado, pero yo no tengo manera
de ver de una cuáles están saldadas, cuáles van por la mitad y cuáles no se tocaron. Termino sumando
a mano y siempre me da distinto."*

Y sobre los recibos: *"Cuando una factura vence, tenemos que generarle un recibo al proveedor (no un
pago, un recibo: el comprobante de que la recibimos y va a ser pagada). Eso se puede generar en
cualquier momento hasta la fecha de vencimiento. El problema es que hoy, si a alguien se le pasa la
fecha, nadie se entera hasta que el proveedor llama preguntando: el sistema viejo no avisa nada."*

El relevamiento midió el tamaño del problema: de cada 100 facturas, **26 están pagadas, 41 pagadas a
medias y 33 sin tocar**; y **30 no tienen su recibo de recepción, de las cuales 17 ya están
vencidas**.

## Objetivo

Que el estado de pago de cada factura se vea de un vistazo y coincida con lo que el cliente
verifica a mano, y que ninguna factura se pase de su fecha de vencimiento sin su recibo de recepción
sin que el equipo se haya enterado antes.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El sistema | Trae del portal los comprobantes de pago y los recibos, los imputa a su factura, calcula el saldo, aparta lo que no puede resolver solo y avisa antes de que se pase una fecha |
| Marcela — compras | Ve el estado de cada factura, registra un pago a mano, reparte un pago que cubre varias facturas, emite el recibo de recepción y cierra lo que quedó señalado |
| El dueño | Ve todo. Consulta cuánto le debe a cada proveedor y hace cuánto. Define con cuánta anticipación avisa el sistema |
| Julián — ventas | No accede a los pagos ni a las cuentas de proveedores |

## Aclaración de vocabulario

<!-- Va en la spec a propósito: el cliente usó la palabra en un sentido preciso y el sistema tiene que distinguir las dos cosas. -->

El cliente usa **recibo** en un sentido puntual: *"no un pago, un recibo: el comprobante de que la
recibimos y va a ser pagada"*. Es el **recibo de recepción** de la factura, se emite hasta la fecha
de vencimiento, y **no** es el comprobante que se entrega al pagar. Las dos cosas existen en el
negocio y esta feature las trata como dos cosas distintas:

- **Recibo de recepción** — se emite al recibir la factura, hasta su fecha de vencimiento.
- **Comprobante de pago** — se registra al pagar, entero o a cuenta.

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que la numeración de los recibos la lleva el sistema, correlativa, sin huecos y
  arrancando en el primero que se emita.** El cliente decidió que el recibo sea un documento que
  genera el sistema; **no definió una serie ni un formato heredado**. Si el recibo que usan hoy en
  papel tiene su propia numeración, se conversa antes de emitir el primero.

- **Se asume que dos pagos son sospechosos de ser el mismo cuando corresponden a la misma factura y
  al mismo monto.** El cliente pidió que en ese caso el sistema pregunte en lugar de decidir; **con
  qué grado de parecido pregunta** es un criterio que se puede ajustar sin cambiar el acuerdo.

- **Se asume que un comprobante que cubre varias facturas cubre facturas de un mismo proveedor.** Es
  lo que muestran los comprobantes relevados. Si aparece uno que cruza dos proveedores, el sistema
  lo mantiene apartado y pregunta.

## Historias de usuario

### H1 — Saldada, a medias o sin tocar, de un vistazo *(prioridad más alta)*
Como **dueño**, quiero ver en la lista de facturas cuáles están saldadas, cuáles van por la mitad y
cuáles no se tocaron, para dejar de sumar a mano.

**Cómo se prueba que anda:** se abre la lista de facturas y cada una muestra su estado; se elige una
que está a medias y el saldo que muestra coincide con la cuenta hecha a mano.

### H2 — Los pagos se imputan solos
Como **Marcela**, quiero que los comprobantes de pago que ya existen queden pegados a su factura sin
que yo los cargue, para que el saldo esté siempre al día.

**Cómo se prueba que anda:** se deja andar el sistema y las facturas que tenían pagos registrados
aparecen con esos pagos listados y su saldo actualizado, sin que nadie cargue nada.

### H3 — Cuando los números no cierran, el sistema lo dice
Como **dueño**, quiero que si los pagos de una factura no coinciden con su total el sistema me lo
señale, en lugar de acomodar el número para que cierre.

**Cómo se prueba que anda:** llega una factura donde los pagos suman más que el total; la factura
queda señalada como inconsistente, con los dos números a la vista, y no se la cuenta como saldada.

### H4 — Registrar un pago a mano
Como **Marcela**, quiero registrar yo un pago que hicimos, para no esperar a que aparezca en el
sistema viejo cuando necesito el saldo hoy.

**Cómo se prueba que anda:** se registra un pago a cuenta sobre una factura sin tocar; la factura
pasa a estado parcial con el porcentaje pagado, y el pago figura con el nombre de quien lo cargó.

### H5 — Cuánto le debo a cada proveedor, y hace cuánto
Como **dueño**, quiero abrir un proveedor y ver cuánto le pagué, cuánto le debo, desde hace cuánto y
si le venimos pagando tarde contra el plazo que acordamos con él, para saber si le estamos
cumpliendo.

**Cómo se prueba que anda:** se abre un proveedor con plazo de 30 días, y la ficha muestra su deuda,
cuánto de esa deuda tiene más de 30, 60 y 90 días contados desde el vencimiento, y cuántos días en
promedio se le paga tarde.

### H6 — Qué facturas ya tienen su recibo y cuáles no
Como **Marcela**, quiero ver cuáles facturas ya tienen emitido su recibo de recepción y cuáles
todavía no, para saber qué me falta hacer.

**Cómo se prueba que anda:** en la lista de facturas se distingue a simple vista cuál tiene recibo y
cuál no, y se pueden pedir sólo las que no lo tienen.

### H7 — Emitir el recibo, hasta la fecha y no después
Como **Marcela**, quiero emitir el recibo de recepción de una factura desde el sistema y poder
descargarlo para mandárselo al proveedor, y que el sistema no me deje emitirlo pasada la fecha de
vencimiento, porque después de esa fecha ya no corresponde.

**Cómo se prueba que anda:** se emite el recibo de una factura que vence la semana que viene, queda
emitido con su número y se puede descargar; se intenta emitir el de una que venció ayer y el sistema
no lo permite, explicando por qué.

### H8 — Que avise antes de que se pase la fecha
Como **dueño**, quiero que el sistema avise por WhatsApp cuando se acerca el vencimiento de una
factura que sigue sin recibo, para enterarme antes y no cuando el proveedor llama preguntando.

**Cómo se prueba que anda:** configurada la anticipación en tres días, llega el aviso tres días antes
del vencimiento de una factura sin recibo —a compras y al dueño—, y no llega para las que ya lo
tienen.

### H9 — Un pago que cubre varias facturas
Como **Marcela**, quiero repartir yo el monto de un pago que cubrió varias facturas, para que el
saldo de cada una quede bien y el sistema no reparta por su cuenta.

**Cómo se prueba que anda:** llega un comprobante que referencia tres facturas; queda apartado sin
tocar ningún saldo hasta que Marcela reparte el monto entre las tres y el reparto suma exactamente
el monto del comprobante.

### H10 — Cerrar lo que se pasó de fecha
Como **Marcela**, quiero poder cerrar el incidente de una factura que se venció sin recibo,
explicando qué hicimos, para que la lista de pendientes muestre lo que de verdad falta hacer.

**Cómo se prueba que anda:** se cierra el incidente de una factura vencida indicando qué se hizo;
la factura deja de contarse entre los pendientes, el motivo queda a la vista con el nombre de quien
lo cerró, y el sistema sigue sin permitir emitirle el recibo.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe mostrar, para cada factura, si está saldada, parcialmente pagada o sin pagos. | H1 |
| RF-02 | El sistema debe mostrar, para cada factura, el monto pagado y el saldo pendiente. | H1 |
| RF-03 | El sistema debe mostrar, para cada factura parcialmente pagada, el porcentaje pagado. | H1 |
| RF-04 | El sistema debe permitir filtrar las facturas por su estado de pago. | H1 |
| RF-05 | El sistema debe permitir filtrar las facturas por proveedor y por fecha de vencimiento. | H1 |
| RF-06 | El sistema debe mostrar el estado de pago dentro de la propia factura. | H1 |
| RF-07 | El sistema debe obtener del portal los comprobantes de pago con la frecuencia configurada. | H2 |
| RF-08 | Cuando el sistema obtenga un comprobante de pago, debe conservarlo tal como llegó del portal. | H2 |
| RF-09 | Cuando el sistema obtenga un comprobante de pago, debe imputarlo a la factura que ese comprobante indica. | H2 |
| RF-10 | El sistema debe mostrar, dentro de una factura, todos los pagos imputados con su fecha y su monto. | H2 |
| RF-11 | Si un comprobante de pago referencia una factura que el sistema no tiene registrada, entonces el sistema debe apartarlo para revisión. | H2 |
| RF-12 | Si un comprobante de pago referencia más de una factura, entonces el sistema debe apartarlo para que una persona reparta el monto, en lugar de repartirlo por su cuenta. | H2 |
| RF-13 | Si un comprobante de pago llega dos veces, entonces el sistema debe imputarlo una sola vez. | H2 |
| RF-42 | Si un comprobante traído del portal coincide en factura y monto con un pago cargado a mano, entonces el sistema debe apartarlo para revisión en lugar de imputarlo. | H2 |
| RF-43 | Cuando una persona resuelva que un comprobante apartado y un pago cargado a mano son el mismo pago, el sistema debe conservar uno solo y registrar quién lo decidió y cuándo. | H2 |
| RF-44 | Cuando el sistema registre la factura que un comprobante apartado referencia, debe imputarle ese comprobante e informar que lo hizo. | H2 |
| RF-14 | Si los pagos imputados a una factura superan su total, entonces el sistema debe señalar la factura como inconsistente. | H3 |
| RF-15 | Si una factura queda señalada como inconsistente, entonces el sistema debe mostrar su total y la suma de sus pagos. | H3 |
| RF-16 | Si una factura queda señalada como inconsistente, entonces el sistema debe excluirla de los totales de deuda e informar que la excluyó. | H3 |
| RF-17 | El sistema debe impedir que una factura señalada como inconsistente figure como saldada. | H3 |
| RF-45 | El sistema debe determinar el estado de pago de una factura a partir de los pagos imputados, y no del estado que informe el portal. | H3 |
| RF-46 | Si el estado de pago que informa el portal no coincide con el que surge de los pagos imputados, entonces el sistema debe señalar la factura y mostrar los dos estados. | H3 |
| RF-18 | El sistema debe permitir al rol compras registrar un pago sobre una factura indicando su monto y su fecha. | H4 |
| RF-19 | Cuando alguien registre un pago a mano, el sistema debe registrar quién lo cargó y cuándo. | H4 |
| RF-20 | El sistema debe distinguir los pagos traídos del portal de los cargados a mano. | H4 |
| RF-21 | Si el monto de un pago cargado a mano supera el saldo de la factura, entonces el sistema debe advertirlo antes de registrarlo. | H4 |
| RF-22 | El sistema debe permitir al rol compras dejar sin efecto un pago cargado a mano. | H4 |
| RF-23 | El sistema debe impedir dejar sin efecto un pago traído del portal. | H4 |
| RF-24 | El sistema debe mostrar, para cada proveedor, el total pagado y el saldo adeudado. | H5 |
| RF-25 | El sistema debe mostrar, para cada proveedor, cómo se reparte su deuda por antigüedad, contada desde la fecha de vencimiento de cada factura. | H5 |
| RF-26 | El sistema debe calcular la fecha de vencimiento de una factura a partir del plazo de pago pactado con su proveedor, y no de ninguna otra fecha que traiga el documento. | H5 |
| RF-27 | El sistema debe mostrar, para cada proveedor, el promedio de días de atraso respecto de su plazo pactado, contando las facturas ya pagadas hasta el pago que las saldó y las impagas vencidas hasta hoy. | H5 |
| RF-28 | El sistema debe informar, junto a la deuda de un proveedor, cuántas facturas quedaron excluidas por estar en revisión o señaladas como inconsistentes. | H5 |
| RF-29 | El sistema debe mostrar, para cada factura, si su recibo de recepción está emitido. | H6 |
| RF-30 | El sistema debe obtener del portal los recibos de recepción ya emitidos. | H6 |
| RF-31 | El sistema debe permitir filtrar las facturas por si tienen o no su recibo de recepción emitido. | H6 |
| RF-32 | El sistema debe mostrar cuántas facturas están sin su recibo de recepción. | H6 |
| RF-33 | El sistema debe permitir al rol compras emitir el recibo de recepción de una factura. | H7 |
| RF-34 | Si la fecha de vencimiento vigente de una factura ya pasó, entonces el sistema debe impedir emitir su recibo de recepción e informar el motivo. | H7 |
| RF-35 | Si una factura ya tiene su recibo de recepción emitido, entonces el sistema debe impedir emitir otro. | H7 |
| RF-36 | Cuando alguien emita un recibo de recepción, el sistema debe registrar quién lo emitió y cuándo. | H7 |
| RF-37 | El sistema debe señalar como incidente toda factura vencida sin su recibo de recepción emitido. | H7 |
| RF-47 | Cuando alguien emita un recibo de recepción, el sistema debe generar su documento y permitir descargarlo. | H7 |
| RF-48 | Cuando el sistema emita un recibo de recepción, debe asignarle un número propio, correlativo y sin repetir. | H7 |
| RF-49 | El sistema debe permitir al rol compras anular un recibo de recepción emitido, registrando quién lo anuló y cuándo. | H7 |
| RF-50 | Si se anula el recibo de una factura cuya fecha de vencimiento vigente todavía no pasó, entonces el sistema debe permitir emitirle uno nuevo. | H7 |
| RF-51 | Si se anula el recibo de una factura cuya fecha de vencimiento vigente ya pasó, entonces el sistema debe señalarla como incidente. | H7 |
| RF-38 | Cuando falten para el vencimiento de una factura sin recibo los días de anticipación configurados, el sistema debe avisar por WhatsApp al rol compras y al dueño. | H8 |
| RF-39 | Mientras una factura siga sin su recibo de recepción, el sistema debe avisar una sola vez por vencimiento. | H8 |
| RF-40 | Si una factura tiene su recibo de recepción emitido, entonces el sistema no debe avisar por su vencimiento. | H8 |
| RF-41 | El sistema debe permitir al dueño definir con cuántos días de anticipación se avisa un vencimiento sin recibo. | H8 |
| RF-52 | Mientras el dueño no configure otro valor, el sistema debe avisar con tres días de anticipación. | H8 |
| RF-53 | El sistema debe permitir al rol compras repartir el monto de un comprobante que cubre varias facturas entre esas facturas. | H9 |
| RF-54 | Mientras el reparto de un comprobante no esté confirmado, el sistema debe mantenerlo apartado y no imputar ninguna de sus partes. | H9 |
| RF-55 | Si las partes de un reparto no suman exactamente el monto del comprobante, entonces el sistema debe impedir confirmarlo. | H9 |
| RF-56 | Cuando alguien reparta un comprobante entre varias facturas, el sistema debe registrar quién lo repartió y cuándo. | H9 |
| RF-57 | El sistema debe permitir al rol compras cerrar el incidente de una factura vencida sin recibo, indicando qué se hizo. | H10 |
| RF-58 | Cuando alguien cierre un incidente, el sistema debe registrar quién lo cerró, cuándo y el motivo que indicó. | H10 |
| RF-59 | Cuando se cierre un incidente, el sistema debe dejar de contarlo entre los pendientes y conservarlo consultable. | H10 |

## Reglas de negocio

- **El estado del pago vive en la factura, no en una lista aparte.** Si hubiera dos lugares que
  informan lo mismo, tarde o temprano dirían cosas distintas.
- **El estado de pago lo dicen los pagos, no el origen.** El sistema suma los comprobantes
  imputados; si el portal informa otra cosa, no gana el portal: se señala la diferencia con los dos
  datos a la vista.
- **Un recibo de recepción no es un comprobante de pago.** El primero dice "la recibimos y la vamos a
  pagar"; el segundo, "la pagamos". El sistema los trata como dos cosas distintas.
- **El recibo de recepción se emite hasta la fecha de vencimiento y no después.** Es un borde duro
  del negocio: pasada esa fecha, la factura queda señalada como incidente y lo que corresponde es
  resolverlo, no emitir un recibo fuera de término. La fecha que manda es la **vigente**: si el
  vencimiento se reprogramó en el calendario **antes** de que la factura venciera, el plazo corre
  hasta la fecha nueva. Nada reabre la emisión una vez pasada: ni cerrar el incidente, ni reprogramar
  después.
- **El recibo lo numera el sistema.** Cada recibo emitido lleva su número propio y correlativo, y su
  documento se puede descargar para mandárselo al proveedor.
- **Los números no se acomodan para que cierren.** Si los pagos de una factura no coinciden con su
  total, el sistema lo señala con los dos números a la vista y deja esa factura afuera de los
  totales, diciendo que la dejó afuera.
- **Ningún total miente por omisión.** Toda deuda y todo total informa cuántas facturas quedaron
  excluidas y permite ir a verlas.
- **El vencimiento sale del plazo pactado con ese proveedor**, no de un plazo general y no de una
  fecha que traiga el documento: con algunos se acordó 30 días, con otros 45 o 60, y el atraso se
  mide contra el plazo de cada uno. Ese plazo da la fecha inicial; si después se acuerda otra y se
  reprograma en el calendario antes de que la factura venza, manda la reprogramada (**P11**).
- **La antigüedad y el atraso se cuentan desde el vencimiento vigente**, que es la fecha contra la
  que se mide si le estamos cumpliendo al proveedor. Reprogramar una factura que ya se venció no
  borra el atraso ya ocurrido: se sigue contando desde su fecha original. El atraso promedio incluye lo que todavía se debe y ya
  se pasó de fecha: dejarlo afuera haría bajar el número justo cuando peor se está cumpliendo.
- **Un pago traído del portal no se borra.** Lo que informó el origen se conserva; lo que se puede
  dejar sin efecto es lo que cargó una persona, y queda registrado que se dejó sin efecto.
- **Un pago que cubre varias facturas lo reparte una persona, nunca el sistema.** Hasta que el
  reparto esté confirmado y cierre exacto contra el monto del comprobante, ningún saldo se mueve.
- **Dos pagos que se parecen no se unen solos.** Un pago cargado a mano y uno traído del portal por
  la misma factura y el mismo monto son un caso para preguntar, no para decidir: unirlos por cuenta
  propia esconde un pago, y contarlos por separado infla lo pagado.
- **Nada se descarta.** Un comprobante que no se puede imputar queda apartado y visible, no se
  pierde ni se aplica a la factura que más se le parezca. Cuando aparece la factura que estaba
  faltando, el sistema lo imputa y lo dice.
- **Un aviso no se repite mientras la causa siga siendo la misma.** Una factura sin recibo genera un
  aviso, no uno por día.
- **Un incidente se cierra explicando qué se hizo.** No se borra ni se apaga en silencio: queda el
  motivo, quién lo cerró y cuándo, y se puede volver a consultar.
- **Los pagos y las cuentas de proveedores no las ve ventas.**

## Criterios de aceptación

- [ ] **RF-01** — La lista de facturas distingue a simple vista saldada, parcial y sin pagos.
- [ ] **RF-02** — Cada factura muestra cuánto se pagó y cuánto queda.
- [ ] **RF-03** — Una factura de $100 con $40 pagados muestra 40%.
- [ ] **RF-04** — Se pueden pedir sólo las facturas parciales, y salen las 41 del relevamiento.
- [ ] **RF-05** — Se pueden pedir las facturas de un proveedor que vencen en un rango de fechas.
- [ ] **RF-06** — Abierta una factura, su estado de pago está ahí y no en otra pantalla.
- [ ] **RF-07** — Sin que nadie lo dispare, los comprobantes de pago nuevos aparecen en el sistema.
- [ ] **RF-08** — De cualquier pago se puede recuperar el comprobante tal como llegó.
- [ ] **RF-09** — Cada comprobante traído queda listado dentro de la factura que indica.
- [ ] **RF-10** — Abierta una factura, se ven sus pagos con fecha y monto.
- [ ] **RF-11** — Un comprobante que apunta a una factura inexistente queda en revisión, no se pierde.
- [ ] **RF-12** — Un comprobante que cubre dos facturas queda en revisión, sin repartir el monto solo.
- [ ] **RF-13** — Traído dos veces el mismo comprobante, el saldo de la factura no se descuenta dos veces.
- [ ] **RF-42** — Cargado a mano un pago de $50 sobre una factura, cuando llega del portal un comprobante de $50 de esa misma factura, queda en revisión y el saldo no baja dos veces.
- [ ] **RF-43** — Resuelto que eran el mismo pago, la factura queda con un solo pago y figura quién lo resolvió.
- [ ] **RF-44** — Un comprobante apartado por factura inexistente se imputa solo el día que esa factura entra al sistema, y el sistema informa que lo hizo.
- [ ] **RF-14** — Una factura de $100 con pagos por $130 queda señalada como inconsistente.
- [ ] **RF-15** — Esa factura muestra los dos números, $100 y $130.
- [ ] **RF-16** — La deuda del proveedor no incluye esa factura, y dice que la excluyó.
- [ ] **RF-17** — Esa factura no figura entre las saldadas en ningún filtro ni total.
- [ ] **RF-45** — Una factura que el portal informa como pagada, con comprobantes por la mitad de su total, figura como parcial.
- [ ] **RF-46** — Esa misma factura queda señalada, mostrando lo que dice el portal y lo que suman sus pagos.
- [ ] **RF-18** — Marcela registra un pago a cuenta y el saldo de la factura baja.
- [ ] **RF-19** — Ese pago figura con el nombre de Marcela y la fecha en que lo cargó.
- [ ] **RF-20** — En la lista de pagos de una factura se distingue cuál vino del portal y cuál se cargó a mano.
- [ ] **RF-21** — Al cargar un pago mayor que el saldo, el sistema advierte antes de confirmar.
- [ ] **RF-22** — Un pago cargado a mano se puede dejar sin efecto y el saldo vuelve a lo anterior.
- [ ] **RF-23** — Un pago traído del portal no ofrece la opción de dejarlo sin efecto.
- [ ] **RF-24** — La ficha del proveedor muestra el total pagado y el saldo adeudado.
- [ ] **RF-25** — La ficha muestra cuánto de la deuda venció hace hasta 30 días, hasta 60, hasta 90 y más.
- [ ] **RF-26** — Una factura del 1 de marzo de un proveedor con plazo de 45 días vence el 15 de abril, aunque el documento traiga otra fecha.
- [ ] **RF-27** — La ficha muestra el promedio de días de atraso —pagadas e impagas vencidas— y coincide con la cuenta hecha a mano.
- [ ] **RF-28** — Junto a la deuda se lee cuántas facturas quedaron afuera y se llega a verlas.
- [ ] **RF-29** — Cada factura indica si su recibo de recepción está emitido.
- [ ] **RF-30** — Los recibos que ya existían en el portal aparecen sin que nadie los cargue.
- [ ] **RF-31** — Se pueden pedir sólo las facturas sin recibo, y salen las 30 del relevamiento.
- [ ] **RF-32** — La pantalla dice cuántas facturas están sin recibo.
- [ ] **RF-33** — Marcela emite el recibo de una factura y queda emitido.
- [ ] **RF-34** — Sobre una factura vencida ayer, el sistema no permite emitir el recibo y explica por qué.
- [ ] **RF-35** — Sobre una factura que ya tiene recibo, el sistema no permite emitir otro.
- [ ] **RF-36** — Cada recibo emitido figura con quién lo emitió y cuándo.
- [ ] **RF-37** — Las 17 facturas vencidas sin recibo aparecen señaladas como incidente desde el primer día.
- [ ] **RF-47** — Emitido el recibo, se descarga su documento y dice de qué factura y de qué proveedor es.
- [ ] **RF-48** — Emitidos tres recibos seguidos, sus números son correlativos y ninguno se repite.
- [ ] **RF-49** — Un recibo emitido por error se anula, y queda registrado quién lo anuló y cuándo.
- [ ] **RF-50** — Anulado el recibo de una factura que vence la semana que viene, se puede emitir otro.
- [ ] **RF-51** — Anulado el recibo de una factura que ya venció, la factura queda señalada como incidente.
- [ ] **RF-38** — Con la anticipación en tres días, el aviso llega tres días antes del vencimiento, a compras y al dueño.
- [ ] **RF-39** — Una misma factura sin recibo genera un aviso, no uno por día.
- [ ] **RF-40** — Emitido el recibo, deja de llegar el aviso por esa factura.
- [ ] **RF-41** — El dueño cambia los días de anticipación y el próximo aviso sale con el valor nuevo.
- [ ] **RF-52** — Sin tocar ningún parámetro, el aviso sale tres días antes del vencimiento.
- [ ] **RF-53** — Un comprobante de $300 que cubre tres facturas se reparte entre las tres, y cada saldo baja por su parte.
- [ ] **RF-54** — Hasta que ese reparto se confirma, ninguna de las tres facturas cambia su saldo.
- [ ] **RF-55** — Un reparto que suma $280 sobre un comprobante de $300 no se puede confirmar.
- [ ] **RF-56** — El reparto confirmado figura con el nombre de quien lo hizo y la fecha.
- [ ] **RF-57** — Marcela cierra el incidente de una factura vencida indicando qué se hizo.
- [ ] **RF-58** — Ese incidente muestra el motivo, quién lo cerró y cuándo.
- [ ] **RF-59** — Cerrado el incidente, la factura deja de contarse entre los pendientes y se la sigue pudiendo consultar.

## Fuera de alcance

- **Pagarle al proveedor desde el sistema.** El sistema registra pagos, no los ejecuta: no se conecta
  con ningún banco ni mueve dinero.
- **La conciliación bancaria.** No existe ningún dato de banco en el origen; prometerla sería
  inventar una fuente.
- **Escribir el recibo en el portal del proveedor.** El recibo se emite y vive del lado nuevo; el
  portal es de sólo lectura.
- **Mandarle el recibo al proveedor desde el sistema.** El sistema genera el documento y se
  descarga; hacérselo llegar al proveedor sigue siendo como hoy.
- **Adoptar la numeración o el formato del recibo que usan hoy en papel.** La numeración la lleva el
  sistema, correlativa y propia. Si el recibo actual tiene su serie, se conversa aparte.
- **El calendario de vencimientos.** Acá se ve el estado de cada factura y se emite su recibo; verlo
  todo junto en un calendario es **P11 — El problema de las fechas**.
- **El detalle de artículos de las facturas.** Sigue fuera de alcance, como en **P2**.
- **Los avisos de órdenes de compra y de la bandeja de mensajes.** Son
  **P6 y P8 — El problema de las compras que se pierden y el de los avisos que nadie mira**.
- **Reprogramar la fecha de vencimiento de una factura.** Acá se calcula contra el plazo pactado;
  moverla a mano es del calendario (**P11**). La fecha que resulte de ahí sí manda acá, con el límite
  de la regla de más arriba.
- **Repartir un pago entre facturas de proveedores distintos.** El reparto es entre facturas de un
  mismo proveedor; si aparece uno que cruza dos, queda apartado y se pregunta.
