# Lo apartado se ve — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
-->

**Estado:** Aprobado · **Feature:** 011-set-aside-visibility · **Fecha:** 2026-08-31
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-31 *(tercera firma)*

> **Por qué van tres.** La primera cayó con la enmienda sobre RF-20, que achicó el alcance: el
> cierre automático se prometía con un comprobante de pago y sólo puede darse con una venta. La
> segunda cayó con RF-24, que lo **agranda**: el cierre automático pasa a tener vuelta atrás. Las dos
> veces se volvió a firmar por la misma razón — lo que el cliente había leído dejó de ser lo que
> iba a recibir. Esta firma es sobre el texto con RF-20 acotado y RF-24 incluido.

## Problema

No resuelve uno de los doce problemas: resuelve **el problema de fondo**, el que el brief pone antes
que los doce y que el cliente enunció con sus palabras:

> *"Que si algo no se puede resolver solo, nos avise en vez de adivinar mal."*

Esa regla es la que sostiene P2, P3, P4, P6 y P8. La plataforma la cumple a medias, y la mitad que
falta no se nota: **hay cosas que el sistema aparta y que no llegan a ninguna persona**. No se
pierden —quedan guardadas y contadas— pero nadie las ve nunca, que para quien tiene que decidir es
lo mismo que si se hubieran perdido.

Hoy, cuando el sistema no puede interpretar algo, pasa una de dos cosas según de dónde venga:

| De dónde viene lo apartado | Llega a la pantalla de revisión |
|---|---|
| Una fila de la lista de precios, o del historial de un producto | **Sí** |
| Una fila de la pantalla de facturas | **Sí** |
| Una fila del padrón de proveedores | **No** |
| Un comprobante de pago que no se pudo interpretar | **No** |
| Un mensaje del buzón del portal | **No** |
| Una orden de compra | **Sí** *(desde la 007 — ver Enmiendas)* |
| Una venta | **No** |

Las cuatro últimas se apartan igual que las que sí llegan, y ahí se quedan. El sistema hizo bien lo
difícil —no adivinó— y no hizo lo fácil: avisar.

Es además la diferencia entre un total en el que se puede confiar y uno que no: el brief promete que
*"cada indicador declara cuántos registros quedaron afuera"*, y un registro que quedó afuera sin que
nadie pueda verlo es una resta que no se puede explicar.

## Objetivo

Que **todo** lo que el sistema aparta llegue a una persona, con lo necesario para decidir, y que la
lista de pendientes diga la verdad: ni esconda lo que falta resolver, ni siga mostrando lo que ya se
resolvió en otro lado.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El sistema | Cada vez que aparta algo por no poder interpretarlo, lo pone en la lista de pendientes con el motivo y con lo que alcanzó a leer |
| Marcela — compras | Ve lo apartado que es de su área —proveedores, pagos, órdenes, mensajes y **precios**— y lo resuelve o lo da por revisado |
| Julián — ventas | Ve lo apartado que es de su área —ventas y rubros— y hace lo mismo |
| El dueño | Ve todo, y ve cuánto hace que algo espera |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que lo apartado se agrupa por lo que es y no por cada aparición.** Cien filas rotas
  iguales del mismo origen son **un** pendiente que dice que llegó cien veces, y no cien pendientes.
  Es lo que la plataforma ya hace con los precios, y es lo que evita que la lista sea impracticable.

- **Se asume que hay cosas que sólo se pueden dar por revisadas.** Una fila que el portal publicó
  rota no se puede arreglar desde acá —el portal es de sólo lectura y cargarla a mano quedó fuera de
  alcance en su momento—, así que lo que una persona puede hacer es verla, entenderla y dejar
  constancia de que la vio. Eso ya es más de lo que hay hoy.

- **La lista de pendientes es una sola, y no es un supuesto: está decidido** (2026-08-31). Todo
  cae en la pantalla «Revisar esto», que es donde el equipo ya entra a revisar lo de precios, y cada
  persona ve ahí lo de su área. El motivo de no partirla en varias es el que ya se pagó una vez: lo
  que hizo que nadie mirara el buzón del portal no fue que fuera largo, fue que era **otro lugar más
  al que había que acordarse de entrar**.

## Historias de usuario

### H1 — Que nada quede apartado en silencio *(prioridad más alta)*
Como **dueño**, quiero que todo lo que el sistema no pudo interpretar aparezca en la lista de
pendientes, para enterarme de lo que hoy no me entero.

