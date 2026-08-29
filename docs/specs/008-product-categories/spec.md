# Rubros unificados — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Aprobado · **Feature:** 008-product-categories · **Fecha:** 2026-08-29
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-29

<!-- `/approve-spec` completa Aprobada por y Fecha de aprobación, y pasa Estado a Aprobado. -->

## Problema

Resuelve **P7 — El problema de los rubros**.

El cliente quiere saber cuánto gasta en cada tipo de producto y no puede, porque el mismo rubro está
escrito de varias maneras distintas y hay productos que no tienen ninguno.

En palabras del cliente: *"Quiero saber cuánto gasto en cada tipo de producto (cuánto en pinturas,
cuánto en herramientas, cuánto en sanitarios) y no puedo. Cada uno cargó las categorías como se le
ocurrió, y ahora tengo el mismo rubro escrito de cinco maneras y varios productos sin nada cargado.
Cuando sumo por rubro me quedan pedazos sueltos por todos lados."*

El relevamiento midió el desorden sobre la lista del proveedor: **18 formas escritas distintas que
corresponden a 7 rubros reales**, más **8 productos sin ninguna categoría cargada**. No es mucho, y
eso es lo que hace que el problema sea resoluble: alcanza con decidir qué forma escrita corresponde a
qué rubro, y decidir qué hacer con los que no tienen ninguna.

**Lo que esta feature no resuelve, y conviene decirlo primero:** el pedido del cliente empieza con
*"quiero saber cuánto gasto"*, y eso **queda afuera**. Hoy no hay de dónde sacarlo: las facturas de
compra se cargan sólo por su cabecera —número, fecha, proveedor y total— y las órdenes de compra
traen proveedor, fecha, monto y estado. Ninguna de las dos dice **qué productos** se compraron, así
que no hay manera de repartir un gasto entre rubros sin inventarlo. Esta feature deja los rubros
limpios, que es la condición para medir el gasto; **medirlo se especifica aparte**, cuando exista una
fuente que ligue lo gastado con el producto.

## Objetivo

Que cada producto quede en un rubro que el negocio reconoce, que los productos sin rubro estén a la
vista en lugar de escondidos, y que contar por rubro dé el total general sin pedazos sueltos.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El sistema | Reconoce a qué rubro corresponde cada forma escrita, aparta las que no conoce, y propone un rubro para los productos que no tienen ninguno |
| Julián — ventas | Mantiene los rubros y el catálogo: confirma o corrige las propuestas del sistema y resuelve las formas escritas nuevas |
| El dueño | Ve todo. Consulta cómo quedó clasificado el catálogo |
| Marcela — compras | Consulta los rubros para entender qué le están facturando |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **La agrupación de las 18 formas escritas en 7 rubros está medida, no supuesta**: sale de la lista
  del proveedor, y cada forma escrita cae en un solo rubro sin casos dudosos. **Los nombres son los
  de la tabla de abajo**, acordados al firmar esta spec, y son los que el dueño va a leer en sus
  propios informes. Una vez en marcha, se cambian desde el sistema (RF-06).

- **Se asume que la lista del proveedor no trae rubros que hoy no tengan ningún producto.** Si el
  negocio maneja un rubro que todavía no aparece en la lista, se agrega a mano (RF-05).

## Los rubros y sus formas escritas

Los 7 rubros acordados, con las formas en que llegan escritos y cuántos productos trae cada uno.

| Rubro | Formas en que llega escrito | Productos |
|---|---|---|
| Electricidad | `ELECTRICIDAD` · `Electricidad` | 10 |
| Ferretería General | `FERRETERIA GENERAL` · `Ferreteria General` · `Ferreteria Gral.` | 27 |
| Herramientas | `HERRAMIENTAS` · `Herramientas` · `Herram.` | 9 |
| Instrumental | `INSTRUMENTAL` · `Instrumental` | 10 |
| Pinturas y Adhesivos | `PINTURAS Y ADHESIVOS` · `Pinturas y Adhesivos` · `Pinturas/Adhesivos` | 18 |
| Sanitarios | `SANITARIOS` · `Sanitarios` | 9 |
| Seguridad Industrial | `SEGURIDAD INDUSTRIAL` · `Seguridad Industrial` · `Seg. Industrial` | 9 |
| **Sin rubro** | *(el producto llegó sin categoría)* | 8 |

