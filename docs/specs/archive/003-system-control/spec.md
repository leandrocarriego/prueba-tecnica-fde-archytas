# Control propio del sistema — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Aprobado · **Feature:** 003-system-control · **Fecha:** 2026-08-28
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-29

<!-- `/approve-spec` completa Aprobada por y Fecha de aprobación, y pasa Estado a Aprobado. -->

## Problema

Resuelve **P9 — El problema de no tener control**.

Hoy el cliente depende de otros para dos cosas distintas. Una es operativa: registrar un pago,
emitir un recibo, corregir un monto que llegó mal. La otra es de configuración: cambiar cada cuánto
corre el sistema, o a partir de qué monto tiene que avisar. Ninguna de las dos debería requerir que
alguien le edite un archivo.

En palabras del cliente: *"Hoy todo lo hacemos a mano: armar un recibo para un proveedor, registrar
que pagamos algo, ajustar un monto. Queremos poder hacer esas cosas nosotros mismos desde un solo
lugar, sin pedirle a nadie que nos edite un archivo. También queremos poder ajustar nosotros mismos
algunos parámetros (cada cuánto se actualiza el sistema, a partir de qué monto nos tiene que avisar
algo) sin depender de que alguien nos reprograme algo."*

Hay un costo escondido en devolver ese control: si cualquiera puede corregir cualquier cosa a mano,
**los números dejan de ser explicables**. Por eso lo que se entrega no es sólo la capacidad de
editar, sino la de saber siempre quién editó qué, cuándo, y qué decía antes.

## Objetivo

Que el dueño ajuste los parámetros del sistema desde la propia aplicación y que el equipo cargue y
corrija lo que haga falta desde un solo lugar, quedando registrado en todos los casos quién lo
hizo, cuándo y qué valor había antes.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El dueño | Cambia los parámetros del sistema. Ve todo el historial de cambios manuales del equipo |
| Marcela — compras | Carga y corrige lo que le toca desde un solo lugar, dejando dicho por qué |
| Julián — ventas | Carga y corrige lo que le toca desde un solo lugar, dejando dicho por qué |
| El sistema | Registra cada cambio manual con su autor, su momento y el valor anterior, conserva lo que trajo del portal sin pisarlo, y le avisa al dueño cuando el portal contradice una corrección |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que el equipo corrige, pero no borra.** Un valor que llegó mal se corrige dejando a la
  vista lo que decía antes; nada se elimina del sistema. Es la misma regla que gobierna todo el
  proyecto: lo que no se puede explicar no sirve, aunque el número quede lindo.

## Historias de usuario

### H1 — El dueño ajusta los parámetros sin pedirle nada a nadie *(prioridad más alta)*
Como **dueño**, quiero cambiar desde la aplicación cada cuánto corre el sistema, con cuánta
anticipación avisa un vencimiento y a partir de cuántos días una orden está estancada, para no
depender de que alguien me reprograme algo cada vez que cambia una circunstancia del negocio.

**Cómo se prueba que anda:** el dueño abre una sola pantalla, ve todos los parámetros del sistema
con su valor actual, cambia uno, y el sistema se comporta con el valor nuevo sin que nadie toque
nada más.

### H2 — Cada cambio manual queda registrado
Como **dueño**, quiero que todo lo que alguien corrige a mano quede registrado con su nombre, la
fecha y el valor que había antes, para poder explicar cualquier número cuando no me cierre.

**Cómo se prueba que anda:** Marcela corrige un monto; el dueño abre el historial y ve qué valor
había, cuál quedó, quién lo cambió, cuándo y por qué.

### H3 — Un solo lugar para cargar y corregir
Como **Marcela**, quiero tener un solo lugar donde estén todas las cargas y correcciones que puedo
hacer, para no andar buscando en qué pantalla se hacía cada cosa.

