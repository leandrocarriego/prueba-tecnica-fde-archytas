# Facturas y proveedores — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Aprobado · **Feature:** 004-invoices-suppliers · **Fecha:** 2026-08-28
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-29

<!-- `/approve-spec` completa Aprobada por y Fecha de aprobación, y pasa Estado a Aprobado. -->

## Problema

Resuelve **P2 — El problema de las facturas** y **P4 — El problema de los proveedores**.

Son el mismo problema mirado desde dos lados. Las facturas llegan en tres formatos distintos y con
el nombre del proveedor escrito de cualquier manera; y como el nombre está escrito de cualquier
manera, el cliente no sabe con cuántos proveedores trabaja ni cuánto le compró a cada uno.

En palabras del cliente, sobre las facturas: *"Cada proveedor nos manda sus facturas como puede:
algunos un PDF prolijo, otros un PDF que en realidad es una foto escaneada, otros directamente un
Excel armado a las apuradas (…) el mismo proveedor a veces figura con el nombre completo, a veces
abreviado, a veces con un error de tipeo, nunca sabemos con certeza si dos facturas son del mismo
proveedor o de dos distintos. Necesitamos que todo esto entre a un solo lugar, ordenado, sin que se
nos duplique nada, y que si algo no se puede resolver solo, nos avise en vez de adivinar mal."*

Y sobre los proveedores: *"No sé con cuántos proveedores trabajo realmente. En el sistema el mismo
me aparece escrito de tres o cuatro formas distintas, así que cuando quiero saber cuánto le compré a
uno en el año, no me da nunca. (…) También necesito tener a mano el mail y el CUIT de cada uno,
porque hoy los buscamos en la libreta."*

Dos datos del relevamiento dimensionan el trabajo: **46 de cada 100 facturas son una imagen
escaneada sin una sola letra que se pueda leer de forma automática**, y el nombre del proveedor
aparece escrito de **24 formas distintas** entre las facturas.

## Objetivo

Que todas las facturas de compra entren a un solo lugar ordenado, con su proveedor correctamente
identificado contra el padrón real, y que el cliente pueda abrir un proveedor y ver sus datos, su
contacto, su plazo de pago acordado y todo lo que le compró.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El sistema | Trae del portal las facturas y sus archivos, lee los datos de cada una, reconoce al proveedor y aparta lo que no puede resolver |
| Marcela — compras | Trabaja las facturas y los proveedores: busca, filtra, revisa lo apartado, completa lo que faltó y edita los datos del proveedor |
| El dueño | Ve todo. Consulta cuánto le compró a cada proveedor, y también resuelve lo apartado y asigna grafías |
| Julián — ventas | No accede a las facturas de compra ni a las cuentas de proveedores |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que una herramienta de lectura sin costo de licencia alcanza para las 46 facturas
  escaneadas.** El cliente decidió resolver la lectura **sin costo por documento**, y la
  consecuencia se acepta de frente: sobre una imagen escaneada esa lectura acierta menos, así que
  más facturas van a caer en la pantalla de revisión. **Cuánto más, no está medido sobre las
  facturas reales.** Si el volumen de revisión resultara impracticable, la salida no es dar por
  bueno un dato dudoso: es volver a conversar el costo.

## Historias de usuario

### H1 — Todas las facturas en un solo lugar *(prioridad más alta)*
Como **Marcela**, quiero ver todas las facturas de compra juntas en una sola pantalla, para dejar de
buscarlas de a una en el sistema viejo.

**Cómo se prueba que anda:** se abre la pantalla de facturas y están las cien, cada una con su
número, su fecha, su proveedor y su total, sin que nadie las haya cargado a mano.

### H2 — Un proveedor por proveedor
Como **dueño**, quiero que cada proveedor aparezca una sola vez, con todas las formas en que está
escrito su nombre ya unificadas, para saber por fin con cuántos proveedores trabajo.

**Cómo se prueba que anda:** la pantalla de proveedores muestra ocho proveedores y no veinticuatro,
y al abrir uno se ven todas las grafías con las que llegó su nombre.

### H3 — La ficha del proveedor, con lo que hoy está en la libreta
Como **Marcela**, quiero abrir un proveedor y ver su CUIT, su correo, su teléfono y el plazo de pago
que tenemos acordado, para no buscarlo en la libreta cada vez.

