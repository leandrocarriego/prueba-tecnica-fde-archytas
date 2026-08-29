# Accesos por persona — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Aprobado · **Feature:** 002-access-control · **Fecha:** 2026-08-29
**Aprobada por:** Leandro Carriego — FDE · **Fecha de aprobación:** 2026-08-29

<!-- Segunda firma del mismo día. La primera cubría un documento en el que la invitación y la
     recuperación iban por correo; al no haber dominio propio, pasaron a WhatsApp. El alcance no
     se movió: cambió el canal, y la firma anterior dejó de corresponder al texto. -->

<!-- `/approve-spec` completa Aprobada por y Fecha de aprobación, y pasa Estado a Aprobado. -->

## Problema

Resuelve **P10 — El problema de los accesos**.

Hoy las tres personas del equipo entran con la misma clave, y eso significa que cualquiera ve
todo: la facturación de la empresa, las ventas, las cuentas de los proveedores. No es un problema
de desconfianza, es que **no existe una forma de que cada uno entre sólo a lo suyo**.

En palabras del cliente: *"Hoy entramos todos con el mismo usuario y eso ya no me sirve. (…) no
quiero que Marcela ande viendo toda la facturación y las ventas de la empresa, ni que Julián toque
las cuentas de los proveedores. Me gustaría que cada uno tenga su propio acceso y que entre sólo a
la parte que le toca, y que yo sí pueda ver todo. Que no sea que porque conocen la clave pueden
entrar a cualquier lado."*

Esa última frase es la que define el alcance: **esconder una opción del menú no es un acceso
restringido.** Si alguien conoce la dirección de una pantalla, tiene que quedarse afuera igual.

## Objetivo

Que cada persona del equipo entre al sistema con su propio acceso y vea únicamente la parte del
negocio que le corresponde, y que el dueño pueda dar de alta, cambiar y quitar esos accesos por su
cuenta.

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| El dueño | Entra con su acceso y ve todo el sistema. Da de alta, modifica y desactiva los accesos de las otras personas |
| Marcela — compras | Entra con su acceso y trabaja sobre proveedores, facturas, pagos, órdenes, recibos, calendario y precios |
| Julián — ventas | Entra con su acceso y trabaja sobre ventas, tablero, stock, rubros y catálogo. Consulta los precios y el calendario, sin poder cambiarlos |
| El sistema | Verifica en cada consulta si quien la hace tiene permiso, y deja registro de los intentos rechazados |

## Supuestos

<!-- Un supuesto NO es una respuesta del cliente. Se declara para que se vea al firmar. -->

- **Se asume que una persona que deja el equipo se desactiva y no se borra.** Su acceso deja de
  funcionar en el momento, pero todo lo que hizo mientras trabajó sigue figurando con su nombre.
  Borrarla dejaría el historial de ediciones firmado por nadie, y el sistema se comprometió a
  registrar quién hizo cada cosa.

- **Se asume que cada persona del equipo tiene un teléfono propio con WhatsApp**, porque por ahí
  llegan la invitación con la que entra la primera vez y la recuperación si pierde su clave. Es el
  mismo canal por el que el sistema manda sus avisos, y el equipo ya lo usa. Quien no lo tenga no
  puede darse de alta ni recuperar el acceso por su cuenta.

- **Se asume que el correo de cada acceso es sólo su nombre de usuario.** Es lo que la persona
  escribe para entrar y sirve para distinguir un acceso de otro; el sistema **no le manda nada
  ahí**. Todo lo que el sistema tiene que decirle a alguien va por WhatsApp.

- **Se asume que el bloqueo por intentos fallidos arranca en cinco intentos seguidos y quince
  minutos de espera.** **El cliente decidió que el bloqueo exista, no estos números**: son un punto
  de partida y el dueño los ajusta después desde los parámetros del sistema.

- **Se asume que el acceso del dueño se crea al poner el sistema en marcha, y no desde el sistema.**
  Todo lo demás lo da de alta él, así que el suyo no puede darlo de alta nadie: se crea una sola vez
  al instalar, fuera de la aplicación, y por eso no hay ninguna pantalla donde alguien pueda crearse
  un acceso de dueño. **El cliente no lo conversó**, porque es el primer día del sistema y no una
  situación del uso diario.

