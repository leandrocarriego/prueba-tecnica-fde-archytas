# Sistema de diseño — Especificación

**Estado:** Aprobado · **Feature:** 012-design-system · **Fecha:** 2026-08-31
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-31
**Enmendada y vuelta a firmar:** 2026-08-31 — Leandro Carriego (FDE), por el alta de `RF-24`
(ver *Enmiendas*)

## Problema

La plataforma se construyó feature por feature, y cada una resolvió su aspecto por su cuenta. El
resultado es que dieciséis secciones que son el mismo producto no se parecen entre sí: el mismo
estado —una factura vencida, un dato sin confirmar— se dibuja de tres maneras distintas según la
pantalla,
los montos se leen con la misma tipografía que el texto y no se alinean en columna, y el color se
usa a veces para avisar y a veces para adornar. Cuando todo puede ser importante, nada lo es.

Eso tiene un costo concreto para el negocio, y no es estético. La promesa que atraviesa los doce
problemas del brief es **"si algo no se puede resolver solo, avisame"**: un aviso sólo cumple esa
promesa si se distingue de un adorno de un vistazo. Hoy no se distingue.

Hay además una guía visual acordada —"taller ordenado"— que hasta ahora vivía como tres archivos
de diseño que nadie estaba obligado a mirar.

## Objetivo

Que la plataforma se vea y se lea como **una sola herramienta de trabajo**: los mismos estados con
la misma forma en todas las pantallas, la plata siempre legible en columna, y el naranja reservado
para una única cosa —"acá hay algo que decidir vos"— de modo que quien la usa aprenda el código de
colores una vez y le sirva para siempre.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| Dueño | Recorre el tablero, el calendario y los proveedores; es quien más necesita distinguir de un vistazo lo confiable de lo dudoso |
| Compras | Trabaja todo el día sobre facturas, pagos y órdenes: es quien más veces por día lee montos y fechas en columna |
| Ventas | Revisa ventas y catálogo; ve las mismas señales de estado que los demás, con las mismas formas |
| El sistema | Presenta cada dato con la señal que le corresponde, y no inventa una nueva por pantalla |

## Historias de usuario

### H1 — Todas las pantallas hablan el mismo idioma visual *(prioridad más alta)*
Como **cualquier persona del negocio**, quiero que **todas las pantallas usen los mismos colores,
la misma tipografía y las mismas formas**, para **no tener que aprender de nuevo cómo se lee cada
pantalla**.

**Cómo se prueba que anda:** se recorren las dieciséis secciones del menú una tras otra, más Mi
cuenta y las pantallas de ingreso, y ninguna desentona: mismo fondo, mismos títulos, mismas
tarjetas, mismos bordes.

### H2 — Cada estado se dibuja siempre igual
Como **quien revisa facturas**, quiero que **"saldada", "parcial", "vencida" y "sin confirmar" se
vean igual en toda la plataforma**, para **reconocer el estado sin leer la etiqueta**.

**Cómo se prueba que anda:** se busca una factura vencida en el listado, en el calendario y en la
ficha del proveedor: la señal es la misma pastilla roja en los tres lugares.

### H3 — La plata y las fechas se leen en columna
Como **quien controla pagos**, quiero que **los montos, las fechas y los códigos estén en una
tipografía de ancho fijo**, para **comparar una columna de números de un vistazo, sin seguirlos con
el dedo**.

**Cómo se prueba que anda:** en cualquier tabla con importes, las comas y los últimos dígitos
quedan alineados verticalmente aunque los números tengan distinta cantidad de cifras.

### H4 — Una sola acción naranja por pantalla
Como **quien tiene que decidir**, quiero que **en cada pantalla haya un solo botón naranja, y que
sea el que resuelve lo que vine a hacer**, para **saber dónde tengo que apretar sin leer todo**.

**Cómo se prueba que anda:** en cualquier pantalla hay como mucho un botón naranja; el resto son de
contorno, grises o enlaces. En las pantallas que listan casos para resolver —Revisar esto, el
calendario— no hay ninguno: la acción de cada caso va en tinta o contorno.

### H5 — El aviso va antes que el número
Como **el dueño**, quiero que **cuando un total dejó cosas afuera por dudosas, el aviso aparezca
arriba del número y no al pie**, para **no leer un número y enterarme después de que no era
confiable**.

**Cómo se prueba que anda:** en el tablero, con doce casos sin resolver, la franja de aviso está
visible antes que los importes, y ofrece el enlace para ir a resolverlos.

### H6 — La barra lateral muestra sólo lo que puedo abrir
Como **alguien de Ventas**, quiero que **el menú no me ofrezca secciones que no puedo abrir**, para
**no chocar con una negativa después de hacer clic**.