**Cómo se prueba que anda:** se abre un proveedor y ahí están sus datos fiscales, su contacto y su
plazo pactado, y se pueden corregir desde la misma pantalla.

### H4 — Cuánto le compré a cada uno
Como **dueño**, quiero ver, dentro de la ficha de un proveedor, todas sus facturas y cuánto le
compré en un período, para tener por fin un número que me cierre.

**Cómo se prueba que anda:** se abre un proveedor, se pide el año en curso, y el total que muestra
coincide con la suma de sus facturas hecha a mano.

### H5 — Los datos salen del archivo de la factura
Como **Marcela**, quiero que el sistema lea el número, la fecha, el proveedor y el total del archivo
de cada factura, para no tipearlos yo de a cien.

**Cómo se prueba que anda:** llega una factura en PDF, otra escaneada y otra en planilla, y en las
tres el sistema carga los cuatro datos sin que nadie los escriba.

### H6 — Lo dudoso se pregunta, no se adivina
Como **Marcela**, quiero que cuando el sistema no esté seguro de un dato me lo muestre y me deje
decidir, con el pedazo del archivo a la vista, para resolverlo en segundos en lugar de descubrir un
error tres meses después.

**Cómo se prueba que anda:** llega una factura escaneada donde el total no se lee bien; la factura
aparece en la pantalla de revisión mostrando ese pedazo de la imagen, y al confirmar el número la
factura queda completa.

### H7 — Que no se duplique nada
Como **Marcela**, quiero que la misma factura no entre dos veces, para que la deuda con un proveedor
no aparezca inflada.

**Cómo se prueba que anda:** el sistema trae dos veces la misma factura y en la pantalla sigue
habiendo una sola.

### H8 — Encontrar una factura sin recorrer la lista
Como **Marcela**, quiero buscar una factura por CUIT o por razón social y filtrar por fecha, por
proveedor y por monto, para llegar a la que necesito sin recorrer cien.

**Cómo se prueba que anda:** se escribe el CUIT de un proveedor y quedan sus facturas; se agrega un
rango de fechas y quedan sólo las de ese rango.

### H9 — Que no me pregunten dos veces lo mismo
Como **Marcela**, quiero que cuando decido que una forma de escribir un nombre corresponde a tal
proveedor, el sistema no me lo vuelva a preguntar **y resuelva de una vez las que ya estaban
esperando**, para que la pantalla de revisión se vacíe en lugar de crecer.