- **Se asume que la invitación vale siete días y el enlace de recuperación una hora.** **El cliente
  eligió que existan, no cuánto duran.** Son el mismo criterio que los números del bloqueo: un punto
  de partida que se ajusta si en el uso resultan cortos o largos.

## Historias de usuario

### H1 — Cada uno entra con lo suyo *(prioridad más alta)*
Como **dueño**, quiero que cada persona del equipo entre al sistema con su propio acceso, para
dejar de compartir una clave entre los tres.

**Cómo se prueba que anda:** las tres personas entran cada una con su acceso, y el sistema muestra
en pantalla con el nombre de quién está trabajando.

### H2 — Cada uno ve sólo su parte
Como **dueño**, quiero que Marcela no vea las ventas y que Julián no vea las cuentas de los
proveedores, para que la información del negocio no esté toda a la vista de todos.

**Cómo se prueba que anda:** Marcela entra y no encuentra el tablero de ventas por ningún lado;
Julián entra y no encuentra las facturas de compra. Julián sí abre el calendario de vencimientos,
pero no puede mover ninguno.

### H3 — El permiso se verifica de verdad
Como **dueño**, quiero que conocer la dirección de una pantalla no alcance para entrar, para que la
restricción sea real y no un menú que esconde opciones.

**Cómo se prueba que anda:** Julián copia la dirección exacta de la pantalla de proveedores que usa
Marcela, la abre, y el sistema le dice que no tiene permiso en lugar de mostrársela.

### H4 — El dueño administra los accesos
Como **dueño**, quiero dar de alta a una persona nueva, cambiarle lo que puede ver, desactivarla
cuando deja el equipo y reactivarla si vuelve, sin pedirle nada a nadie.

**Cómo se prueba que anda:** el dueño da de alta a una persona nueva con acceso de compras, a esa
persona le llega una invitación por WhatsApp, define su clave, entra y ve lo mismo que Marcela;
después el dueño la desactiva y ya no puede entrar. Si vuelve, la reactiva, ella define una clave
nueva y la de antes no sirve más.

### H5 — Cada uno maneja su propia clave
Como **Marcela**, quiero cambiar mi clave cuando quiera y poder recuperar el acceso si me la
olvido, para no depender de que alguien me la reponga.

**Cómo se prueba que anda:** Marcela cambia su clave, sale y vuelve a entrar con la nueva; la clave
vieja deja de funcionar. Y si se la olvida, pide recuperarla y le llega un enlace por WhatsApp sin
que el dueño se entere ni tenga que hacer nada.

### H6 — Saber quién entró y a qué le dijeron que no
Como **dueño**, quiero ver quién entró al sistema y qué intentos de acceso quedaron rechazados,
para enterarme si alguien está intentando llegar a donde no le toca.

**Cómo se prueba que anda:** después de que Julián intenta abrir la pantalla de proveedores, el
dueño ve ese intento rechazado registrado con el nombre de Julián y la fecha.

