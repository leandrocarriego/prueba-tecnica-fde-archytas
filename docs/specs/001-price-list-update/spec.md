# Actualización de la lista de precios — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Aprobado · **Feature:** 001-price-list-update · **Fecha:** 2026-08-28
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-28

<!-- `/approve-spec` completa Aprobada por y Fecha de aprobación, y pasa Estado a Aprobado. -->

## Problema

Resuelve **P1 — El problema de los precios**.

Hoy alguien tiene que entrar todos los días al portal del proveedor, bajar el archivo con la lista
del día y pasar los precios a mano. Es un trabajo que no se puede olvidar ni un día, porque el
proveedor publica precios nuevos dos veces por día y trabajar con un precio viejo significa
controlar mal lo que le facturan a la empresa.

En palabras del cliente: *"Necesitamos tener esos precios siempre actualizados en nuestro sistema,
sin que alguien tenga que entrar manualmente todos los días a bajar el archivo."*

El valor no está en bajar el archivo una vez: está en que nadie tenga que acordarse nunca más.

## Objetivo

Que la lista de precios del proveedor esté siempre al día en el sistema propio, sin que nadie la
baje a mano, y que se pueda ver cómo evolucionó el precio de cada producto y cuáles subieron más de
lo esperable.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El sistema | Entra al portal por su cuenta con la frecuencia configurada, trae la lista del día y actualiza los precios |
| El dueño | Define cada cuánto se consulta el portal y a partir de qué porcentaje de suba un producto se destaca. Ve todo |
| Marcela — compras | Consulta los precios vigentes para controlar lo que le facturan, pide la lista sin esperar al próximo ciclo, y revisa y resuelve lo que el sistema apartó |
| Julián — ventas | Consulta la evolución de los precios en el tiempo |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que la lista diaria sólo cambia el precio de productos que ya existen**, y que no da de
  alta ni de baja productos. **Esto no lo confirmó el cliente**: es un supuesto tomado para poder
  avanzar, y sigue pendiente de confirmación.

  Para que el supuesto no pueda fallar en silencio, el sistema **no actúa por su cuenta** cuando la
  realidad lo contradice: si aparece un producto que no conoce, lo aparta en lugar de darlo de alta;
  si un producto conocido deja de aparecer, conserva su último precio y lo señala en lugar de darlo
  de baja. Si el supuesto resulta falso, se ve en la pantalla de revisión el primer día.

  Si el supuesto resulta falso, esta feature no se queda sin salida: la pantalla de revisión es
  donde una persona decide, caso por caso, si un producto desconocido se incorpora y si uno que
  dejó de aparecer se da por discontinuado. Lo que el sistema nunca hace es decidirlo solo.

- **Se asume que los avisos de esta feature llegan por WhatsApp, y que los recibe el dueño.** El
  canal es el mismo que va a usar el sistema para todos sus avisos. **Tampoco lo confirmó el
  cliente**: queda a la espera de que el equipo acepte recibirlos por ahí, porque un canal que
  incomoda se apaga y el aviso deja de existir.

## Historias de usuario

### H1 — Los precios se actualizan solos *(prioridad más alta)*
Como **dueño**, quiero que el sistema traiga la lista de precios del proveedor por su cuenta, para
que nadie tenga que entrar al portal a bajarla todos los días.

**Cómo se prueba que anda:** se deja el sistema andando un día entero sin que nadie lo toque, y al
día siguiente los precios que muestra coinciden con los que publica el portal.

### H2 — Saber que la actualización sigue viva
Como **dueño**, quiero ver cuándo fue la última actualización que salió bien y que el sistema me
avise por WhatsApp si dejó de funcionar, para no descubrir tarde que estoy mirando precios viejos.

**Cómo se prueba que anda:** se corta el acceso al portal, y la pantalla de precios pasa a mostrar
que la última actualización exitosa quedó vieja mientras llega el aviso al WhatsApp del dueño, en
vez de que todo siga como si nada.

### H3 — Traer la lista ahora, sin esperar
Como **Marcela**, quiero pedirle al sistema que traiga la lista en el momento, para no quedarme con
precios viejos hasta la próxima consulta cuando necesito controlar una factura ahora.

**Cómo se prueba que anda:** se pide la actualización a mano y, al terminar, la pantalla muestra los
precios que publica el portal en ese momento y dice si la consulta salió bien o falló.