**Cómo se prueba que anda:** Marcela abre una sola pantalla y desde ahí llega a todas las acciones
que le corresponden, sin recorrer el menú entero.

### H4 — Corregir un valor sin borrar lo que decía
Como **Marcela**, quiero corregir un dato que llegó mal del portal —un monto, una fecha, un número
de comprobante o el nombre de un proveedor— dejando dicho por qué lo corrijo, para que el dato quede
bien sin que se pierda lo que el portal había dicho.

**Cómo se prueba que anda:** se corrige el número de una factura escaneada que llegó mal leído; la
pantalla pasa a mostrar el valor corregido, señalado como corregido a mano, y desde ahí se llega a
ver qué decía el portal.

> **Nota agregada el 2026-08-29, después de la firma. No cambia el alcance ni ningún requisito.**
> **H2** y **H4** están escritas desde Marcela, y el único dato traído del portal que existe cuando
> esta feature se construye son los precios de lista, que son de la sección de ventas —Marcela los ve
> sólo para consultar—. El mecanismo de corrección se entrega completo y funciona igual para
> cualquier dato; lo que llega después es el dato de Marcela. Hasta entonces las dos historias se
> verifican con el dueño y con Julián, y Marcela las ejerce sobre lo suyo —las facturas de compra—
> cuando se construya esa feature.

### H5 — Deshacer una corrección equivocada
Como **dueño**, quiero poder dejar sin efecto una corrección manual, para que un error de quien
corrigió no quede pegado al número para siempre.

**Cómo se prueba que anda:** el dueño deja sin efecto una corrección y el valor vuelve a ser el que
había traído el portal, quedando registrado que la corrección se anuló y quién la anuló.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe mostrar en una sola pantalla todos los parámetros configurables con su valor vigente. | H1 |
| RF-02 | El sistema debe permitir al dueño cambiar el valor de un parámetro configurable. | H1 |
| RF-03 | El sistema debe impedir a los roles distintos de dueño cambiar un parámetro configurable. | H1 |
| RF-04 | Mientras el dueño no haya cambiado un parámetro, el sistema debe usar el valor inicial de ese parámetro. | H1 |
| RF-05 | El sistema debe mostrar, junto a cada parámetro, qué cambia en el sistema cuando se lo modifica. | H1 |
| RF-06 | Si el valor indicado para un parámetro está fuera del rango admitido, entonces el sistema debe rechazar el cambio e informar el rango. | H1 |
| RF-07 | Cuando el dueño cambie un parámetro, el sistema debe aplicar el valor nuevo sin que haga falta ninguna intervención adicional. | H1 |
| RF-08 | Cuando el dueño cambie un parámetro, el sistema debe registrar el valor anterior, el valor nuevo, quién lo cambió y cuándo. | H1 |
| RF-09 | Cuando una persona cargue o modifique un dato a mano, el sistema debe registrar quién lo hizo y cuándo. | H2 |
| RF-10 | Cuando una persona modifique a mano un dato existente, el sistema debe conservar el valor que tenía antes. | H2 |
| RF-11 | Cuando una persona modifique a mano un dato existente, el sistema debe exigirle un motivo elegido de una lista de motivos, y debe admitir un detalle adicional escrito. | H2 |
| RF-12 | El sistema debe mostrar el motivo de cada cambio en el historial. | H2 |
| RF-13 | El sistema debe mostrar el historial de cambios manuales ordenado por fecha. | H2 |
| RF-14 | El sistema debe permitir filtrar el historial de cambios manuales por persona y por rango de fechas. | H2 |
| RF-15 | El sistema debe mostrar, desde cualquier dato modificado a mano, su historial de cambios. | H2 |
| RF-16 | El sistema debe impedir que un registro del historial de cambios se modifique. | H2 |
| RF-17 | El sistema debe impedir que un registro del historial de cambios se elimine. | H2 |
| RF-18 | El sistema debe mostrar al dueño el historial de cambios manuales de todas las personas. | H2 |
| RF-19 | El sistema debe mostrar a los roles distintos de dueño únicamente los cambios manuales de las secciones a las que tienen acceso. | H2 |
| RF-20 | El sistema debe reunir en una sola pantalla las acciones de carga y corrección disponibles. | H3 |
| RF-21 | El sistema debe mostrar a cada persona únicamente las acciones habilitadas para su rol. | H3 |
| RF-22 | Cuando una acción manual termine, el sistema debe informar a quien la ejecutó si se aplicó o si falló. | H3 |
| RF-23 | El sistema debe permitir corregir a mano cualquier dato traído del portal: importes, fechas, números de comprobante y nombres de proveedor. | H4 |
| RF-24 | El sistema debe permitir corregir un dato únicamente a las personas con acceso a la sección a la que ese dato pertenece. | H4 |
| RF-25 | Cuando una persona corrija a mano un dato traído del portal, el sistema debe conservar sin cambios lo que el portal había informado. | H4 |
| RF-26 | El sistema debe señalar como corregido a mano todo dato que difiera de lo que informó el portal. | H4 |
| RF-27 | El sistema debe mostrar, junto a un dato corregido a mano, el valor que había informado el portal. | H4 |
| RF-28 | Si una actualización posterior del portal trae para un dato corregido a mano un valor distinto del original, entonces el sistema debe señalarlo para revisión en la pantalla de ese dato, en lugar de pisar la corrección. | H4 |
| RF-29 | Si una actualización posterior del portal trae para un dato corregido a mano un valor distinto del original, entonces el sistema debe avisarle al dueño. | H4 |
| RF-30 | El sistema debe permitir al dueño dejar sin efecto una corrección manual. | H5 |
| RF-31 | Cuando el dueño deje sin efecto una corrección manual, el sistema debe restituir el valor informado por el portal. | H5 |
| RF-32 | Cuando el dueño deje sin efecto una corrección manual, el sistema debe registrar quién la anuló y cuándo. | H5 |
| RF-33 | El sistema debe impedir dejar sin efecto una corrección manual sobre un dato que no fue traído del portal. | H5 |