**Cómo se prueba que anda:** se deja andar el sistema con datos que incluyan una fila rota de
proveedores, una de pagos, una del buzón, una de órdenes y una de ventas; las cinco aparecen en la
lista de pendientes con su motivo, y ninguna se pierde ni se cuenta como buena.

### H2 — Entender un pendiente sin salir a buscar el dato
Como **Marcela**, quiero ver junto a cada pendiente qué fue lo que el sistema alcanzó a leer y de
dónde salió, para decidir en segundos y no tener que ir a buscarlo al portal.

**Cómo se prueba que anda:** se abre un pendiente de una fila rota y se lee el pedazo de información
tal como llegó, de qué pantalla del portal salió y cuándo se leyó.

### H3 — Cada uno ve lo suyo
Como **dueño**, quiero que cada persona vea en la lista lo que es de su área, para que nadie tenga
que filtrar entre cosas que no le tocan ni pueda tocar lo que no le corresponde.

**Cómo se prueba que anda:** Marcela abre la lista y ve lo de proveedores, pagos, órdenes, mensajes
y precios; Julián ve lo de ventas y rubros; el dueño ve todo; y ninguno de los dos puede resolver un
pendiente del área del otro.

### H4 — Saber cuánto hace que algo espera
Como **dueño**, quiero ver cuántos pendientes hay y desde cuándo, para darme cuenta si la lista se
está abandonando antes de que sea un problema.

**Cómo se prueba que anda:** la pantalla dice cuántos pendientes hay en total y cuál es el más
viejo; con un pendiente de hace dos semanas sin resolver, se ve señalado como demorado.

### H5 — Que la lista no mienta cuando el trabajo se hizo en otra pantalla
Como **Julián**, quiero que un pendiente desaparezca de la lista cuando ya lo resolví en la pantalla
que le corresponde, para no tener que cerrarlo dos veces ni dudar de cuál de las dos tiene razón.

**Cómo se prueba que anda:** se corrige desde la pantalla de ventas una venta que estaba esperando;
el pendiente que la anunciaba deja de figurar entre los pendientes, sin que nadie lo cierre a mano. Y
si después esa resolución se deshace, el pendiente vuelve a figurar, tampoco a mano (RF-24).