**Cómo se prueba que anda:** se asigna una grafía nueva a su proveedor; antes de guardar, el sistema
avisa que esa decisión resuelve otras once facturas que estaban en revisión, y al confirmar las
once desaparecen de la cola junto con la que se estaba resolviendo. La próxima factura que llegue
con esa misma grafía entra directo, sin pasar por revisión.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe obtener del portal las facturas de compra con la frecuencia configurada. | H1 |
| RF-02 | Cuando el sistema obtenga una factura, debe conservar su archivo tal como llegó del portal. | H1 |
| RF-03 | El sistema debe mostrar las facturas de compra con su número, su fecha, su proveedor y su total. | H1 |
| RF-04 | El sistema debe permitir abrir el archivo original de cualquier factura. | H1 |
| RF-05 | El sistema debe mostrar el formato en que llegó cada factura. | H1 |
| RF-06 | El sistema debe impedir al rol ventas el acceso a las facturas de compra. | H1 |
| RF-07 | Cuando el sistema se ponga en marcha por primera vez, debe procesar las facturas que ya están en el portal, y las que no pueda resolver deben quedar apartadas sin impedir el uso de las demás. | H1 |
| RF-08 | El sistema debe mantener un padrón de proveedores tomado del portal. | H2 |
| RF-09 | Cuando el sistema identifique al proveedor de una factura, debe asociarla a un proveedor del padrón. | H2 |
| RF-10 | El sistema debe registrar, para cada proveedor, todas las formas en que llegó escrito su nombre. | H2 |
| RF-11 | Si una factura trae el CUIT del proveedor, entonces el sistema debe identificar al proveedor por ese CUIT. | H2 |
| RF-12 | Si una factura no trae el CUIT del proveedor, entonces el sistema debe identificarlo por el nombre escrito en ella, contra el padrón. | H2 |
| RF-13 | Si el proveedor de una factura no se puede identificar con certeza, entonces el sistema debe apartar la factura para revisión. | H2 |
| RF-14 | Si una factura corresponde a un proveedor que no está en el padrón, entonces el sistema debe apartarla indicando ese motivo, sin dar de alta un proveedor ni permitir darlo de alta desde la revisión. | H2 |
| RF-15 | El sistema debe mostrar, para cada proveedor, su razón social, su CUIT, su correo, su teléfono y su plazo de pago pactado. | H3 |
| RF-16 | El sistema debe permitir al dueño y al rol compras corregir el correo, el teléfono y el plazo de pago pactado de un proveedor. | H3 |
| RF-17 | El sistema debe impedir editar la razón social y el CUIT de un proveedor. | H3 |
| RF-18 | Cuando alguien corrija un dato de un proveedor, el sistema debe registrar quién lo corrigió, cuándo y qué valor tenía antes. | H3 |
| RF-19 | Si el portal trae, para un dato que ya fue corregido a mano, un valor distinto, entonces el sistema debe conservar el valor corregido y señalar la diferencia en lugar de sobrescribirlo. | H3 |
| RF-20 | Si un dato de contacto de un proveedor falta en el portal, entonces el sistema debe mostrarlo como faltante en lugar de dejarlo en blanco. | H3 |
| RF-21 | El sistema debe mostrar, dentro de la ficha de un proveedor, todas sus facturas. | H4 |
| RF-22 | El sistema debe mostrar, para un proveedor y un período elegido, el total facturado por ese proveedor. | H4 |
| RF-23 | El sistema debe informar, junto al total facturado de un proveedor, cuántas facturas quedaron excluidas por estar en revisión. | H4 |
| RF-24 | El sistema debe mostrar la cantidad de proveedores del padrón. | H4 |
| RF-25 | Cuando el sistema obtenga el archivo de una factura, debe extraer de él su número, su fecha, su proveedor y su total. | H5 |
| RF-26 | El sistema debe extraer los datos de cabecera de una factura tanto si el archivo es un documento con texto, como si es una imagen escaneada, como si es una planilla. | H5 |
| RF-27 | El sistema debe registrar, para cada dato extraído, si se obtuvo con certeza o si quedó en duda. | H5 |
| RF-28 | Si un archivo de factura tiene una forma que el sistema no reconoce, entonces el sistema debe apartarlo para revisión sin interrumpir el procesamiento de los demás. | H5 |
| RF-29 | Si un dato de una factura queda en duda, entonces el sistema debe apartar esa factura para revisión en lugar de darlo por bueno. | H6 |
| RF-30 | El sistema debe mostrar, junto a cada dato en duda, la parte del archivo original de la que se obtuvo. | H6 |
| RF-31 | Cuando el dueño o el rol compras confirme o corrija un dato en duda, el sistema debe registrarlo como el valor de ese dato. | H6 |
| RF-32 | Cuando una persona resuelva una factura apartada, el sistema debe registrar qué decidió, quién lo decidió y cuándo. | H6 |
| RF-33 | Cuando una factura apartada quede resuelta, el sistema debe dejar de mostrarla entre las pendientes de revisión. | H6 |
| RF-34 | El sistema debe mostrar cuántas facturas están pendientes de revisión. | H6 |
| RF-35 | El sistema debe impedir que una factura quede registrada sin número, sin fecha, sin proveedor o sin total. | H6 |
| RF-36 | El sistema debe habilitar únicamente al dueño y al rol compras a resolver las facturas apartadas y a asignar grafías a un proveedor. | H6 |
| RF-37 | Si una factura obtenida coincide en número y proveedor con una ya registrada, entonces el sistema debe conservar una sola. | H7 |
| RF-38 | Si una factura obtenida coincide en número y proveedor con una ya registrada pero difiere en su total, entonces el sistema debe apartarla para revisión en lugar de descartarla. | H7 |
| RF-39 | El sistema debe mostrar, para una factura que llegó más de una vez, cuántas veces llegó. | H7 |
| RF-40 | Mientras el proveedor de una factura no esté identificado, el sistema no debe darla por duplicada de ninguna otra. | H7 |
| RF-41 | El sistema debe permitir buscar facturas por CUIT del proveedor. | H8 |
| RF-42 | El sistema debe permitir buscar facturas por razón social del proveedor. | H8 |
| RF-43 | El sistema debe permitir filtrar las facturas por rango de fechas. | H8 |
| RF-44 | El sistema debe permitir filtrar las facturas por proveedor. | H8 |
| RF-45 | El sistema debe permitir ordenar las facturas por fecha y por total. | H8 |
| RF-46 | El sistema debe permitir filtrar las facturas por su estado de revisión. | H8 |
| RF-47 | Cuando el dueño o el rol compras asigne una grafía de nombre a un proveedor, el sistema debe guardar esa decisión como criterio. | H9 |
| RF-48 | Cuando alguien vaya a guardar una asignación de grafía, el sistema debe informar antes cuántas facturas apartadas resuelve esa asignación. | H9 |
| RF-49 | Cuando una asignación de grafía quede guardada, el sistema debe aplicarla también a las facturas ya apartadas que traían esa misma grafía. | H9 |
| RF-50 | Si una factura posterior trae una grafía ya asignada a un proveedor, entonces el sistema debe asociarla a ese proveedor sin apartarla. | H9 |
| RF-51 | El sistema debe mostrar las asignaciones de grafía guardadas, junto con quién las decidió y cuándo. | H9 |
| RF-52 | El sistema debe permitir dejar sin efecto una asignación de grafía guardada. | H9 |
| RF-53 | Cuando una asignación de grafía quede sin efecto, el sistema debe volver a apartar las facturas que esa asignación venía resolviendo. | H9 |

