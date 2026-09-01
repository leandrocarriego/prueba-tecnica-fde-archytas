# Quién mantiene los rubros — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Aprobado · **Feature:** 010-category-ownership · **Fecha:** 2026-08-30
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-31

## Problema

Corrige una parte de lo acordado en **P10 — El problema de los accesos**, a la luz de lo que
apareció al construir **P7 — El problema de los rubros**.

Cuando se definieron los accesos, los rubros quedaron del lado de **ventas**, junto al catálogo:
*"ventas trabaja sobre ventas, tablero, stock, rubros y catálogo"*. Y en el mismo acuerdo, entre las
revisiones que le tocan a Julián, quedaron también *"los productos sin rubro"*. La feature de rubros
heredó las dos frases y quedó escrita entera desde él: él agrega un rubro, él clasifica los productos
que llegaron sin ninguno, él decide qué significa una forma escrita nueva.

Al construirlo se vio que no es así. **El rubro es la categoría con la que se compra.** El dueño
compra una pinza para revenderla en la ferretería, y esa pinza es Herramientas desde el momento en
que la compra. Quien ve llegar esa pinza —en la lista del proveedor, en la factura, en la orden de
compra— es **compras**. Pedirle a ventas que decida a qué rubro corresponde algo que todavía no
llegó al salón es pedirle una decisión que no es suya.

Hoy el sistema queda partido a la mitad: la pantalla de rubros le pide las decisiones a ventas, y
la cola donde aparecen las formas escritas nuevas es de compras. Ninguna de las dos personas puede
completar el circuito sola.

**Esta spec corrige el acuerdo, no agrega funcionalidad.** Todo lo que los rubros hacen ya está
definido y firmado en la feature de rubros; lo único que cambia es **quién lo hace**. En los tres
casos en que aquel acuerdo no dijo quién —eliminar un rubro, guardar una equivalencia y dejarla sin
efecto— esta spec lo dice, y eso tampoco agrega una capacidad: las tres ya estaban acordadas, sin
dueño. Donde esta spec y la de rubros digan cosas distintas sobre quién mantiene un rubro, gana
esta, que es posterior, y cada requisito de acá dice a cuál de allá reemplaza.

## Objetivo

Que los rubros los mantenga quien compra, que ventas los siga viendo para vender, y que el circuito
de una forma escrita nueva —desde que aparece hasta que queda decidida— lo pueda cerrar una sola
persona.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| Marcela — compras | Pasa a mantener los rubros: los agrega, los renombra, clasifica los productos sin rubro y decide qué significa cada forma escrita nueva |
| Julián — ventas | Consulta los rubros del catálogo del que vende, y deja de poder cambiarlos |
| El dueño | Ve todo y hace todo, como en todas las secciones |
| El sistema | Deja pasar el cambio sólo a quien corresponde, y lo rechaza aunque el botón no esté a la vista |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que ventas conserva la consulta de los rubros.** Julián vende desde ese catálogo y
  necesita saber en qué rubro cae cada producto; lo que pierde es la posibilidad de cambiarlo. Es
  el mismo trato que ya tiene con los precios de lista, que ve y no toca. Si el negocio prefiere
  que deje de verlos, se dice al firmar.

- **Se asume que el catálogo sigue siendo de ventas.** Sólo se mueven los rubros. Julián sigue
  corrigiendo la descripción de un producto, y a partir de esta spec ya no su rubro. Es una
  consecuencia deliberada y vale decirla en voz alta: **rubros y catálogo dejan de viajar juntos**,
  que es como los había atado el acuerdo de los accesos.

## Historias de usuario

### H1 — Compras mantiene los rubros *(prioridad más alta)*
Como **Marcela**, quiero agregar rubros, clasificar los productos que llegaron sin ninguno y decidir
qué significa una forma escrita que el sistema no conoce, para poder cerrar sola el circuito de lo
que veo llegar sin tener que pedírselo a ventas.

**Cómo se prueba que anda:** Marcela entra con su acceso, encuentra los rubros entre lo que le toca,
agrega uno, le asigna un rubro a un producto que no tenía, y resuelve una forma escrita nueva desde
la misma pantalla donde ya resuelve lo que la actualización aparta.

### H2 — Ventas los sigue viendo, sin poder cambiarlos
Como **Julián**, quiero seguir viendo en qué rubro cae cada producto, para vender sabiendo lo que
vendo, aunque ya no sea yo quien los mantiene.