## Requisitos funcionales

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | El sistema debe permitir entrar únicamente con un acceso individual asignado a una persona. | H1 |
| RF-02 | Si las credenciales presentadas no corresponden a un acceso activo, entonces el sistema debe rechazar el ingreso sin indicar cuál de los dos datos falló. | H1 |
| RF-03 | Mientras una persona esté trabajando en el sistema, la pantalla debe mostrar su nombre. | H1 |
| RF-04 | El sistema debe permitir a una persona cerrar su sesión. | H1 |
| RF-05 | Cuando una sesión supere el tiempo de inactividad configurado, el sistema debe cerrarla. | H1 |
| RF-06 | El sistema debe asignar a cada acceso exactamente uno de los tres roles: dueño, compras o ventas. | H2 |
| RF-07 | El sistema debe mostrar a cada persona únicamente las secciones habilitadas para su rol. | H2 |
| RF-08 | El sistema debe habilitar al rol dueño todas las secciones. | H2 |
| RF-09 | El sistema debe impedir al rol compras el acceso a las ventas y al tablero comercial. | H2 |
| RF-10 | El sistema debe impedir al rol ventas el acceso a las cuentas de proveedores, a las facturas de compra y a los pagos. | H2 |
| RF-11 | El sistema debe habilitar la consulta de los precios de lista a los tres roles. | H2 |
| RF-12 | El sistema debe verificar el permiso de quien consulta antes de responder cada consulta. | H3 |
| RF-13 | Si quien consulta no tiene permiso sobre lo consultado, entonces el sistema debe rechazar la consulta e informarlo. | H3 |
| RF-14 | Si quien consulta no tiene permiso sobre lo consultado, entonces el sistema debe registrar el intento rechazado. | H3 |
| RF-15 | Si una consulta llega sin una sesión activa, entonces el sistema debe rechazarla. | H3 |
| RF-16 | El sistema debe permitir al dueño dar de alta un acceso indicando la persona, su correo, su teléfono y su rol. | H4 |
| RF-17 | El sistema debe permitir al dueño cambiar el rol de un acceso existente. | H4 |
| RF-18 | El sistema debe permitir al dueño desactivar un acceso. | H4 |
| RF-19 | Si un acceso está desactivado, entonces el sistema debe rechazar el ingreso de esa persona. | H4 |
| RF-20 | Cuando el dueño desactive un acceso, el sistema debe cerrar las sesiones abiertas de esa persona. | H4 |
| RF-21 | El sistema debe conservar el nombre de una persona desactivada en todo lo que ella haya registrado. | H4 |
| RF-22 | El sistema debe impedir al dueño desactivar su propio acceso. | H4 |
| RF-23 | Cuando el dueño dé de alta, modifique, desactive o reactive un acceso, el sistema debe registrar qué cambió, quién lo cambió y cuándo. | H4 |
| RF-24 | El sistema debe impedir que un rol distinto de dueño administre accesos. | H4 |
| RF-25 | El sistema debe permitir a cada persona cambiar su propia clave. | H5 |
| RF-26 | Cuando una persona cambie su clave, el sistema debe invalidar la clave anterior. | H5 |
| RF-27 | El sistema debe permitir a una persona iniciar la recuperación de su acceso sin intervención del dueño. | H5 |
| RF-28 | El sistema debe impedir que una clave quede guardada de forma que alguien pueda leerla. | H5 |
| RF-29 | Cuando una persona ingrese al sistema, el sistema debe registrar quién ingresó y cuándo. | H6 |
| RF-30 | El sistema debe mostrar al dueño los ingresos registrados y los intentos rechazados. | H6 |
| RF-31 | El sistema debe impedir a los roles distintos de dueño ver los ingresos y los intentos rechazados de otras personas. | H6 |
| RF-32 | El sistema debe habilitar cada sección a un rol como consulta, o como consulta y edición. | H2 |
| RF-33 | Si quien consulta tiene una sección habilitada sólo como consulta, entonces el sistema debe rechazar cualquier cambio que intente sobre ella. | H2 |
| RF-34 | El sistema debe habilitar el calendario de vencimientos como consulta y edición al dueño y a compras, y sólo como consulta a ventas. | H2 |
| RF-35 | El sistema debe habilitar únicamente al dueño y a compras a pedir la actualización de los precios a mano y a resolver lo que el sistema haya apartado. | H2 |
| RF-36 | Mientras el dueño no haya cambiado el tiempo de inactividad, el sistema debe cerrar toda sesión que lleve ocho horas sin uso. | H1 |
| RF-37 | El sistema debe registrar en cada acceso un teléfono propio de esa persona. | H4 |
| RF-38 | Cuando una persona solicite recuperar su acceso, el sistema debe enviar un enlace de recuperación por WhatsApp al teléfono registrado en ese acceso. | H5 |
| RF-39 | Si el correo indicado para recuperar un acceso no corresponde a ningún acceso activo, entonces el sistema debe responder lo mismo que si correspondiera. | H5 |
| RF-40 | Cuando se use un enlace de recuperación, el sistema debe invalidarlo. | H5 |
| RF-41 | Si un enlace de recuperación supera su vigencia, entonces el sistema debe rechazarlo. | H5 |
| RF-42 | Cuando el dueño dé de alta un acceso, el sistema debe enviar por WhatsApp a su teléfono una invitación para que esa persona defina su propia clave. | H4 |
| RF-43 | Mientras una persona no haya definido su clave desde la invitación, el sistema debe impedir el ingreso de ese acceso. | H4 |
| RF-44 | El sistema debe impedir al dueño definir o consultar la clave de otra persona. | H4 |
| RF-45 | Si un acceso acumula más intentos fallidos seguidos que el límite configurado, entonces el sistema debe bloquearlo temporalmente. | H1 |
| RF-46 | Mientras un acceso esté bloqueado temporalmente, el sistema debe rechazar su ingreso aunque las credenciales sean correctas. | H1 |
| RF-47 | Cuando un acceso quede bloqueado temporalmente, el sistema debe registrar el bloqueo entre los intentos rechazados. | H6 |
| RF-48 | Cuando venza el tiempo de bloqueo de un acceso, el sistema debe volver a permitir su ingreso. | H1 |
| RF-49 | Mientras el dueño no los haya cambiado, el sistema debe bloquear un acceso durante quince minutos después de cinco intentos fallidos seguidos. | H1 |
| RF-50 | El sistema debe impedir que exista más de un acceso con el rol dueño. | H4 |
| RF-51 | El sistema debe permitir al dueño reactivar un acceso desactivado. | H4 |
| RF-52 | Cuando el dueño reactive un acceso, el sistema debe enviar por WhatsApp a su teléfono una invitación para que esa persona defina una clave nueva. | H4 |
| RF-53 | Cuando el dueño reactive un acceso, el sistema debe invalidar la clave que ese acceso tenía antes de desactivarse. | H4 |