## Reglas de negocio

- **El portal del proveedor es la única fuente de las facturas, y el sistema nunca le escribe nada.**
  El cliente confirmó que hoy las facturas no llegan por ninguna otra vía.
- **Nada se descarta.** Una factura que no se puede leer, o cuyo proveedor no se puede reconocer, no
  se pierde ni frena el procesamiento del resto: queda apartada, contada y visible para que una
  persona decida.
- **El archivo de cada factura se conserva tal como llegó.** Si mañana mejora la forma de leerlos, se
  pueden volver a leer los cien sin pedirle nada al portal — y si un número no cierra, se puede
  mostrar el papel del que salió.
- **La lectura de las facturas se resuelve sin costo por documento.** El cliente eligió no pagar un
  costo recurrente por factura leída, y la consecuencia se acepta con los ojos abiertos: sobre las
  46 escaneadas la lectura acierta menos y más facturas caen en revisión. Lo que **no** se hace para
  compensar es dar por bueno un dato dudoso.
- **Ningún dato de una factura se completa por suposición.** Un total dudoso se pregunta; no se
  redondea, no se estima y no se deja en cero.
- **El CUIT manda cuando está.** El cliente confirmó que algunas facturas lo traen y otras no: con
  CUIT, reconocer al proveedor es una certeza; sin CUIT, se resuelve por el nombre contra el padrón,
  y toda interpretación que no sea concluyente va a revisión humana.
- **El padrón son los ocho proveedores del portal.** El cliente confirmó que son ocho y que las
  condiciones de pago que publica el portal —30, 45 o 60 días— son las vigentes. Ese plazo entra como
  valor inicial de cada ficha y se corrige desde ahí.
- **El sistema no da de alta proveedores por su cuenta, y tampoco se lo puede dar de alta desde la
  revisión.** Una factura de alguien que no está en el padrón queda apartada, con el motivo a la
  vista, hasta que ampliar el padrón se decida como lo que es: una decisión del negocio.
- **Lo que corrige una persona no lo pisa el portal.** Un correo, un teléfono o un plazo corregido a
  mano gana sobre lo que traiga el portal después; si el portal trae otro valor, el sistema lo
  señala en lugar de sobrescribir. La razón social y el CUIT no se editan: son con lo que se
  reconoce al proveedor, y corregirlos a mano desarmaría la identificación de sus facturas.
- **Una decisión sobre una grafía se toma una sola vez, y alcanza también a lo que ya estaba
  esperando.** Cuando una persona dice que "Ferrec. SA" es tal proveedor, esa decisión se guarda, se
  aplica a lo que llegue después y resuelve las facturas que ya estaban apartadas con esa misma
  grafía. Antes de guardarla, el sistema dice a cuántas alcanza, para que quien decide vea el tamaño
  de lo que está por resolver. Las decisiones están a la vista, con quién las tomó, y se pueden
  dejar sin efecto: una decisión equivocada tiene que poder corregirse, y corregirla devuelve a
  revisión lo que esa decisión venía resolviendo.