Los 8 sin rubro no llegan del todo vacíos: traen una **subcategoría** cargada y limpia —Iluminación,
Medición, Cerraduras, Tornillos, Herramientas Eléctricas—, y en los 92 productos que sí tienen rubro
cada subcategoría corresponde siempre al mismo. Sobre eso se apoya la propuesta de H3.

## Historias de usuario

### H1 — Un rubro por rubro *(prioridad más alta)*
Como **Julián**, quiero que `PINTURAS Y ADHESIVOS`, `Pinturas y Adhesivos` y `Pinturas/Adhesivos`
cuenten como el mismo rubro, para dejar de tener el mismo rubro escrito de varias maneras.

**Cómo se prueba que anda:** la pantalla de rubros muestra siete rubros y no dieciocho, y al abrir
uno se ven todas las formas en que llegó escrito.

### H2 — Los que no tienen rubro, a la vista
Como **dueño**, quiero que los productos sin rubro aparezcan como una categoría más y no escondidos,
para que cuando cuente por rubro me dé el total y no me falten pedazos.

**Cómo se prueba que anda:** en cualquier corte por rubro aparece "sin rubro" con sus ocho
productos, y la suma de todos los rubros da el total general.

### H3 — Clasificar los que quedaron sueltos
Como **Julián**, quiero que el sistema me proponga un rubro para cada producto que no tiene ninguno y
poder confirmarlo o corregirlo, para vaciar la lista sin tener que pensar cada caso desde cero.

**Cómo se prueba que anda:** se abre la lista de productos sin clasificar y cada uno llega con un
rubro propuesto a partir de su subcategoría; se confirma uno, el producto pasa a ese rubro, y la
lista tiene uno menos.

### H4 — Una forma escrita nueva se pregunta, no se adivina
Como **Julián**, quiero que cuando llegue una forma de escribir un rubro que el sistema no conoce,
me lo pregunte en lugar de meterla en un cajón de "otros", para que la clasificación no se ensucie
sola con el tiempo.

**Cómo se prueba que anda:** llega un producto con una categoría nunca vista; el producto aparece en
la pantalla de revisión con esa categoría a la vista, y no queda asignado a ningún rubro por su
cuenta.

### H5 — Corregir una equivalencia mal puesta
Como **Julián**, quiero ver todas las equivalencias que el sistema está usando y poder corregir una
que quedó mal, para que un error no se propague a toda la clasificación.