## Reglas de negocio

- **Los parámetros del sistema son del dueño.** Nadie más los cambia, y ninguno de ellos exige
  intervención técnica: si un valor hace falta ajustarlo, se ajusta desde la aplicación.
- **Todo parámetro configurable vive en una sola pantalla.** Cada funcionalidad que necesite un
  valor ajustable lo publica ahí; no hay parámetros escondidos en la pantalla de la funcionalidad
  que los usa.
- **Los parámetros que el negocio ya identificó** son siete: cada cuánto se consulta el portal, a
  partir de qué porcentaje de suba se destaca un precio, con cuántos días de anticipación se avisa
  un vencimiento, a partir de cuántos días una orden de compra se considera estancada, después de
  cuánto tiempo sin uso se cierra una sesión, con cuántos días de anticipación se avisa una factura
  que sigue sin recibo, y a qué hora sale el resumen diario de avisos. Todos tienen valor inicial:
  un parámetro entra al panel cuando se sabe qué mide, no antes.
- **Con qué valores arranca el sistema el primer día**: avisa un vencimiento con **3 días** de
  anticipación, considera estancada una orden de compra a los **15 días**, cierra una sesión sin uso
  a los **60 minutos**, avisa con **3 días** de anticipación una factura que sigue sin recibo, y
  manda el resumen diario a las **8:00**. Los dos parámetros de la actualización de precios llegan
  con el valor inicial que fijó esa feature, y no se redefinen acá. El dueño cambia todos cuando
  quiera: son puntos de partida, no decisiones cerradas.
- **Toda edición manual deja rastro**: quién, cuándo, qué decía antes, qué dice ahora y por qué. Sin
  excepciones y sin importar quién la haga.