**Cómo se prueba que anda:** se entra con un acceso de Ventas y el menú no lista Facturas, Órdenes
de compra ni Accesos; tampoco aparece el grupo que quedó vacío.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe presentar todas sus pantallas —las dieciséis secciones del menú, Mi cuenta y las pantallas de sesión— con la paleta, la tipografía, los espaciados y los radios definidos en la guía visual acordada. | H1 |
| RF-02 | El sistema debe usar un único color de fondo de aplicación y un único color de tarjeta en todas las pantallas del área privada. | H1 |
| RF-03 | El sistema debe presentar el menú principal como una barra lateral fija, agrupada por área del negocio, con la sección actual señalada. | H1 |
| RF-04 | El sistema debe mostrar en todo momento, dentro de esa barra, el nombre de la persona con la sesión abierta y la salida para cerrarla. | H1 |
| RF-05 | El sistema debe presentar las pantallas de ingreso, invitación y recuperación de contraseña con la misma identidad visual que el resto. | H1 |
| RF-06 | El sistema debe dibujar cada estado de un dato con una única forma —una pastilla— y un único color por estado en todas las pantallas. | H2 |
| RF-07 | El sistema debe reservar cinco significados de color para el estado de un dato, y no usarlos para nada más: conforme, informativo, requiere decisión, vencido o con error, y sin novedad, y no debe usar el acento naranja para señalar un estado, porque señala la acción que resuelve la pantalla (RF-11). | H2 |
| RF-08 | El sistema debe distinguir visualmente un dato leído del origen y todavía sin confirmar por una persona, de un dato ya confirmado. | H2 |
| RF-09 | El sistema debe mostrar los importes, las fechas y los códigos en tipografía de ancho fijo con cifras de ancho uniforme. | H3 |
| RF-10 | Mientras una tabla muestre una columna de importes, el sistema debe alinearla de modo que las cifras queden en columna. | H3 |
| RF-11 | El sistema debe mostrar como mucho un botón de acción naranja por pantalla, y debe ser el que resuelve la tarea principal de esa pantalla. | H4 |
| RF-12 | El sistema debe presentar toda acción secundaria como botón de contorno, botón gris o enlace, nunca en naranja. | H4 |
| RF-13 | El sistema debe usar el color de enlace únicamente para navegar o consultar, y nunca para una acción que modifica datos. | H4 |
| RF-14 | Cuando una pantalla muestre un total que dejó registros afuera por dudosos, el sistema debe mostrar el aviso correspondiente por encima de ese total. | H5 |
| RF-15 | El sistema debe acompañar todo aviso con la acción que permite resolverlo. | H5 |
| RF-16 | Si un indicador del tablero no dejó ningún registro afuera, entonces el sistema debe decirlo explícitamente en lugar de no mostrar nada. | H5 |
| RF-17 | El sistema debe ocultar del menú las secciones que la persona con la sesión abierta no puede abrir. | H6 |
| RF-18 | Si un grupo del menú queda sin ninguna sección visible, entonces el sistema debe ocultar también el título del grupo. | H6 |
| RF-19 | El sistema debe mostrar los estados de carga, de error y de lista vacía con la misma forma en todas las pantallas. | H1 |
| RF-20 | El sistema debe presentar sus pantallas en un solo tema claro, sin cambiarlo según la configuración del dispositivo. | H1 |
| RF-21 | Mientras una pantalla liste casos que requieren una decisión, el sistema debe presentar la acción de cada caso en tinta o contorno, y no debe mostrar ningún botón naranja en esa pantalla. | H4 |
| RF-22 | El sistema debe ofrecer la sección de Ventas como una entrada más del menú principal, visible para quien pueda abrirla. | H6 |
| RF-23 | Fuera del tablero, si un total no dejó ningún registro afuera, entonces el sistema no debe mostrar ningún aviso sobre ese total. | H5 |
| RF-24 | Cuando una persona entra a la plataforma, el sistema debe dejarla directamente en el tablero, sin una pantalla de bienvenida en el medio. | H1 |

## Reglas de negocio

- **El color se gana, no se reparte.** Un color aparece cuando comunica el estado de un dato o una
  decisión pendiente. Un color que decora le quita fuerza al que avisa.
- **El naranja significa una sola cosa:** "acá tenés que decidir vos". Por eso hay uno por pantalla,
  y en una pantalla que es una lista de decisiones no hay ninguno: si cada caso pintara su botón de
  naranja, el naranja dejaría de señalar algo.
- **Lo dudoso se muestra aparte y antes.** Ningún número se presenta como confiable si se calculó
  dejando registros afuera: el aviso va arriba, con su salida.
- **Lo que no se puede ver, no aparece.** Los permisos se resuelven ocultando la entrada del menú,
  no mostrando un botón que después devuelve una negativa.
- **Los cambios son de presentación.** Esta feature no cambia ningún cálculo, ninguna regla de
  negocio ni ningún permiso: cambia cómo se muestra lo que ya se decidió.

## Criterios de aceptación

- [ ] **RF-01** — Se recorren las dieciséis secciones del menú, Mi cuenta y las pantallas de
      ingreso, y todas coinciden con la guía visual acordada en fondo, tipografía, tamaños de
      título y estilo de tarjeta; ninguna queda con el aspecto anterior.