### H4 — El dueño decide cada cuánto y qué es una suba grande
Como **dueño**, quiero cambiar desde la aplicación cada cuánto se consulta el portal y a partir de
qué porcentaje se destaca una suba, para ajustarlo yo cuando cambien las circunstancias, sin
pedirle nada a nadie.

**Cómo se prueba que anda:** el dueño cambia la frecuencia y la próxima consulta ocurre con la
frecuencia nueva; cambia el porcentaje y cambia qué productos quedan destacados.

### H5 — La evolución de cada producto
Como **Julián**, quiero ver cómo cambió el precio de un producto a lo largo del tiempo y cuánto
varió contra el mes anterior, para entender qué se está encareciendo.

**Cómo se prueba que anda:** el mismo día de la instalación se abre un producto y ya se ve el
historial que el portal publica para él, con sus fechas; de ahí en adelante se le suman los cambios
que el sistema va viendo.

### H6 — Las subas que hay que mirar
Como **dueño**, quiero que el sistema destaque los productos que subieron más del porcentaje que yo
definí, para mirar sólo lo que se salió de lo normal en lugar de recorrer los cien productos.

**Cómo se prueba que anda:** fijado el porcentaje en un valor, quedan destacados exactamente los
productos que subieron por encima de ese valor.

### H7 — Lo que no se pudo resolver queda a la vista
Como **Marcela**, quiero ver lo que el sistema apartó y por qué, en vez de que desaparezca sin que
nadie se entere.

**Cómo se prueba que anda:** llega una lista con una fila rota y un producto desconocido; el resto
de los precios se actualiza igual, y esos dos casos aparecen en la pantalla de revisión con su
motivo.

### H8 — Resolver lo apartado, y que no vuelva a preguntar lo mismo
Como **Marcela**, quiero decidir qué hacer con cada caso que el sistema apartó y que esa decisión
quede guardada, para que la pantalla de revisión se vacíe en lugar de crecer, y para que el sistema
no me vuelva a preguntar lo que ya contesté.