- **El historial de cambios no se edita ni se borra.** Un historial que se puede corregir no es un
  historial.
- **Lo que dijo el portal se conserva siempre.** Se corrige cualquier dato que el portal haya
  informado mal —un monto, una fecha, un número de comprobante, el nombre de un proveedor—, y en
  todos los casos la corrección se muestra encima, señalada como tal, sin reemplazar nunca lo que el
  portal informó: si mañana un número no cierra, tiene que poder explicarse con lo que decía el
  origen.
- **Una corrección no se pisa sola.** Si el portal vuelve a informar algo distinto sobre un dato que
  una persona ya corrigió, el sistema pregunta en lugar de decidir cuál de los dos vale: lo señala
  en la pantalla del propio dato y además le avisa al dueño, para que el conflicto no dependa de que
  alguien pase por esa pantalla. El caso se cierra donde vive el dato —corrigiéndolo otra vez o
  dejando sin efecto la corrección—, no en una bandeja aparte.
- **Corregir exige decir por qué.** El motivo es lo que convierte una corrección en una decisión del
  negocio y no en un número que apareció. Se elige de una lista corta y admite un detalle escrito,
  para poder contar después cuántas correcciones fueron por lo mismo sin perder el caso raro. Se
  exige en toda modificación manual de un dato que ya existía, haya venido del portal o lo haya
  cargado una persona.
- **Cada uno corrige lo suyo.** Corrige quien tiene acceso a la sección del dato, siempre con su
  nombre registrado; dejar sin efecto una corrección es sólo del dueño. El lugar único donde están
  reunidas las acciones no amplía lo que cada uno puede tocar.

## Criterios de aceptación

- [ ] **RF-01** — Hay una sola pantalla que lista todos los parámetros del sistema con lo que valen hoy.
- [ ] **RF-02** — El dueño cambia un parámetro desde esa pantalla y queda guardado.
- [ ] **RF-03** — Marcela y Julián no encuentran esa pantalla.
- [ ] **RF-04** — Recién instalado y sin que nadie toque nada, el aviso de vencimiento sale con 3 días de anticipación, una orden se considera estancada a los 15 días y la sesión se cierra a los 60 minutos sin uso.
- [ ] **RF-05** — Junto a cada parámetro se lee, en una frase, qué cambia si se lo modifica.
- [ ] **RF-06** — Puesto un valor imposible (una frecuencia de cero), el sistema lo rechaza y dice entre qué valores tiene que estar.
- [ ] **RF-07** — Cambiada la anticipación de aviso, el siguiente aviso sale con la anticipación nueva.
- [ ] **RF-08** — Cada cambio de parámetro figura con el valor viejo, el nuevo, quién y cuándo.
- [ ] **RF-09** — Después de que Marcela carga algo a mano, ese dato muestra su nombre y la fecha.
- [ ] **RF-10** — Modificado un dato, el valor anterior sigue estando disponible.
- [ ] **RF-11** — Sin elegir un motivo, la modificación no se puede confirmar: ni sobre un dato traído del portal ni sobre uno que cargó una persona.
- [ ] **RF-12** — En el historial, cada cambio se lee con el motivo por el que se hizo.
- [ ] **RF-13** — El historial de cambios se lee de más nuevo a más viejo.
- [ ] **RF-14** — Se puede pedir el historial de una persona en un rango de fechas y sale sólo eso.
- [ ] **RF-15** — Estando parado en un dato corregido, se llega a su historial sin buscarlo en otra pantalla.
- [ ] **RF-16** — No hay ninguna pantalla que permita editar una entrada del historial.
- [ ] **RF-17** — No hay ninguna pantalla que permita borrar una entrada del historial.
- [ ] **RF-18** — El dueño ve en el historial los cambios de las tres personas.
- [ ] **RF-19** — Julián ve en el historial sus cambios y los de su sección, no los de las facturas de compra.
- [ ] **RF-20** — Hay una sola pantalla desde la que se llega a todas las cargas y correcciones.
- [ ] **RF-21** — Esa pantalla le muestra a Marcela acciones distintas de las que le muestra a Julián.
- [ ] **RF-22** — Ejecutada una acción, quien la ejecutó ve si se aplicó o si falló.
- [ ] **RF-23** — Se corrige el número de comprobante de una factura escaneada que llegó mal leído, y no sólo su total.
- [ ] **RF-24** — Julián no puede corregir el total de una factura de compra.
- [ ] **RF-25** — Corregido un total, lo que informó el portal ese día sigue estando.
- [ ] **RF-26** — Un dato corregido a mano se distingue a simple vista de uno que llegó del portal.
- [ ] **RF-27** — Al lado del valor corregido se ve el valor original.
- [ ] **RF-28** — Si el portal vuelve a informar otro valor para un dato ya corregido, el caso queda señalado en la pantalla de ese dato y la corrección sigue en pie.
- [ ] **RF-29** — Ese mismo conflicto le llega al dueño como aviso, sin que tenga que estar mirando la pantalla.
- [ ] **RF-30** — El dueño deja sin efecto una corrección desde el historial.
- [ ] **RF-31** — Anulada la corrección, el dato vuelve a mostrar lo que informó el portal.
- [ ] **RF-32** — La anulación figura en el historial con quién la hizo y cuándo.
- [ ] **RF-33** — Un dato cargado enteramente a mano no ofrece la opción de "volver al valor del portal".