**Cómo se prueba que anda:** se abre la lista de equivalencias, se cambia una de rubro, y los
productos que dependían de ella pasan al rubro correcto.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe mantener una lista de rubros del negocio. | H1 |
| RF-02 | El sistema debe asignar a cada producto el rubro que corresponde a la forma en que llegó escrita su categoría. | H1 |
| RF-03 | El sistema debe mostrar, para cada rubro, todas las formas escritas que le corresponden. | H1 |
| RF-04 | El sistema debe mostrar cuántos productos hay en cada rubro. | H1 |
| RF-05 | El sistema debe permitir al rol ventas agregar un rubro a la lista de rubros. | H1 |
| RF-06 | El sistema debe permitir al rol ventas cambiar el nombre de un rubro. | H1 |
| RF-07 | Si un rubro tiene productos asignados, entonces el sistema debe impedir eliminarlo. | H1 |
| RF-08 | El sistema debe conservar y mostrar la subcategoría con la que llegó escrito cada producto. | H1 |
| RF-09 | El sistema debe mostrar "sin rubro" como una categoría más en todo corte por rubro. | H2 |
| RF-10 | El sistema debe incluir los productos sin rubro en los totales generales. | H2 |
| RF-11 | El sistema debe mostrar cuántos productos están sin rubro. | H2 |
| RF-12 | El sistema debe permitir listar los productos sin rubro. | H2 |
| RF-13 | El sistema debe permitir al rol ventas asignar un rubro a un producto sin rubro. | H3 |
| RF-14 | Si un producto llega sin categoría pero con una subcategoría conocida, entonces el sistema debe proponer el rubro que corresponde a esa subcategoría. | H3 |
| RF-15 | El sistema debe presentar la propuesta al rol ventas para que la confirme o la corrija. | H3 |
| RF-16 | Mientras una propuesta no haya sido confirmada, el sistema no debe asignar el producto a ningún rubro. | H3 |
| RF-17 | Si un producto llega sin categoría y sin subcategoría conocida, entonces el sistema debe presentarlo para clasificar sin proponer ningún rubro. | H3 |
| RF-18 | Cuando alguien asigne un rubro a un producto, el sistema debe registrar quién lo asignó y cuándo. | H3 |
| RF-19 | Cuando un producto quede clasificado, el sistema debe dejar de mostrarlo entre los productos sin rubro. | H3 |
| RF-20 | El sistema debe permitir al rol ventas cambiar el rubro de un producto ya clasificado. | H3 |
| RF-21 | Si llega una forma escrita de categoría que el sistema no conoce, entonces el sistema debe apartar el producto para revisión. | H4 |
| RF-22 | Si llega una forma escrita de categoría que el sistema no conoce, entonces el sistema no debe asignar el producto a ningún rubro. | H4 |
| RF-23 | El sistema debe mostrar, junto a un producto apartado, la forma escrita de categoría con la que llegó. | H4 |
| RF-24 | Cuando una persona autorizada asigne una forma escrita a un rubro, el sistema debe guardar esa decisión como equivalencia. | H4 |
| RF-25 | Si un producto posterior llega con una forma escrita ya asignada a un rubro, entonces el sistema debe asignarlo a ese rubro sin apartarlo. | H4 |
| RF-26 | El sistema debe mostrar cuántos productos están pendientes de revisión por su categoría. | H4 |
| RF-27 | El sistema debe mostrar todas las equivalencias guardadas, junto con quién las decidió y cuándo. | H5 |
| RF-28 | El sistema debe permitir al rol ventas cambiar el rubro al que apunta una equivalencia guardada. | H5 |
| RF-29 | Cuando una equivalencia cambie de rubro, el sistema debe reasignar los productos que dependían de ella. | H5 |
| RF-30 | El sistema debe permitir dejar sin efecto una equivalencia guardada. | H5 |
| RF-31 | Cuando una equivalencia quede sin efecto, el sistema debe volver a apartar los productos que esa equivalencia venía resolviendo. | H5 |

## Reglas de negocio

- **"Sin rubro" es un rubro más, no un problema escondido.** Aparece en todos los cortes, con sus
  productos, para que contar por rubro dé el total general. Un total que no cierra porque hay pedazos
  afuera es exactamente lo que el cliente vino a resolver.
- **El sistema propone, la persona decide.** Sobre lo ya decidido, el sistema aplica solo. Sobre lo
  que no conoce —una forma escrita nueva, un producto sin categoría— propone con lo que tiene a mano
  y espera. Nunca asigna un rubro por su cuenta, y nunca manda nada a un cajón de "otros", que es la
  forma prolija de perder información.
- **Una decisión sobre una forma escrita se toma una sola vez.** Cuando alguien dice que
  `Pinturas/Adhesivos` es Pinturas y Adhesivos, esa decisión queda guardada y se aplica a lo que
  llegue después.
- **Una equivalencia equivocada se corrige, y la corrección alcanza a lo ya clasificado.** Si una
  forma escrita estaba apuntando al rubro que no era, cambiarla arregla todos los productos que
  dependían de ella: si no, el error queda pegado a lo viejo.
- **Los rubros los define el negocio, no el sistema.** El sistema propone reconocer lo que ya está
  escrito; cuáles son los rubros y cómo se llaman lo decide el cliente, y los nombres de la tabla de
  más arriba son los que quedaron acordados.
- **La subcategoría se guarda, pero no arma un segundo nivel.** Se conserva porque el proveedor la
  entrega limpia y sirve para proponer el rubro de un producto que no tiene ninguno, y se muestra en
  la ficha del producto. No se agrupa ni se totaliza por ella: los rubros son siete y son planos.
- **Un rubro con productos no se puede borrar.** Borrarlo dejaría productos sueltos sin que nadie lo
  haya decidido.
- **Los rubros y el catálogo los mantiene ventas.** Ya está acordado y firmado en **P10 — El problema
  de los accesos**: ventas trabaja sobre ventas, tablero, stock, rubros y catálogo.

## Criterios de aceptación