**Por qué las ventas y no los comprobantes de pago.** Un origen puede cerrarse solo únicamente si lo
que se apartó **vuelve a aparecer** en una pantalla propia donde alguien lo resuelve, y hoy eso pasa
nada más que con las ventas: una venta que no se pudo interpretar igual queda listada en la pantalla
de ventas, y ahí se la corrige. Un comprobante de pago que no se pudo interpretar, en cambio, no
llega a ser un pago: se queda apartado —que es exactamente el silencio que esta feature viene a
romper abriéndole un pendiente— y por lo tanto **no aparece en la pantalla de comprobantes**. Lo que
se reparte ahí son los comprobantes que sí se pudieron leer, y ésos nunca tuvieron pendiente. Ver
*Fuera de alcance*.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | Cuando el sistema aparte una fila del padrón de proveedores por no poder interpretarla, debe registrarla como pendiente de revisión. | H1 |
| RF-02 | Cuando el sistema aparte un comprobante de pago por no poder interpretarlo, debe registrarlo como pendiente de revisión. | H1 |
| RF-03 | Cuando el sistema aparte un mensaje del buzón por no poder interpretarlo, debe registrarlo como pendiente de revisión. | H1 |
| RF-04 | Cuando el sistema aparte una orden de compra por no poder interpretarla, debe registrarla como pendiente de revisión. *(Ya cumplido desde la 007; esta feature lo verifica y no lo deja caer.)* | H1 |
| RF-05 | Cuando el sistema aparte una venta por no poder interpretarla, debe registrarla como pendiente de revisión. | H1 |
| RF-06 | El sistema debe mostrar en un solo lugar todo lo que quedó pendiente de revisión, cualquiera sea su origen. | H1 |
| RF-07 | Si el sistema aparta varias veces lo mismo por el mismo motivo, entonces debe mostrarlo como un solo pendiente e informar cuántas veces llegó. | H1 |
| RF-08 | El sistema debe permitir dar por revisado un pendiente, registrando quién lo hizo y cuándo. | H1 |
| RF-09 | El sistema debe mostrar, para cada pendiente, el motivo por el que no se pudo resolver solo. | H2 |
| RF-10 | El sistema debe mostrar, para cada pendiente, la información que alcanzó a leer tal como llegó. | H2 |
| RF-11 | El sistema debe mostrar, para cada pendiente, de qué sección del portal proviene y cuándo se leyó. | H2 |
| RF-12 | El sistema debe mostrar cada pendiente únicamente a quien tenga acceso al área de la que proviene. | H3 |
| RF-13 | Si alguien intenta resolver un pendiente de un área a la que no tiene acceso, entonces el sistema debe impedirlo. | H3 |
| RF-14 | El sistema debe permitir al dueño ver los pendientes de todas las áreas. | H3 |
| RF-15 | El sistema debe mostrar cuántos pendientes hay sin resolver. | H4 |
| RF-16 | El sistema debe mostrar, para cada pendiente, desde cuándo está esperando. | H4 |
| RF-17 | Si un pendiente lleva sin resolverse más días que los configurados, entonces el sistema debe señalarlo como demorado. | H4 |
| RF-18 | El sistema debe permitir al dueño definir a partir de cuántos días un pendiente se considera demorado. | H4 |
| RF-19 | Mientras el dueño no configure otro valor, el sistema debe considerar demorado un pendiente de más de siete días. | H4 |
| RF-20 | Cuando lo que originó un pendiente se resuelva en la pantalla propia de ese origen, el sistema debe dejar de contarlo entre los pendientes, sin que nadie lo cierre a mano. Hoy el único origen que tiene esa pantalla es **las ventas** (ver *Fuera de alcance*). | H5 |
| RF-21 | Cuando un pendiente deje de contarse por haberse resuelto en otra pantalla, el sistema debe registrar que se resolvió así y conservarlo consultable. | H5 |
| RF-22 | El sistema debe permitir filtrar los pendientes por el área de la que provienen. | H3 |
| RF-23 | El sistema debe conservar los pendientes ya resueltos y permitir consultarlos, sin límite de tiempo. | H1 |
| RF-24 | Cuando se deshaga, en la pantalla propia del origen, el trabajo que había hecho dejar de contar un pendiente, el sistema debe volver a contarlo entre los pendientes. | H5 |

## Reglas de negocio

- **Apartar y avisar son la misma acción.** Un dato que se aparta sin que nadie se entere es un dato
  descartado con pasos extra: la promesa del cliente no es "no lo perdimos", es "te avisamos".
- **Un pendiente no se cierra solo por el paso del tiempo.** O lo resuelve una persona, o se resuelve
  lo que lo originó. Nada se vence en silencio.
- **Lo repetido se agrupa.** Cien apariciones del mismo problema son una sola pregunta con un número
  al lado. La lista tiene que poder recorrerse en minutos o el equipo la abandona, que es
  exactamente lo que ya les pasó con el buzón del portal.
- **Lo apartado se muestra a quien puede hacer algo con eso.** Una lista llena de cosas ajenas se
  deja de mirar igual que una lista larga.
- **Hay una sola verdad sobre si algo sigue pendiente, y vale en las dos direcciones.** Si el
  trabajo se hizo en otra pantalla, la lista lo refleja **sola**; y si ese trabajo se deshace, la
  lista lo vuelve a mostrar, también sola. Una lista que sabe cerrar y no sabe reabrir dice la
  verdad sólo mientras nadie se arrepienta: dos lugares que dicen cosas distintas sobre lo mismo obligan a
  desconfiar de los dos. Se decidió el cierre automático y no el manual (2026-08-31): pedirle a
  alguien que cierre a mano algo que ya resolvió es trabajo doble, y el día que se olvide la lista
  vuelve a mentir. La constancia de quién lo resolvió no se pierde — la tiene la pantalla donde el
  trabajo se hizo.
- **Nada se borra, ni siquiera lo resuelto.** Un pendiente resuelto sale de la lista al instante y
  queda consultable para siempre: la decisión sobre un dato es lo que explica por qué ese dato es
  como es, y un sistema que la borra deja de poder contestar «¿por qué este número es este?».
- **Nada de lo que se muestra acá se corrige contra el portal.** El origen es de sólo lectura: lo
  que se decide de este lado se guarda de este lado.

## Criterios de aceptación