## Reglas de negocio

- **Los roles son tres, son fijos, y salen de lo que hace cada persona**: el dueño ve y hace todo;
  compras trabaja sobre proveedores, facturas, pagos, órdenes, recibos, calendario y precios;
  ventas trabaja sobre ventas, tablero, stock, rubros y catálogo. Quien entre al equipo entra en
  uno de esos tres, y no hay una pantalla donde armar un rol distinto.
- **El rol dueño es de una sola persona.** No hay dos dueños: administrar los accesos y los
  parámetros del sistema es de uno solo.
- **Una sección se habilita de dos maneras: consulta, o consulta y edición.** Que alguien pueda
  mirar algo no significa que pueda cambiarlo, y esconder el botón no alcanza: el sistema rechaza
  el cambio igual.
- **Los precios de lista los ven los tres.** Son precios que publica el proveedor y no revelan nada
  de las ventas de la empresa; compras los necesita para controlar lo que le facturan. Pedir la
  lista sin esperar al próximo ciclo y resolver lo que el sistema apartó son cosas del dueño y de
  compras; ventas mira los precios y su evolución.
- **El calendario de vencimientos lo edita el dueño y compras; ventas sólo lo consulta.**
- **El permiso se verifica en cada consulta, no al dibujar el menú.** Un menú que esconde opciones
  es una comodidad visual; el que decide si algo se responde o no es el sistema, cada vez.
- **Sólo el dueño administra los accesos.** Nadie se cambia el rol a sí mismo, y el dueño no puede
  dejarse afuera del sistema.
- **Una persona que deja el equipo se desactiva, no se borra.** Deja de entrar en el momento, pero
  lo que hizo sigue figurando con su nombre: el sistema se comprometió a registrar quién hizo cada
  cosa, y un historial firmado por nadie no sirve para nada.
- **Y si vuelve, el dueño la reactiva: es la misma persona, no una nueva.** Su acceso queda otra vez
  a la espera de que ella defina una clave, que define ella y no el dueño. La que usaba antes no
  vuelve a servir, y todo lo que hizo antes y lo que haga ahora figura junto, bajo un solo nombre.
- **La sesión se cierra a las ocho horas sin uso.** Es el valor con el que arranca el sistema y lo
  ajusta el dueño desde los parámetros.
- **Las claves de las personas no se pueden leer, y nadie se las pone a otro.** Cada uno define la
  suya desde la invitación con la que entra la primera vez, y si la pierde la recupera por
  WhatsApp: ni el dueño la ve ni se la puede asignar.