- **Con qué se arranca el primer día.** Las cien facturas del portal entran como **trabajo
  pendiente**: lo que se pudo leer está disponible desde el primer momento, y lo apartado se trabaja
  al ritmo de compras, contado y visible en la pantalla de revisión. No hay una jornada de limpieza
  previa que haya que terminar antes de usar el sistema.
- **Del detalle de artículos no se carga nada.** Se cargan los cuatro datos de cabecera —número,
  fecha, proveedor y total—, que son los que alimentan la deuda, el calendario y los recibos. Con la
  calidad de imagen de los escaneados, leer la lista de artículos daría un error tan alto que habría
  que revisarla toda a mano igual.
- **Cada revisión se resuelve en segundos.** El dato dudoso viene con el pedazo del archivo a la
  vista: si resolver un caso cuesta trabajo, la pantalla se abandona, que es exactamente lo que ya
  pasó con la bandeja del portal.
- **Las facturas de compra y las cuentas de proveedores no las ve ventas.** La cola de revisión la
  trabajan el dueño y compras.

## Criterios de aceptación

- [ ] **RF-01** — Sin que nadie lo dispare, las facturas nuevas del portal aparecen en el sistema.
- [ ] **RF-02** — De cualquier factura se puede recuperar el archivo exactamente como llegó.
- [ ] **RF-03** — La pantalla de facturas lista número, fecha, proveedor y total de cada una.
- [ ] **RF-04** — Desde una factura se abre su PDF o su planilla original.
- [ ] **RF-05** — La lista distingue a simple vista cuáles llegaron como imagen escaneada.
- [ ] **RF-06** — Julián no llega a la pantalla de facturas ni pegando su dirección.
- [ ] **RF-07** — El primer día, las cien facturas del portal quedan procesadas: las legibles listas para usar y las demás contadas en la pantalla de revisión, sin que haya que vaciar la cola para empezar a trabajar.
- [ ] **RF-08** — La pantalla de proveedores muestra los proveedores del padrón del portal.
- [ ] **RF-09** — Cada factura procesada muestra a qué proveedor del padrón quedó asociada.
- [ ] **RF-10** — Al abrir un proveedor se ven todas las formas en que llegó escrito su nombre.
- [ ] **RF-11** — Una factura que trae CUIT queda asociada a su proveedor sin pasar por revisión.
- [ ] **RF-12** — Una factura sin CUIT, con un nombre que corresponde sin dudas a un proveedor del padrón, queda asociada a ese proveedor.
- [ ] **RF-13** — Una factura con un nombre que podría ser de dos proveedores queda apartada.
- [ ] **RF-14** — Una factura de un proveedor que no está en el padrón no crea un proveedor nuevo ni deja darlo de alta desde la revisión: queda apartada, y el motivo dice que el proveedor no está en el padrón.
- [ ] **RF-15** — La ficha del proveedor muestra razón social, CUIT, correo, teléfono y plazo pactado.
- [ ] **RF-16** — Marcela corrige el correo de un proveedor desde su ficha.
- [ ] **RF-17** — La razón social y el CUIT de un proveedor no se pueden editar desde la ficha.
- [ ] **RF-18** — Esa corrección figura con su nombre, la fecha y el valor anterior.
- [ ] **RF-19** — Corregido a mano un teléfono, una actualización posterior del portal con otro teléfono no lo pisa: la ficha sigue mostrando el corregido y señala que el portal trae otro distinto.
- [ ] **RF-20** — Un proveedor sin teléfono en el portal muestra "falta", no un espacio vacío.
- [ ] **RF-21** — La ficha del proveedor lista todas sus facturas.
- [ ] **RF-22** — Pedido el año en curso de un proveedor, el total coincide con la suma hecha a mano.
- [ ] **RF-23** — Junto a ese total se lee cuántas facturas del proveedor quedaron afuera por estar en revisión.
- [ ] **RF-24** — La pantalla de proveedores dice cuántos son.
- [ ] **RF-25** — Cargada una factura nueva, sus cuatro datos de cabecera aparecen sin que nadie los tipee.
- [ ] **RF-26** — Las tres facturas de muestra —PDF, imagen escaneada y planilla— quedan con sus cuatro datos cargados.
- [ ] **RF-27** — Cada dato de una factura indica si se obtuvo con certeza o quedó en duda.
- [ ] **RF-28** — Una planilla con la fila de títulos corrida no rompe el procesamiento de las demás facturas: queda apartada.
- [ ] **RF-29** — Una factura escaneada con el total borroso no se carga con un número inventado: queda en revisión.
- [ ] **RF-30** — En la revisión se ve el recorte del archivo donde estaba ese dato.
- [ ] **RF-31** — Confirmado el total desde la revisión, la factura pasa a mostrar ese total.
- [ ] **RF-32** — Cada factura resuelta muestra qué se decidió, quién y cuándo.
- [ ] **RF-33** — Resuelta una factura, la pantalla de revisión tiene una pendiente menos.
- [ ] **RF-34** — La pantalla de revisión dice cuántas facturas están pendientes.
- [ ] **RF-35** — No hay ninguna factura registrada a la que le falte alguno de los cuatro datos.
- [ ] **RF-36** — Julián no puede resolver una factura apartada ni asignar una grafía; el dueño y Marcela sí.
- [ ] **RF-37** — Traída dos veces la misma factura, en la lista hay una sola.
- [ ] **RF-38** — Traída dos veces la misma factura con totales distintos, el caso aparece en revisión con los dos totales a la vista.
- [ ] **RF-39** — Una factura que llegó tres veces lo indica.
- [ ] **RF-40** — Dos facturas apartadas sin proveedor identificado, con el mismo número, siguen siendo dos: ninguna se descarta por duplicada.
- [ ] **RF-41** — Escrito un CUIT, quedan las facturas de ese proveedor.
- [ ] **RF-42** — Escrito parte de una razón social, quedan sus facturas.
- [ ] **RF-43** — Aplicado un rango de fechas, quedan sólo las de ese rango.
- [ ] **RF-44** — Elegido un proveedor, quedan sólo sus facturas.
- [ ] **RF-45** — Se puede ordenar la lista por fecha y por total, en los dos sentidos.
- [ ] **RF-46** — Se pueden pedir sólo las facturas que están en revisión.
- [ ] **RF-47** — Asignada una grafía a un proveedor, la decisión queda guardada.
- [ ] **RF-48** — Antes de guardar la asignación, la pantalla dice a cuántas facturas apartadas alcanza.
- [ ] **RF-49** — Guardada la asignación, esas facturas quedan resueltas y salen de la cola de revisión.
- [ ] **RF-50** — La próxima factura con esa misma grafía entra sin pasar por revisión.
- [ ] **RF-51** — Hay una pantalla con las asignaciones guardadas, cada una con quién y cuándo.
- [ ] **RF-52** — Una asignación guardada se puede dejar sin efecto.
- [ ] **RF-53** — Dejada sin efecto, las facturas que resolvía vuelven a aparecer en revisión.