**Cómo se prueba que anda:** Julián entra con su acceso, abre los rubros y los ve con su conteo y
sus formas escritas, y no encuentra ninguna acción para cambiarlos. Si el pedido se manda igual, el
sistema lo rechaza.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe permitir al rol compras agregar un rubro a la lista de rubros. | H1 |
| RF-02 | El sistema debe permitir al rol compras cambiar el nombre de un rubro. | H1 |
| RF-03 | El sistema debe permitir al rol compras eliminar un rubro que no tenga productos asignados. | H1 |
| RF-04 | El sistema debe permitir al rol compras asignar un rubro a un producto sin rubro. | H1 |
| RF-05 | El sistema debe permitir al rol compras cambiar el rubro de un producto ya clasificado. | H1 |
| RF-06 | El sistema debe permitir al rol compras asignar a un rubro una forma escrita de categoría que el sistema no conocía. | H1 |
| RF-07 | El sistema debe permitir al rol compras cambiar el rubro al que apunta una equivalencia guardada. | H1 |
| RF-08 | El sistema debe permitir al rol compras dejar sin efecto una equivalencia guardada. | H1 |
| RF-09 | El sistema debe mostrar los rubros al rol compras entre las secciones a las que entra. | H1 |
| RF-10 | El sistema debe permitir al rol ventas consultar los rubros, sus formas escritas y cuántos productos tiene cada uno. | H2 |
| RF-11 | Si el rol ventas pide cambiar un rubro, la clasificación de un producto o una equivalencia, entonces el sistema debe rechazar el pedido. | H2 |
| RF-12 | El sistema no debe ofrecer al rol ventas ninguna acción para cambiar un rubro, una clasificación o una equivalencia. | H2 |
| RF-13 | El sistema debe presentar al rol compras la propuesta de rubro de un producto sin rubro, para que la confirme o la corrija. | H1 |
| RF-14 | El sistema debe mostrar al rol compras las formas escritas de categoría que no conoce en la misma pantalla de revisión donde resuelve lo que la actualización aparta. | H1 |

### A qué requisito de la feature de rubros reemplaza cada uno

La regla de precedencia de más arriba alcanza a lo que las dos specs digan distinto. Para que no
quede a interpretación, acá está dicho uno por uno. Ninguno de estos reemplazos cambia lo que el
sistema hace: cambia de quién es.

| Requisito de esta spec | Requisito que reemplaza en «Rubros unificados» |
|---|---|
| RF-01 | RF-05 — agregar un rubro |
| RF-02 | RF-06 — cambiar el nombre de un rubro |
| RF-03 | RF-07 — eliminar un rubro. Allá se dijo cuándo no se puede; acá se dice además quién puede |
| RF-04 | RF-13 — asignar un rubro a un producto sin rubro |
| RF-05 | RF-20 — cambiar el rubro de un producto ya clasificado |
| RF-06 | RF-24 — asignar una forma escrita a un rubro y guardar esa decisión |
| RF-07 | RF-28 — cambiar el rubro al que apunta una equivalencia |
| RF-08 | RF-30 — dejar sin efecto una equivalencia |
| RF-13 | RF-15 — presentar la propuesta para que se la confirme o se la corrija |

Todo lo demás de la feature de rubros queda como está firmado.

## Reglas de negocio

- **Los rubros los mantiene compras.** Es la corrección del acuerdo de los accesos, que los había
  puesto del lado de ventas. El rubro es la categoría de lo que se compra para revender, y quien ve
  llegar la mercadería es quien está en condiciones de decir a qué rubro corresponde.
- **El catálogo sigue siendo de ventas.** Se mueven los rubros y nada más. Es la primera vez que las
  dos cosas se separan, y es a propósito.
- **Ventas ve y no cambia.** Es el mismo trato que ya tiene con los precios de lista y con el
  calendario. Y esconder el botón no alcanza: el sistema rechaza el cambio igual, como quedó
  acordado al definir los accesos.
- **El dueño sigue haciendo todo.** Ninguna sección se le cierra, y esta tampoco.
- **La cola de revisión vuelve a tener un solo dueño.** Todo lo que la actualización nocturna
  aparta —una fila ilegible, un producto desconocido, una forma escrita de categoría que nadie
  decidió— lo resuelve la misma persona, en la misma pantalla. No es nuevo: al definir los accesos
  ya se acordó que resolver lo que el sistema aparta es del dueño y de compras. Lo que faltaba era
  que las formas escritas de categoría cayeran de ese mismo lado, y eso lo dice RF-14.
- **Los rubros los define el negocio, no el sistema.** No cambia con esta spec: cambia quién los
  define de este lado.

## Criterios de aceptación