- **Probar claves hasta acertar no sale gratis.** Después de varios intentos fallidos seguidos, ese
  acceso queda bloqueado un rato, y el bloqueo queda a la vista del dueño junto al resto de los
  intentos rechazados.
- **La cuenta compartida del portal del proveedor no es un acceso de este sistema.** Es una
  credencial de un tercero que usa el sistema para leer el portal, vive fuera de la aplicación y
  nadie la ve desde ninguna pantalla.
- **Un intento rechazado no se pierde.** Que alguien haya intentado entrar a donde no le toca es
  información del negocio, no ruido técnico.

## Criterios de aceptación

- [ ] **RF-01** — No hay forma de entrar al sistema que no sea con el acceso de una persona.
- [ ] **RF-02** — Con la clave equivocada el sistema rechaza el ingreso y no dice si el error estaba en el usuario o en la clave.
- [ ] **RF-03** — Estando dentro, la pantalla muestra el nombre de quien está trabajando.
- [ ] **RF-04** — Al cerrar sesión, volver atrás en el navegador no devuelve a la pantalla anterior con datos.
- [ ] **RF-05** — Dejada la pantalla abierta y sin uso más tiempo del configurado, hay que volver a entrar.
- [ ] **RF-06** — Cada acceso muestra su rol, y es uno solo de los tres.
- [ ] **RF-07** — El menú de Marcela y el de Julián no tienen las mismas secciones.
- [ ] **RF-08** — El dueño llega a todas las secciones del sistema.
- [ ] **RF-09** — Marcela no encuentra el tablero comercial ni las ventas por ningún camino del menú.
- [ ] **RF-10** — Julián no encuentra las cuentas de proveedores, las facturas de compra ni los pagos.
- [ ] **RF-11** — Los tres abren la pantalla de precios de lista.
- [ ] **RF-12** — Cada pantalla responde recién después de comprobar quién la pidió.
- [ ] **RF-13** — Julián pega la dirección de la pantalla de proveedores y recibe un aviso de que no tiene permiso, no la pantalla.
- [ ] **RF-14** — Ese intento queda registrado con el nombre de Julián, qué quiso ver y cuándo.
- [ ] **RF-15** — Abierta una dirección del sistema sin haber entrado, el sistema pide entrar.
- [ ] **RF-16** — El dueño da de alta una persona con su correo, su teléfono y su rol de compras, y queda registrada.
- [ ] **RF-17** — Cambiado el rol de una persona de ventas a compras, al volver a entrar ve las secciones de compras.
- [ ] **RF-18** — Desactivado un acceso, esa persona ya no puede entrar.
- [ ] **RF-19** — El intento de ingreso de un acceso desactivado se rechaza como el de una clave equivocada.
- [ ] **RF-20** — Desactivada una persona que estaba trabajando, su pantalla deja de responder y le pide entrar de nuevo.
- [ ] **RF-21** — Una factura cargada por una persona desactivada sigue mostrando su nombre.
- [ ] **RF-22** — El dueño intenta desactivarse a sí mismo y el sistema no lo permite.
- [ ] **RF-23** — Cada alta, cambio de rol, desactivación y reactivación figura con qué cambió, quién y cuándo.
- [ ] **RF-24** — Marcela y Julián no encuentran la pantalla de administración de accesos.
- [ ] **RF-25** — Marcela cambia su clave desde su propia pantalla.
- [ ] **RF-26** — Cambiada la clave, la anterior deja de servir para entrar.
- [ ] **RF-27** — Una persona que olvidó su clave recupera el acceso sin que el dueño intervenga.
- [ ] **RF-28** — En ninguna pantalla del sistema aparece la clave de nadie.
- [ ] **RF-29** — Cada ingreso queda registrado con nombre y fecha.
- [ ] **RF-30** — El dueño ve una lista con los ingresos y los intentos rechazados.
- [ ] **RF-31** — Marcela no encuentra esa lista.
- [ ] **RF-32** — Abierto un acceso, se ve sección por sección si esa persona la consulta o si además la edita.
- [ ] **RF-33** — Julián abre el calendario, intenta mover un vencimiento y el sistema no se lo permite.
- [ ] **RF-34** — Marcela mueve un vencimiento del calendario; Julián lo ve movido y no puede moverlo él.
- [ ] **RF-35** — Marcela pide la actualización de precios a mano y resuelve una fila apartada; Julián no llega a ninguna de las dos cosas.
- [ ] **RF-36** — Sin tocar ningún parámetro, una pantalla abierta y sin uso desde hace ocho horas pide entrar de nuevo.
- [ ] **RF-37** — Cada acceso muestra el teléfono de su persona.
- [ ] **RF-38** — Marcela pide recuperar su acceso y le llega un enlace por WhatsApp.
- [ ] **RF-39** — Pedida la recuperación con un correo que no existe, la pantalla responde lo mismo que con uno que sí.
- [ ] **RF-40** — Usado el enlace una vez, volver a abrirlo ya no sirve.
- [ ] **RF-41** — Un enlace guardado y abierto más tarde de su vigencia no deja cambiar la clave.
- [ ] **RF-42** — Dada de alta una persona, le llega por WhatsApp la invitación para poner su clave.
- [ ] **RF-43** — Antes de aceptar la invitación, esa persona no puede entrar.
- [ ] **RF-44** — En la pantalla de administración no hay forma de escribir ni de ver la clave de otro.
- [ ] **RF-45** — Tras varios intentos seguidos con la clave equivocada, el acceso queda bloqueado.
- [ ] **RF-46** — Bloqueado el acceso, entrar con la clave correcta tampoco funciona.
- [ ] **RF-47** — El bloqueo figura en la lista de intentos rechazados que ve el dueño.
- [ ] **RF-48** — Pasado el tiempo del bloqueo, la clave correcta vuelve a funcionar.
- [ ] **RF-49** — Sin tocar ningún parámetro, el acceso se bloquea quince minutos al quinto intento fallido seguido.
- [ ] **RF-50** — El dueño intenta poner a una segunda persona como dueño y el sistema no lo permite.
- [ ] **RF-51** — Reactivado el acceso de alguien que había dejado el equipo, esa persona vuelve a figurar entre los activos y con el mismo nombre de antes.
- [ ] **RF-52** — Al reactivarla, le llega por WhatsApp una invitación para definir una clave nueva.
- [ ] **RF-53** — La clave que usaba antes de que la desactivaran no sirve para entrar.