## Fuera de alcance

- **El detalle de artículos de las facturas.** Se cargan los cuatro datos de cabecera. En las 46
  escaneadas, leer la lista de artículos daría un error tan alto que habría que revisarla a mano
  igual.
- **El estado de pago de cada factura, la deuda, el atraso y la antigüedad de la deuda.** La ficha
  del proveedor de esta feature muestra qué le compré; **cuánto le pagué, cuánto le debo y hace
  cuánto** lo completa **P5 — El problema de los pagos a medias**, que es donde entran los pagos.
- **El recibo de recepción de cada factura.** Es **P12 — El problema de los recibos**.
- **El calendario de vencimientos.** Es **P11 — El problema de las fechas**.
- **Cargar una factura a mano desde un archivo propio.** Las facturas llegan del portal.
- **Dar de alta un proveedor nuevo**, ni por iniciativa del sistema ni desde la pantalla de revisión.
  El padrón es el del portal —ocho proveedores, confirmados por el cliente—; sumar uno es una
  decisión del negocio que se toma aparte.
- **Editar la razón social o el CUIT de un proveedor.** Son los datos con los que se lo reconoce.
- **Recibir facturas por correo electrónico.** El cliente confirmó que hoy no llegan por esa vía y
  que el portal sigue siendo la única fuente. Si mañana llegaran, sumar una segunda vía cambia el
  alcance y se conversa aparte.
- **Un servicio pago de lectura de documentos.** El cliente eligió resolver la lectura sin costo por
  documento. Si el volumen de revisión resultara impracticable, es una conversación de costo, no un
  cambio que el equipo tome por su cuenta.
- **Reclamarle nada al proveedor ni escribir en el portal.** El origen es de sólo lectura.