## Fuera de alcance

- **Las acciones concretas sobre facturas, pagos, recibos y vencimientos.** Esta feature entrega el
  lugar único donde viven, la regla de que todo cambio queda registrado y la corrección de valores.
  *Registrar un pago* y *emitir un recibo* los define **P5 y P12**; *cargar un vencimiento*, **P11**.
  Cada una aparece en esta pantalla cuando se construye.
- **La carga del histórico que hoy vive fuera del sistema viejo.** El cliente confirmó que hoy se
  trabaja de las tres formas a la vez: en papel, en planillas propias y en el sistema viejo pantalla
  por pantalla. Existe entonces un histórico que no está en ningún sistema, y cargarlo es un trabajo
  aparte que primero hay que dimensionar. Esta feature entrega el lugar donde se carga y se corrige
  de acá en adelante.
- **Importar datos desde una planilla.** Aunque el equipo lleve planillas propias, esta feature no
  las levanta: las cargas son de a una, desde la aplicación.
- **Una bandeja aparte para los conflictos** entre el portal y una corrección manual. Se señalan en
  la pantalla del dato y se le avisa al dueño; no hay una lista separada que alguien tenga que ir a
  vaciar.
- **El monto a partir del cual el sistema avisa.** El cliente lo pidió, pero nunca dijo monto **de
  qué**: si el total de una factura, si la deuda acumulada con un proveedor, o si son dos umbrales
  distintos. Un parámetro que nadie puede explicar en una frase no se puede publicar en el panel
  (RF-05) ni arrancar con un valor (RF-04). Lo define **P8** junto con el aviso que lo usa, y entra
  al panel cuando esa feature se especifique — sin que haga falta tocar ésta, porque el panel se
  arma con lo que cada funcionalidad publica.
- **Por qué canal le llega el aviso al dueño.** Esta feature define que el aviso sale; el canal es
  el mismo que usa el sistema para todos sus avisos y lo define **P8**.
- **Escribir cualquier cosa en el portal del proveedor.** Una corrección hecha acá vive en el
  sistema propio; el portal es de un tercero y sólo se lee.
- **El registro de quién entró al sistema y a quién se le negó el paso.** Eso es
  **P10 — El problema de los accesos**.
- **Que el sistema decida solo cuál valor es el correcto** cuando el portal y una corrección manual
  se contradicen. Lo señala, avisa, y espera a una persona.