## Fuera de alcance

- **Un cuarto acceso técnico por encima del dueño.** Se preguntó y quedó descartado: los roles son
  tres y el dueño administra. Si alguna vez el sistema lo opera alguien de fuera del negocio, se
  conversa y se agrega, pero no se construye por las dudas.
- **Transferirle el rol dueño a otra persona.** El dueño es uno solo y no se lo pasa a nadie desde
  una pantalla. Es la consecuencia de tener un único dueño, y si alguna vez hace falta, se
  conversa aparte.
- **Un segundo factor de autenticación** (código por mensaje, aplicación de códigos). El cliente no
  lo pidió y suma fricción diaria a un equipo de tres personas.
- **Entrar con una cuenta de correo o de otro servicio.** El acceso es propio del sistema: el
  correo es sólo el nombre de usuario con el que se entra, y no se usa para nada más.
- **Que el sistema mande correos.** No manda ninguno, a nadie, nunca. Todo lo que tenga que
  decirle a una persona —una invitación, un enlace para recuperar la clave— va por WhatsApp, que es
  el mismo canal de los avisos y el que el equipo ya mira.
- **Permisos más finos que el rol** — que una persona vea sólo algunos proveedores, o sólo las
  facturas de cierto monto. Los tres roles son los que describió el cliente, y el catálogo es fijo:
  no hay una pantalla donde el dueño arme un rol nuevo eligiendo secciones. Lo único que se
  distingue dentro de una sección es consultarla o además editarla.
- **Cambiar la cuenta compartida del portal del proveedor.** Esa credencial es de un tercero, vive
  fuera de la aplicación y se reemplaza sin tocar el sistema.
- **El registro de las ediciones de datos** (quién cambió un monto, quién emitió un recibo). Acá se
  registra quién entró y a quién se le negó el paso; el registro de las ediciones es
  **P9 — El problema de no tener control**.