**Cómo se prueba que anda:** se resuelve un producto desconocido incorporándolo; en la actualización
siguiente ese producto ya no aparece apartado sino con su precio en la lista, y la pantalla de
revisión queda sin ese caso.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe obtener la lista de precios del portal con la frecuencia configurada. | H1 |
| RF-02 | Cuando el sistema obtenga su primera lista de precios, debe registrar como productos conocidos todos los que figuren en ella. | H1 |
| RF-03 | Cuando el sistema obtenga una lista de precios, debe registrar el precio vigente de cada producto conocido incluido en ella. | H1 |
| RF-04 | El sistema debe mostrar la lista de precios vigente con el código, la descripción y el precio de cada producto. | H1 |
| RF-05 | Cuando el sistema obtenga una lista de precios, debe conservarla tal como llegó del portal. | H1 |
| RF-06 | Si una fila de la lista no se puede interpretar, entonces el sistema debe apartarla sin interrumpir la actualización de las demás. | H1 |
| RF-07 | Si una lista posterior a la primera incluye un producto que el sistema no conoce, entonces el sistema debe apartarlo en lugar de darlo de alta. | H1 |
| RF-08 | Si un producto conocido no figura en la lista obtenida, entonces el sistema debe conservar su último precio registrado. | H1 |
| RF-09 | El sistema debe mostrar la fecha y la hora de la última actualización de precios que terminó con éxito. | H2 |
| RF-10 | Si una actualización de precios falla, entonces el sistema debe registrar el fallo junto con su motivo. | H2 |
| RF-11 | Si pasan dos consultas programadas seguidas sin una actualización exitosa, entonces el sistema debe señalarlo de forma visible en la pantalla de precios. | H2 |
| RF-12 | Si pasan dos consultas programadas seguidas sin una actualización exitosa, entonces el sistema debe avisar al dueño por WhatsApp. | H2 |
| RF-13 | Mientras una misma interrupción siga sin resolverse, el sistema debe avisar una sola vez. | H2 |
| RF-14 | Cuando una persona autorizada lo solicite, el sistema debe obtener la lista de precios sin esperar a la consulta programada. | H3 |
| RF-15 | Si ya hay una actualización en curso, entonces el sistema debe informarlo en lugar de iniciar otra. | H3 |
| RF-16 | Cuando termine una actualización pedida a mano, el sistema debe informar a quien la pidió si trajo la lista o si falló. | H3 |
| RF-17 | Cuando alguien pida una actualización a mano, el sistema debe registrar quién la pidió y cuándo. | H3 |
| RF-18 | El sistema debe permitir al dueño definir cada cuánto se consulta el portal. | H4 |
| RF-19 | El sistema debe permitir al dueño definir a partir de qué porcentaje de suba un producto queda destacado. | H4 |
| RF-20 | Mientras el dueño no haya cambiado un parámetro, el sistema debe usar el valor inicial de ese parámetro. | H4 |
| RF-21 | Cuando el dueño cambie la frecuencia de consulta, el sistema debe aplicarla a partir de la consulta siguiente. | H4 |
| RF-22 | Cuando el precio de un producto cambie respecto del último registrado, el sistema debe agregar un punto a su historial. | H5 |
| RF-23 | Cuando alguien abra un producto, el sistema debe mostrar la evolución de su precio en el tiempo. | H5 |
| RF-24 | El sistema debe mostrar, para cada producto, la variación entre su precio vigente y el último precio que tuvo el mes calendario anterior. | H5 |
| RF-25 | El sistema debe destacar los productos cuyo precio vigente subió más que el porcentaje configurado respecto del precio que tenían en la actualización anterior. | H6 |
| RF-26 | El sistema debe mostrar lo que quedó apartado junto con el motivo por el que se apartó. | H7 |
| RF-27 | Cuando termine una actualización, el sistema debe informar cuántas filas quedaron apartadas. | H7 |
| RF-28 | El sistema debe señalar los productos conocidos que dejaron de figurar en la lista. | H7 |
| RF-29 | Cuando una persona autorizada resuelva una fila que no se pudo interpretar, el sistema debe registrar el precio que ella indique para el producto conocido que ella señale. | H8 |
| RF-30 | Cuando una persona autorizada resuelva un producto desconocido, el sistema debe incorporarlo a los productos conocidos o dejarlo fuera, según lo que ella decida. | H8 |
| RF-31 | Cuando una persona autorizada resuelva un producto que dejó de figurar en la lista, el sistema debe darlo por discontinuado o mantenerlo vigente, según lo que ella decida. | H8 |
| RF-32 | Cuando una persona resuelva un caso apartado, el sistema debe registrar qué decidió, quién lo decidió y cuándo. | H8 |
| RF-33 | Cuando un caso quede resuelto, el sistema debe dejar de mostrarlo entre los pendientes de revisión. | H8 |
| RF-34 | Si una actualización posterior encuentra un caso igual a uno ya resuelto, entonces el sistema debe aplicarle la misma decisión sin volver a apartarlo. | H8 |
| RF-35 | Si una actualización encuentra un caso igual a uno que ya está apartado sin resolver, entonces el sistema debe mantener un solo caso pendiente en lugar de agregar otro. | H8 |
| RF-36 | El sistema debe mostrar las decisiones que quedaron guardadas como regla, junto con quién las tomó y cuándo, y debe permitir dejar una sin efecto. | H8 |
| RF-37 | Cuando una regla quede sin efecto, el sistema debe volver a apartar los casos que esa regla venía resolviendo. | H8 |
| RF-38 | Cuando el sistema registre un producto como conocido por primera vez, debe incorporar a su historial los precios que el portal ya publica para ese producto. | H5 |
| RF-39 | Si el historial publicado de un producto no se puede interpretar, entonces el sistema debe apartarlo sin perder el precio vigente de ese producto. | H5 |
| RF-40 | Si un precio del historial publicado coincide con uno que el sistema ya registró, entonces el sistema debe conservar un solo punto. | H5 |

## Reglas de negocio

- **El portal del proveedor es la única fuente de los precios, y el sistema nunca le escribe nada.**
  Es un sistema de un tercero y se lo trata como tal: se lee lo que publica, no se lo modifica.
- **Nada de lo que llega se descarta.** Una fila que el sistema no puede interpretar no se pierde ni
  frena la actualización del resto: queda apartada, contada y visible para que una persona decida.