- [ ] **RF-02** — No hay pantalla del área privada con un fondo distinto al del resto.
- [ ] **RF-03** — El menú está a la izquierda en todas las pantallas, agrupado, y la sección que se
      está mirando aparece resaltada.
- [ ] **RF-04** — El nombre de quien está trabajando y el botón de cerrar sesión se ven sin abrir
      ningún menú desplegable.
- [ ] **RF-05** — La pantalla de ingreso usa los mismos colores y la misma tipografía que el resto.
- [ ] **RF-06** — Un mismo estado se busca en tres pantallas distintas y se ve idéntico en las tres.
- [ ] **RF-07** — No aparece ningún color de estado fuera de los cinco significados acordados, y el
      naranja no se usa para marcar un estado.
- [ ] **RF-08** — Un dato sin confirmar se distingue a simple vista de uno confirmado, sin leer.
- [ ] **RF-09** — Los importes, las fechas y los códigos se ven en tipografía de ancho fijo.
- [ ] **RF-10** — En una tabla con importes de distinta cantidad de cifras, las cifras quedan
      alineadas verticalmente.
- [ ] **RF-11** — En cada pantalla se cuenta como mucho un botón naranja, y es el de la tarea
      principal.
- [ ] **RF-12** — Ninguna acción secundaria aparece en naranja.
- [ ] **RF-13** — Ningún botón que guarda, corrige o borra usa el color de enlace.
- [ ] **RF-14** — En el tablero con casos sin resolver, el aviso se lee antes que los importes.
- [ ] **RF-15** — Cada aviso tiene su botón o enlace para resolverlo.
- [ ] **RF-16** — Un indicador del tablero sin exclusiones lo dice con todas las letras.
- [ ] **RF-23** — Fuera del tablero, un total sin exclusiones no muestra ningún aviso.
- [ ] **RF-24** — Se entra con un acceso válido y lo primero que aparece es el tablero; no
      queda ninguna pantalla de bienvenida intermedia.
- [ ] **RF-17** — Con un acceso de Ventas, el menú no ofrece secciones de Compras ni de Accesos.
- [ ] **RF-18** — Con ese mismo acceso, no aparece el título de un grupo vacío.
- [ ] **RF-19** — Una pantalla cargando, una con error y una sin resultados se ven con la misma
      forma que sus equivalentes en otras secciones.
- [ ] **RF-20** — Con el dispositivo configurado en modo oscuro, la plataforma se sigue viendo
      clara y legible.
- [ ] **RF-21** — En Revisar esto y en el calendario no hay ningún botón naranja: cada caso ofrece
      su acción en tinta o contorno.
- [ ] **RF-22** — Con un acceso de Ventas, la sección de Ventas aparece en el menú y se abre desde
      ahí.

## Fuera de alcance

- **Capacidades nuevas.** El material de diseño muestra un buscador general, la presencia en vivo
  de otra persona en el calendario y asistentes paso a paso para unificar proveedores y emitir
  recibos. Son features, no presentación: cada una necesita su propia spec.
- **Cambios de cálculo, de reglas o de permisos.** Ningún total, ninguna validación y ningún
  permiso cambia acá.
- **Tema oscuro.** La plataforma tiene un solo tema y es el claro.
- **Los documentos que salen del sistema** (el PDF del recibo, los correos): mantienen su formato
  actual. Unificarlos con la identidad visual es una spec propia.
- **Pantalla chica.** La plataforma se usa desde la computadora del negocio, y esta feature
  resuelve el escritorio. Las pantallas de celular que propone el material de diseño quedan para
  una spec propia.
- **Reorganizar el contenido de las pantallas.** Esta feature cambia cómo se ve lo que ya está,
  no qué información muestra cada pantalla ni en qué orden. Las dos únicas excepciones están
  firmadas y son requisitos: el aviso sube por encima del número (`RF-14`) y la pantalla de
  bienvenida sale del medio (`RF-24`).

## Supuestos

- **La marca es la provisoria.** La ferretería todavía no definió su logo, y se entrega con el
  recuadro "FC" de la guía visual. Cambiarlo más adelante no obliga a rehacer ninguna pantalla.

## Enmiendas

Correcciones al documento posteriores a la firma. Una enmienda que **cambia el alcance** exige
volver a firmar, y esta lo cambia: por eso la fila de abajo lleva su propia firma en el encabezado.

| Fecha | Qué cambió | Alcance |
|---|---|---|
| 2026-08-31 | **Alta de `RF-24`: al entrar se cae en el tablero.** Hoy lo primero que ve alguien que entra es una pantalla de bienvenida que no es ninguna de las dieciséis secciones. La planificación técnica ya la daba por sacada, pero ningún requisito lo pedía: era alcance sin firmar. Se agrega el requisito, su criterio de aceptación, y el *fuera de alcance* pasa a nombrar las dos excepciones firmadas en vez de una | **Sí lo cambia**, y por eso se vuelve a firmar. No es presentación: cambia dónde cae una persona al entrar. Lo encontró `/analyze` (hallazgo H-6) antes de que se escribiera una línea de código |