- [ ] **RF-01** — Marcela agrega un rubro nuevo y queda disponible para asignar.
- [ ] **RF-02** — Marcela cambia el nombre de un rubro y el nombre nuevo aparece en todos los cortes.
- [ ] **RF-03** — Marcela elimina un rubro vacío; sobre uno con productos, el sistema lo sigue impidiendo y dice por qué.
- [ ] **RF-04** — Marcela le asigna un rubro a un producto que no tenía, y el producto pasa a ese rubro.
- [ ] **RF-05** — Marcela cambia el rubro de un producto ya clasificado y el cambio se refleja en los cortes.
- [ ] **RF-06** — Llega un producto con una categoría nunca vista; Marcela la asigna a un rubro y la decisión queda guardada.
- [ ] **RF-07** — Marcela cambia una equivalencia de rubro y los productos que dependían de ella pasan al rubro nuevo.
- [ ] **RF-08** — Marcela deja sin efecto una equivalencia y los productos que resolvía vuelven a la pantalla de revisión.
- [ ] **RF-09** — Marcela entra con su acceso y encuentra los rubros entre las secciones a las que entra.
- [ ] **RF-10** — Julián abre los rubros y los ve con su conteo y sus formas escritas.
- [ ] **RF-11** — Julián manda igual el pedido de cambiar un rubro y el sistema lo rechaza.
- [ ] **RF-12** — En la pantalla de Julián no hay ningún botón para agregar, renombrar, eliminar, clasificar ni corregir.
- [ ] **RF-13** — Marcela confirma la propuesta de un producto sin rubro y corrige la de otro, y las dos decisiones se aplican.
- [ ] **RF-14** — Marcela abre la pantalla donde resuelve lo que la actualización apartó y encuentra ahí también las formas escritas de categoría que el sistema no conoce, sin cambiar de sección.

## Fuera de alcance

- **El catálogo y las correcciones de producto.** Siguen siendo de ventas, tal como quedaron
  acordadas. Acá sólo se mueven los rubros.
- **Cambiar lo que los rubros hacen.** Unificar las formas escritas, mostrar «sin rubro» en todo
  corte, proponer un rubro por la subcategoría, preguntar en vez de adivinar: todo eso está firmado
  en la feature de rubros y sigue funcionando igual. De la propuesta por subcategoría cambia una
  sola cosa, y es a quién se le presenta (RF-13). Esta spec cambia **quién**, no **qué**.
- **El gasto por rubro.** Sigue afuera por la misma razón de siempre: las facturas de compra se
  cargan por su cabecera y no dicen qué productos se compraron.
- **Los tres roles.** Siguen siendo tres y siguen siendo fijos. No se crea un rol nuevo ni se arma
  una pantalla para inventar roles.
- **El stock y el tablero.** Siguen de ventas.

## Lo que se confirmó al firmar

<!--
  Esta sección era «Preguntas abiertas» y ya no lo es: las cuatro decisiones que
  listaba quedaron confirmadas con la firma del 2026-08-31, y así consta abajo.
  No se borró porque cada una nombra la alternativa que se descartó, y esa es la
  parte que hay que poder releer cuando alguien pregunte por qué quedó así.
-->

Ninguna pregunta sin responder trabó la firma. Sí había cuatro decisiones tomadas mirando lo que ya
estaba acordado, y no preguntándoselas al cliente: se pusieron sobre la mesa para que firmar fuera
firmarlas.

**Las cuatro quedaron confirmadas el 2026-08-31 por Leandro Carriego — FDE**, en el mismo acto que
aprobó esta spec, y ninguna de las alternativas que cada una ofrecía se tomó. Se dejan escritas tal
como se leyeron, con la alternativa que se descartó incluida.

### Confirmadas con la firma del 2026-08-31

- **Los productos sin rubro también pasan a compras, no sólo los rubros.** El acuerdo de los accesos
  los había dejado entre las revisiones de ventas —*"resuelve las revisiones humanas de su lado
  (ventas duplicadas o con datos rotos, productos sin rubro)"*—, y esta spec los mueve junto con el
  resto (H1, RF-04, RF-05, RF-13), por la misma razón por la que mueve los rubros: el rubro es la
  categoría de lo que se compra. **Si clasificar un producto tiene que seguir siendo de Julián**, se
  dice al firmar, y el circuito vuelve a necesitar dos personas.

- **La propuesta de rubro la confirma compras.** La feature de rubros dice que el sistema se la
  presenta a ventas para que la confirme o la corrija; como acá ventas deja de tener ninguna acción
  para clasificar, ese requisito quedaba sin nadie que lo cumpla. Lo reemplaza RF-13, que es el mismo
  requisito con el actor cambiado. **Si la propuesta la tiene que seguir confirmando ventas**, hay
  que revisar también RF-12, porque confirmar una propuesta es clasificar.

- **Las formas escritas nuevas se resuelven donde compras ya resuelve lo apartado.** Es lo que
  prometen el objetivo y H1, y ningún requisito lo decía: ahora lo dice RF-14. No es una decisión
  nueva —al definir los accesos ya se acordó que resolver lo que el sistema aparta es del dueño y de
  compras, y así está construido—. **Si se prefiere una pantalla aparte sólo para los rubros**, se
  dice al firmar: deja de ser una sola cola con un solo dueño.

- **Eliminar un rubro, guardar una equivalencia y dejarla sin efecto quedan de compras.** La feature
  de rubros acordó las tres sin decir quién las hace, y acá quedan donde quedó todo lo demás (RF-03,
  RF-06, RF-08). **Si alguna tiene que ser sólo del dueño**, se dice al firmar.