- **El sistema no da de alta ni de baja productos por su cuenta.** Ante un producto que no conoce, o
  uno conocido que dejó de aparecer, aparta y avisa: esa decisión es del negocio, no del sistema.
- **Cada lista se conserva tal como llegó.** Si alguna vez un precio del sistema no coincide con el
  del portal, tiene que poder explicarse con lo que el portal dijo ese día.
- **Los precios de lista los pueden consultar tanto compras como ventas.** Son precios del
  proveedor y no revelan información de las ventas de la empresa.
- **Un precio nunca se completa por suposición.** Si un producto no viene en la lista del día,
  conserva el último precio conocido con su fecha, en lugar de quedar en blanco o estimarse.
- **Sólo el dueño cambia los parámetros.** Cada cuánto se consulta y qué porcentaje destaca una suba
  son decisiones suyas, no de quien esté mirando la pantalla.
- **Pedir la lista a mano es golpearle la puerta a un sistema de un tercero.** Por eso sólo pueden
  hacerlo el dueño y compras, el sistema no atiende dos pedidos a la vez, y queda registrado quién
  lo pidió. Un pedido a mano no cambia la frecuencia con la que el sistema consulta por su cuenta.
- **Con qué valores arranca el sistema el primer día**: consulta el portal **cada 12 horas** y
  destaca toda suba **mayor al 10%**. Lo primero sale de un dato medido —el proveedor publica dos
  veces por día, así que consultar más seguido no trae precios nuevos y castiga una cuenta que es de
  un tercero—. Lo segundo es sólo un punto de partida. El dueño cambia los dos cuando quiera.
- **Una decisión sobre un caso apartado se toma una sola vez.** Cuando una persona resuelve un caso,
  esa decisión queda guardada como regla y el sistema la aplica a los casos iguales que lleguen
  después, en lugar de volver a preguntar. Las reglas están a la vista, con quién las tomó, y se
  pueden dejar sin efecto: una regla equivocada tiene que poder corregirse, y corregirla devuelve a
  revisión lo que esa regla venía resolviendo.
- **Un aviso no se repite mientras la causa siga siendo la misma.** Si la actualización lleva días
  sin funcionar, el dueño recibe un aviso, no uno por cada intento fallido.

## Criterios de aceptación