- [ ] **RF-01** — Con una fila del padrón que no se puede interpretar, aparece un pendiente que lo dice.
- [ ] **RF-02** — Con un comprobante de pago ilegible, aparece un pendiente que lo dice.
- [ ] **RF-03** — Con un mensaje del buzón ilegible, aparece un pendiente que lo dice.
- [ ] **RF-04** — Con una orden de compra ilegible, aparece un pendiente que lo dice *(verificación de lo ya construido)*.
- [ ] **RF-05** — Con una venta ilegible, aparece un pendiente que lo dice.
- [ ] **RF-06** — Las cinco se ven en la misma pantalla, sin entrar a cinco lugares distintos.
- [ ] **RF-07** — Cien filas rotas iguales figuran como un pendiente que dice «llegó 100 veces».
- [ ] **RF-08** — Se da por revisado un pendiente y queda con el nombre de quien lo hizo y la fecha.
- [ ] **RF-09** — Cada pendiente dice por qué el sistema no pudo resolverlo solo.
- [ ] **RF-10** — De cada pendiente se lee el pedazo de información tal como llegó.
- [ ] **RF-11** — Cada pendiente dice de qué pantalla del portal salió y cuándo se leyó.
- [ ] **RF-12** — Julián no ve entre sus pendientes los de proveedores, los de pagos ni los de precios.
- [ ] **RF-13** — Si Julián intenta resolver un pendiente de compras, el sistema no se lo permite.
- [ ] **RF-14** — El dueño abre la lista y ve los de todas las áreas.
- [ ] **RF-15** — La pantalla dice cuántos pendientes hay sin resolver.
- [ ] **RF-16** — Cada pendiente dice desde cuándo está esperando.
- [ ] **RF-17** — Un pendiente de hace dos semanas figura señalado como demorado.
- [ ] **RF-18** — El dueño cambia los días y el señalamiento pasa a usar el valor nuevo.
- [ ] **RF-19** — Sin tocar nada, un pendiente de ocho días figura demorado y uno de seis no.
- [ ] **RF-20** — Corregida una venta desde la pantalla de ventas, su pendiente deja de contarse, sin que nadie lo cierre.
- [ ] **RF-21** — Ese pendiente dice que se resolvió en la pantalla de ventas, y se lo puede seguir consultando.
- [ ] **RF-22** — El dueño pide ver sólo lo de ventas y la lista deja de mostrarle lo de proveedores y pagos.
- [ ] **RF-23** — Un pendiente resuelto hace un año se sigue encontrando, con quién lo resolvió y cuándo.
- [ ] **RF-24** — Deshecha desde la pantalla de ventas la resolución de una venta, su pendiente vuelve a figurar entre los pendientes, sin que nadie lo reabra.

## Fuera de alcance

- **Corregir el dato en el portal.** El origen es ajeno y de sólo lectura; lo que se decide acá vive
  de este lado.
- **Cargar a mano lo que llegó roto.** Una factura, una orden o una venta nacen de lo que el portal
  publicó. Escribirlas a mano desde esta pantalla es otra discusión y no está acá.
- **Aprender una regla de la decisión tomada.** La plataforma ya lo hace donde tiene sentido —los
  precios—, y extenderlo a todos los orígenes es una feature propia, no un agregado de esta.
- **Avisar por WhatsApp cuando algo queda pendiente.** Acá se trata de que exista y se vea; a quién
  se le avisa y por qué canal es materia de los avisos (**P8**).
- **Rehacer la pantalla de revisión.** Se usa la que ya existe.

- **Que un comprobante de pago retenido abra su propio pendiente.** Es lo que haría falta para que un
  comprobante pudiera cerrarse solo al repartirse, y es una feature aparte: hay que decidir qué se
  considera «retenido», y hay que medir cuántos abriría el primer día antes de soltarlo, porque una
  lista inundada se abandona, que es el fracaso exacto que esta feature quiere evitar. Lo que **sí**
  entrega esta feature del lado de los pagos es lo que promete RF-02: un comprobante que no se pudo
  interpretar deja de quedar en silencio y abre su pendiente.

## Decisiones tomadas

Las tres preguntas que esta spec dejó abiertas al escribirse se resolvieron el **2026-08-31**, y
quedan acá para que se vea qué se decidió y por qué:

| Pregunta | Decisión |
|---|---|
| ¿Una lista o una por área? | **Una sola**, la que ya existe, con filtro por área (RF-22). Cada persona ve lo suyo por su rol |
| ¿El pendiente se cierra solo o a mano cuando el trabajo se hizo en su pantalla? | **Solo** (RF-20). Cerrar a mano es trabajo doble, y olvidarse hace mentir a la lista |
| ¿Cuánto se conserva un pendiente resuelto? | **Para siempre**, fuera de la vista de pendientes pero consultable (RF-23) |

**No quedan preguntas abiertas**, así que la spec está lista para la firma del cliente.

## Enmiendas

Correcciones al documento posteriores a la firma. Una enmienda que **cambiara el alcance** exigiría
volver a firmar; las que están acá no lo cambian, y por eso la firma del 2026-08-31 sigue valiendo.

| Fecha | Qué se corrigió | Por qué no cambia el alcance |
|---|---|---|
| 2026-08-31 | **Los pendientes de precios son de Marcela, no de Julián.** Esta spec los había puesto del lado de ventas, en la tabla de actores, en el «cómo se prueba» de H3 y en dos criterios de aceptación. Contradice a `PROJECT_BRIEF.md`, que dice de Marcela, con las palabras del cliente, que sobre los precios de lista *«sí puede pedir la lista sin esperar al próximo ciclo y **resolver lo que el sistema haya apartado**»*, y que enumera lo de Julián sin los precios: *«ventas duplicadas o con datos rotos, productos sin rubro»*. Se corrigieron los cuatro lugares | **No cambia el alcance, lo restaura.** Nada de lo prometido deja de entregarse: los mismos pendientes, en la misma pantalla, con el mismo filtro. Lo único que cambia es de quién es cada uno, y vuelve a ser lo que el cliente ya había acordado en el brief — que además es lo que el sistema hace hoy y lo que fija `test_permissions.py`. Una spec que se hubiera firmado como estaba habría movido una pantalla de mano sin que el cliente se enterara |
| 2026-08-31 | **El cierre automático no tenía vuelta atrás (RF-24, nuevo).** La pantalla de ventas permite deshacer una resolución y devolver la venta a su cola; el pendiente que se había cerrado solo se quedaba cerrado, así que la lista pasaba a decir que no había nada que revisar sobre algo que sí volvía a estar en revisión. Se agregó RF-24 con su criterio de aceptación, se extendió el «cómo se prueba» de H5 y la regla de negocio pasó a decir que vale **en las dos direcciones** | **Agranda el alcance, y por eso hay que volver a firmar.** No lo pedía ningún requisito: sale de la regla de negocio ya firmada —«hay una sola verdad sobre si algo sigue pendiente»—, que sin esto se cumple sólo mientras nadie se arrepienta. Construirlo sin escribirlo lo dejaría como una capacidad que nadie pidió y que el próximo control marcaría como tal |
| 2026-08-31 | **El cierre automático se prometía con un comprobante de pago, y sólo puede darse con una venta.** RF-20, su criterio de aceptación y el «cómo se prueba» de H5 usaban de ejemplo un comprobante repartido desde la pantalla de comprobantes. Es irrealizable, y no por cómo se construyó: un comprobante que el sistema no pudo interpretar **nunca llega a esa pantalla** —se queda apartado, que es el silencio que esta feature rompe abriéndole un pendiente—, así que los que se reparten ahí son los legibles, y ésos nunca tuvieron pendiente. Se cambió el ejemplo a una venta corregida, H5 pasó a ser de Julián, RF-20 dice a qué orígenes alcanza hoy, y se agregó a *Fuera de alcance* el pendiente del comprobante retenido, que es lo que haría falta para cumplirlo del lado de pagos | **Cambia el alcance, y por eso hay que volver a firmar.** Es la única enmienda de esta spec que achica lo prometido: quien leyó «repartido un comprobante, su pendiente deja de contarse» leyó una capacidad que esta entrega no trae. Se registra en vez de resolverse sola porque la decisión entre construirlo y acotarlo **es del cliente** (`/converge` del 2026-08-31, hallazgo H-01) |
| 2026-08-31 | La tabla del problema decía que una orden de compra apartada **no** llega a la pantalla de revisión. Es falso: llega desde la 007. Se corrigió la fila y se anotó RF-04 como ya cumplido | Lo prometido no se toca —RF-04 sigue siendo un requisito de esta feature y se verifica con un test—; lo que se achica es el trabajo por construir, de cinco orígenes a cuatro. Nada de lo firmado deja de entregarse |
