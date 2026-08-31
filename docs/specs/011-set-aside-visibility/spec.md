# Lo apartado se ve — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
-->

**Estado:** Aprobado · **Feature:** 011-set-aside-visibility · **Fecha:** 2026-08-31
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-31

## Problema

No resuelve uno de los doce problemas: resuelve **el problema de fondo**, el que el brief pone antes
que los doce y que el cliente enunció con sus palabras:

> *"Que si algo no se puede resolver solo, nos avise en vez de adivinar mal."*

Esa regla es la que sostiene P2, P3, P4, P6 y P8. La plataforma la cumple a medias, y la mitad que
falta no se nota: **hay cosas que el sistema aparta y que no llegan a ninguna persona**. No se
pierden —quedan guardadas y contadas— pero nadie las ve nunca, que para quien tiene que decidir es
lo mismo que si se hubieran perdido.

Hoy, cuando el sistema no puede interpretar algo, pasa una de tres cosas según de dónde venga:

| De dónde viene lo apartado | Llega a la pantalla de revisión |
|---|---|
| Una fila de la lista de precios, o del historial de un producto | **Sí** |
| Una fila de la pantalla de facturas | **Sí** |
| Una fila del padrón de proveedores | **No** |
| Un comprobante de pago que no se pudo interpretar | **No** |
| Un mensaje del buzón del portal | **No** |
| Una orden de compra | **No** |
| Una venta | **No** |

Las cinco últimas se apartan igual que las tres primeras, y ahí se quedan. El sistema hizo bien lo
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
| Marcela — compras | Ve lo apartado que es de su área —proveedores, pagos, órdenes, mensajes— y lo resuelve o lo da por revisado |
| Julián — ventas | Ve lo apartado que es de su área —precios y ventas— y hace lo mismo |
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

**Cómo se prueba que anda:** Marcela abre la lista y ve lo de proveedores, pagos, órdenes y mensajes;
Julián ve lo de precios y ventas; el dueño ve todo; y ninguno de los dos puede resolver un pendiente
del área del otro.

### H4 — Saber cuánto hace que algo espera
Como **dueño**, quiero ver cuántos pendientes hay y desde cuándo, para darme cuenta si la lista se
está abandonando antes de que sea un problema.

**Cómo se prueba que anda:** la pantalla dice cuántos pendientes hay en total y cuál es el más
viejo; con un pendiente de hace dos semanas sin resolver, se ve señalado como demorado.

### H5 — Que la lista no mienta cuando el trabajo se hizo en otra pantalla
Como **Marcela**, quiero que un pendiente desaparezca de la lista cuando ya lo resolví en la pantalla
que le corresponde, para no tener que cerrarlo dos veces ni dudar de cuál de las dos tiene razón.

**Cómo se prueba que anda:** se reparte un comprobante que estaba esperando desde la pantalla de
comprobantes; el pendiente que lo anunciaba deja de figurar entre los pendientes, sin que nadie lo
cierre a mano.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | Cuando el sistema aparte una fila del padrón de proveedores por no poder interpretarla, debe registrarla como pendiente de revisión. | H1 |
| RF-02 | Cuando el sistema aparte un comprobante de pago por no poder interpretarlo, debe registrarlo como pendiente de revisión. | H1 |
| RF-03 | Cuando el sistema aparte un mensaje del buzón por no poder interpretarlo, debe registrarlo como pendiente de revisión. | H1 |
| RF-04 | Cuando el sistema aparte una orden de compra por no poder interpretarla, debe registrarla como pendiente de revisión. | H1 |
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
| RF-20 | Cuando lo que originó un pendiente se resuelva en otra pantalla, el sistema debe dejar de contarlo entre los pendientes. | H5 |
| RF-21 | Cuando un pendiente deje de contarse por haberse resuelto en otra pantalla, el sistema debe registrar que se resolvió así y conservarlo consultable. | H5 |
| RF-22 | El sistema debe permitir filtrar los pendientes por el área de la que provienen. | H3 |
| RF-23 | El sistema debe conservar los pendientes ya resueltos y permitir consultarlos, sin límite de tiempo. | H1 |

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
- **Hay una sola verdad sobre si algo sigue pendiente.** Si el trabajo se hizo en otra pantalla, la
  lista lo refleja **sola**: dos lugares que dicen cosas distintas sobre lo mismo obligan a
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
- [ ] **RF-04** — Con una orden de compra ilegible, aparece un pendiente que lo dice.
- [ ] **RF-05** — Con una venta ilegible, aparece un pendiente que lo dice.
- [ ] **RF-06** — Las cinco se ven en la misma pantalla, sin entrar a cinco lugares distintos.
- [ ] **RF-07** — Cien filas rotas iguales figuran como un pendiente que dice «llegó 100 veces».
- [ ] **RF-08** — Se da por revisado un pendiente y queda con el nombre de quien lo hizo y la fecha.
- [ ] **RF-09** — Cada pendiente dice por qué el sistema no pudo resolverlo solo.
- [ ] **RF-10** — De cada pendiente se lee el pedazo de información tal como llegó.
- [ ] **RF-11** — Cada pendiente dice de qué pantalla del portal salió y cuándo se leyó.
- [ ] **RF-12** — Julián no ve entre sus pendientes los de proveedores ni los de pagos.
- [ ] **RF-13** — Si Julián intenta resolver un pendiente de compras, el sistema no se lo permite.
- [ ] **RF-14** — El dueño abre la lista y ve los de todas las áreas.
- [ ] **RF-15** — La pantalla dice cuántos pendientes hay sin resolver.
- [ ] **RF-16** — Cada pendiente dice desde cuándo está esperando.
- [ ] **RF-17** — Un pendiente de hace dos semanas figura señalado como demorado.
- [ ] **RF-18** — El dueño cambia los días y el señalamiento pasa a usar el valor nuevo.
- [ ] **RF-19** — Sin tocar nada, un pendiente de ocho días figura demorado y uno de seis no.
- [ ] **RF-20** — Repartido un comprobante desde su pantalla, su pendiente deja de contarse, sin que nadie lo cierre.
- [ ] **RF-21** — Ese pendiente dice que se resolvió al repartirse, y se lo puede seguir consultando.
- [ ] **RF-22** — El dueño pide ver sólo lo de compras y la lista deja de mostrarle lo de precios.
- [ ] **RF-23** — Un pendiente resuelto hace un año se sigue encontrando, con quién lo resolvió y cuándo.

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

## Decisiones tomadas

Las tres preguntas que esta spec dejó abiertas al escribirse se resolvieron el **2026-08-31**, y
quedan acá para que se vea qué se decidió y por qué:

| Pregunta | Decisión |
|---|---|
| ¿Una lista o una por área? | **Una sola**, la que ya existe, con filtro por área (RF-22). Cada persona ve lo suyo por su rol |
| ¿El pendiente se cierra solo o a mano cuando el trabajo se hizo en su pantalla? | **Solo** (RF-20). Cerrar a mano es trabajo doble, y olvidarse hace mentir a la lista |
| ¿Cuánto se conserva un pendiente resuelto? | **Para siempre**, fuera de la vista de pendientes pero consultable (RF-23) |

**No quedan preguntas abiertas**, así que la spec está lista para la firma del cliente.