- [ ] **RF-01** — Configurada la frecuencia, el sistema trae la lista solo, sin que nadie lo dispare.
- [ ] **RF-02** — Instalado de cero, la primera consulta deja los cien productos de la lista cargados y visibles, ninguno apartado por desconocido.
- [ ] **RF-03** — Después de una actualización, el precio que muestra cada producto conocido es el que trajo la lista.
- [ ] **RF-04** — La pantalla de precios lista los productos con código, descripción y precio vigente.
- [ ] **RF-05** — Para cualquier día en que hubo actualización, puede recuperarse la lista tal como llegó ese día.
- [ ] **RF-06** — Con una lista que trae una fila rota, los demás productos se actualizan igual.
- [ ] **RF-07** — Una lista que trae un producto nunca visto no lo agrega al catálogo: lo deja apartado.
- [ ] **RF-08** — Un producto que no vino en la lista del día sigue mostrando su último precio, con la fecha en que se registró.
- [ ] **RF-09** — La pantalla de precios muestra la fecha y hora de la última actualización exitosa.
- [ ] **RF-10** — Después de un fallo, queda registrado que la actualización falló y por qué.
- [ ] **RF-11** — Cortado el acceso al portal, tras dos consultas programadas fallidas la pantalla de precios lo señala a la vista.
- [ ] **RF-12** — En esa misma situación, al dueño le llega el aviso a su WhatsApp.
- [ ] **RF-13** — Con la actualización caída varios ciclos seguidos, al dueño le llegó un solo aviso.
- [ ] **RF-14** — Pedida la actualización a mano, el sistema consulta el portal en el momento.
- [ ] **RF-15** — Pedida una segunda actualización mientras corre la primera, el sistema avisa que ya hay una en curso.
- [ ] **RF-16** — Al terminar, quien la pidió ve si la lista se trajo o si la consulta falló.
- [ ] **RF-17** — Después de un pedido a mano queda registrado quién lo hizo y cuándo.
- [ ] **RF-18** — El dueño cambia la frecuencia desde la aplicación y el cambio queda guardado.
- [ ] **RF-19** — El dueño cambia el porcentaje desde la aplicación y el cambio queda guardado.
- [ ] **RF-20** — Recién instalado, sin que nadie toque nada, el sistema consulta cada 12 horas y destaca las subas mayores al 10%.
- [ ] **RF-21** — Cambiada la frecuencia, la consulta siguiente ocurre según el valor nuevo.
- [ ] **RF-22** — Un producto cuyo precio no cambió entre dos consultas no suma un punto nuevo; uno que cambió, sí.
- [ ] **RF-23** — Al abrir un producto se ve cómo cambió su precio a lo largo del tiempo.
- [ ] **RF-24** — Un producto que cerró julio a $100 y hoy vale $115 muestra 15%.
- [ ] **RF-25** — Con el porcentaje en 10%, queda destacado el producto que pasó de $100 a $115 entre dos actualizaciones, y no el que pasó de $100 a $105.
- [ ] **RF-26** — Lo apartado aparece en la pantalla de revisión, cada caso con el motivo por el que se apartó.
- [ ] **RF-27** — Al terminar una actualización se puede ver cuántas filas quedaron apartadas.
- [ ] **RF-28** — Un producto conocido que dejó de venir en la lista queda señalado para revisión.
- [ ] **RF-29** — Una fila rota se resuelve señalando el producto y el precio, y ese producto pasa a mostrar ese precio en la lista.
- [ ] **RF-30** — Resuelto un producto desconocido incorporándolo, la lista de precios pasa a mostrarlo; resuelto dejándolo fuera, no aparece.
- [ ] **RF-31** — Resuelto como discontinuado, el producto deja de estar señalado; resuelto como vigente, conserva su último precio y se lo sigue mostrando.
- [ ] **RF-32** — Cada caso resuelto muestra qué se decidió, quién lo decidió y en qué fecha.
- [ ] **RF-33** — Resuelto un caso, la pantalla de revisión pasa a tener uno menos pendiente.
- [ ] **RF-34** — Resuelto un producto desconocido, la actualización siguiente lo procesa sin apartarlo de nuevo.
- [ ] **RF-35** — El mismo producto desconocido en tres consultas seguidas deja un solo caso pendiente, no tres.
- [ ] **RF-36** — Las reglas guardadas se pueden ver en una pantalla, cada una con quién la tomó y cuándo, y se puede dejar una sin efecto.
- [ ] **RF-37** — Dejada sin efecto la regla que incorporaba un producto, ese producto vuelve a aparecer apartado en la actualización siguiente.
- [ ] **RF-38** — Recién instalado el sistema, un producto muestra los mismos puntos de historial que muestra el portal para ese producto.
- [ ] **RF-39** — Un producto cuyo historial no se pudo leer aparece igual en la lista con su precio vigente, y el historial faltante queda en la pantalla de revisión.
- [ ] **RF-40** — Un producto cuyo historial se trae dos veces sigue mostrando la misma cantidad de puntos.

## Fuera de alcance

- **El panel general de parámetros del sistema.** Esta feature permite ajustar **sus dos**
  parámetros —cada cuánto se consulta y el porcentaje que destaca una suba—. El panel donde el dueño
  administra todos los parámetros del sistema es **P9 — El problema de no tener control**.
- **El control de acceso por rol.** Esta spec dice quién debería poder hacer qué; que el sistema lo
  verifique de verdad es **P10 — El problema de los accesos**.
- **Que el sistema dé de alta o de baja productos por su cuenta.** Los aparta y es una persona la
  que decide, caso por caso, desde la pantalla de revisión. El mantenimiento del catálogo por fuera
  de esa pantalla —dar de alta un producto que nunca vino en una lista, editar su descripción— no
  entra acá.
- **Los precios de venta de la empresa y sus márgenes.** Acá sólo entran los precios que publica el
  proveedor.
- **Unificar los rubros del proveedor.** El portal escribe el mismo rubro de varias formas
  —`PINTURAS Y ADHESIVOS`, `Pinturas/Adhesivos`, `Pinturas y Adhesivos`— y algunos productos vienen
  sin rubro. El sistema conserva lo que el portal dijo y no lo interpreta: unificarlos es **P7 — El
  problema de los rubros**.
- **El resto de la información del portal** (facturas, ventas, órdenes, mensajes): cada una tiene su
  propio problema numerado.