- [ ] **RF-01** — Hay una pantalla con los rubros del negocio.
- [ ] **RF-02** — Un producto que llegó con la categoría `Pinturas/Adhesivos` figura en el rubro Pinturas y Adhesivos.
- [ ] **RF-03** — Al abrir Pinturas y Adhesivos se ven las tres formas escritas que le corresponden.
- [ ] **RF-04** — Cada rubro dice cuántos productos tiene, y la suma da el total de productos.
- [ ] **RF-05** — Julián agrega un rubro nuevo y queda disponible para asignar.
- [ ] **RF-06** — Julián cambia el nombre de un rubro y el nombre nuevo aparece en todos los cortes.
- [ ] **RF-07** — Intentar borrar un rubro con productos no se permite, y el sistema dice por qué.
- [ ] **RF-08** — En la ficha de un producto se lee la subcategoría con la que llegó.
- [ ] **RF-09** — En el corte por rubro aparece "sin rubro" junto a los demás.
- [ ] **RF-10** — La suma de todos los rubros, incluido "sin rubro", da el total general.
- [ ] **RF-11** — La pantalla dice cuántos productos están sin rubro, y son los 8 del relevamiento.
- [ ] **RF-12** — Se pueden listar esos 8 productos.
- [ ] **RF-13** — Julián le asigna un rubro a un producto sin categoría y el producto pasa a ese rubro.
- [ ] **RF-14** — El producto que llegó sin categoría y con subcategoría `Tornillos` se presenta con Ferretería General propuesto.
- [ ] **RF-15** — Julián confirma esa propuesta en un caso y la corrige en otro, y las dos decisiones se aplican.
- [ ] **RF-16** — Un producto con propuesta sin confirmar sigue figurando en "sin rubro".
- [ ] **RF-17** — Un producto sin categoría y sin subcategoría aparece para clasificar, sin ninguna propuesta.
- [ ] **RF-18** — Esa asignación figura con su nombre y la fecha.
- [ ] **RF-19** — La lista de productos sin rubro tiene uno menos.
- [ ] **RF-20** — Julián cambia el rubro de un producto ya clasificado y el cambio se refleja en los cortes.
- [ ] **RF-21** — Un producto con una categoría nunca vista aparece en la pantalla de revisión.
- [ ] **RF-22** — Ese producto no quedó asignado a ningún rubro por decisión del sistema.
- [ ] **RF-23** — En la revisión se lee con qué categoría llegó escrito.
- [ ] **RF-24** — Asignada esa forma escrita a un rubro, la decisión queda guardada.
- [ ] **RF-25** — El próximo producto con esa misma forma escrita entra directo al rubro, sin revisión.
- [ ] **RF-26** — La pantalla dice cuántos productos están pendientes por su categoría.
- [ ] **RF-27** — Hay una pantalla con todas las equivalencias, cada una con quién y cuándo.
- [ ] **RF-28** — Se cambia una equivalencia de rubro desde esa pantalla.
- [ ] **RF-29** — Los productos que dependían de esa equivalencia aparecen en el rubro nuevo.
- [ ] **RF-30** — Una equivalencia se puede dejar sin efecto.
- [ ] **RF-31** — Dejada sin efecto, los productos que resolvía vuelven a la pantalla de revisión.

## Fuera de alcance

- **El gasto por rubro.** Es la mitad del pedido original de P7 y **sale de esta feature**, porque hoy
  no hay de dónde sacarlo: las facturas de compra se cargan sólo por su cabecera (**P2**) y las
  órdenes de compra traen proveedor, fecha, monto y estado (**P6**); ninguna dice qué productos se
  compraron. Repartir un total entre rubros sin ese dato sería inventarlo. Se especifica como feature
  aparte cuando exista una fuente que ligue el gasto con el producto, y esta feature es su condición
  previa: sin los rubros unificados, ese corte no se puede construir igual.
- **Que el sistema decida solo a qué rubro corresponde una forma escrita que no conoce.** Propone
  sobre lo que ya está decidido; lo nuevo lo confirma una persona.
- **Sub-rubros o categorías anidadas.** El cliente habló de siete rubros planos. La subcategoría se
  guarda y se muestra (RF-08), pero no se agrupa ni se totaliza por ella.
- **El detalle de artículos de las facturas.** Sigue fuera de alcance, como en **P2**: 46 de cada 100
  facturas llegan escaneadas y leer su lista de artículos daría un error demasiado alto.
- **El tablero del negocio.** **P3 — El problema de no ver nada**.
- **Los rubros de venta o el margen por rubro.**
- **Cambiar la categoría de un producto en el portal del proveedor.** El origen es de sólo lectura;
  la clasificación vive del lado nuevo.
