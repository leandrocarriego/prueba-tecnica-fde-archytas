# Project Brief — Plataforma Cordillera

## Propósito
Este documento captura el acuerdo inicial entre el **Forward Deployed Engineer** y el cliente sobre las necesidades y el desarrollo planificado del proyecto. Este brief sirve como base para generar la documentación de diseño de solución.

- **Versión**: 1.4.0 · **Fecha**: 2026-08-29
- **Creado por**: Forward Deployed Engineer — Archytas
- **Cliente**: Ferretería Industrial Cordillera
- **Proyecto**: Plataforma Cordillera

> Este brief recoge el pedido del cliente en sus propias palabras. Todo lo que dice **cómo** se
> construye la solución (tecnología, diseño interno, infraestructura) queda deliberadamente fuera:
> se define después, en el plan de cada funcionalidad.

---

## Contexto del Cliente

### Resumen del Negocio
Ferretería Industrial Cordillera es una **PyME distribuidora** con más de 20 años en el rubro.
Importa y distribuye productos de ferretería industrial **a través de varios proveedores**.

Con sus palabras: *"Venimos manejando todo a mano y con un sistema viejo que nos dieron hace años,
y necesitamos modernizarnos. No somos gente de tecnología — yo mismo no entiendo mucho de sistemas
— pero sí sabemos lo que necesitamos: algo visual, claro, que se entienda de un vistazo, tanto para
mí como para la gente nueva que estamos sumando al equipo."*

Dos consecuencias directas de esa frase, que valen como criterio transversal de todo el proyecto:
1. **La claridad es un requisito, no una preferencia**: quien usa el sistema no es técnico.
2. **El sistema tiene que ser entendible por gente que recién entra** al equipo.

### El sistema de origen: SIGProv v2.3
Los datos con los que trabaja el negocio hoy viven en **SIGProv v2.3**
(`https://prueba-tecnica-portal.vercel.app`), un portal de gestión **de un proveedor grande**.

Hechos que condicionan todo el proyecto:

- **El portal no es del cliente.** Es de un tercero; Cordillera es usuario, no dueño.
- **No ofrece integración ni API ni exportación por fuera del sistema.** El cliente lo dice
  textualmente: *"no nos permiten integración directa, ni una API, ni un Excel exportable por fuera
  del sistema. Sólo podés entrar con tu usuario, navegar hasta la sección de precios y descargar el
  archivo del día."*
- **El acceso es una cuenta compartida** que entregó el proveedor: *"El usuario que nos dieron es
  compartido, así que cualquiera de nuestra gente puede entrar cuando quiera."*
- **Es de sólo lectura para nosotros.** Nunca se escribe contra SIGProv; todo lo que Cordillera
  produzca vive en su propio sistema.
- **La obtención de los datos se hace automatizando el uso del portal como lo haría una persona**
  (automatización de navegador), porque es la única forma de acceso que el proveedor habilita.

### El problema de fondo
No es un problema de falta de datos: **los datos existen, pero están encerrados en un portal ajeno
y llegan sucios**. Todos los pedidos del cliente son consecuencia de eso. Por lo tanto la limpieza
de los datos no es un detalle interno: es una función visible del producto, con la regla que el
propio cliente enunció y que gobierna el proyecto entero:

> *"Que si algo no se puede resolver solo, nos avise en vez de adivinar mal."*

### Situación Actual — los doce problemas que plantea el cliente
El cliente enumeró doce problemas, con sus palabras y en su orden. Se conservan numerados **P1 a
P12** porque esa es la numeración que va a usar cuando pregunte si algo está resuelto.

| ID | El problema, como lo llama el cliente | Necesidad de negocio |
|----|---------------------------------------|----------------------|
| P1 | El problema de los precios | Tener los precios del proveedor siempre actualizados sin que nadie entre a bajarlos a mano |
| P2 | El problema de las facturas | Que todas las facturas entren a un solo lugar, ordenadas, sin duplicar y sin adivinar |
| P3 | El problema de no ver nada | Ver el negocio de un vistazo, con las ventas mal cargadas señaladas y no sumadas |
| P4 | El problema de los proveedores | Saber con cuántos proveedores trabaja, cuánto le compró y cuánto le debe a cada uno |
| P5 | El problema de los pagos a medias | Ver qué facturas están saldadas, cuáles a medias y cuáles sin tocar |
| P6 | El problema de las compras que se pierden | Seguir las órdenes de compra hasta que se reciben y evitar pedir dos veces lo mismo |
| P7 | El problema de los rubros | Saber cuánto se gasta en cada tipo de producto, con los rubros unificados |
| P8 | El problema de los avisos que nadie mira | Que los avisos y reclamos lleguen a donde se los vea, y saber cuáles quedan sin resolver |
| P9 | El problema de no tener control | Poder registrar y ajustar cosas por cuenta propia, y cambiar parámetros sin depender de nadie |
| P10 | El problema de los accesos | Que cada persona entre sólo a la parte que le toca |
| P11 | El problema de las fechas | Un calendario visual de vencimientos, editable y compartido en vivo |
| P12 | El problema de los recibos | Emitir el recibo de recepción a tiempo y que el sistema avise antes de que se pase la fecha |

**P1 — Los precios.**
*"Necesitamos tener esos precios siempre actualizados en nuestro sistema, sin que alguien tenga que
entrar manualmente todos los días a bajar el archivo."*
El valor no está en bajar el archivo una vez: está en que nadie tenga que acordarse nunca más.

**P2 — Las facturas.**
*"Cada proveedor nos manda sus facturas como puede: algunos un PDF prolijo, otros un PDF que en
realidad es una foto escaneada, otros directamente un Excel armado a las apuradas (a veces con la
fila de títulos movida, a veces con filas vacías en el medio). Y para colmo, el mismo proveedor a
veces figura con el nombre completo, a veces abreviado, a veces con un error de tipeo, nunca
sabemos con certeza si dos facturas son del mismo proveedor o de dos distintos. Necesitamos que
todo esto entre a un solo lugar, ordenado, sin que se nos duplique nada, y que si algo no se puede
resolver solo, nos avise en vez de adivinar mal."*

**P3 — No ver nada.**
*"Tenemos datos de ventas desde 2023 hasta ahora, pero están repartidos y nadie los mira juntos.
Necesitamos poder ver de un vistazo cómo venimos: cuánto facturamos por mes, cómo evolucionaron los
precios, qué pasó con el stock, qué productos son nuevos. El problema es que en esos datos hay
ventas cargadas dos veces por error (cada venta tiene un código, a veces el mismo código aparece
repetido) y otras con datos rotos, necesitamos que se nos avise cuáles son, no que se sumen como si
fueran válidas."*

**P4 — Los proveedores.**
*"No sé con cuántos proveedores trabajo realmente. En el sistema el mismo me aparece escrito de
tres o cuatro formas distintas, así que cuando quiero saber cuánto le compré a uno en el año, no me
da nunca. Y peor: no sé cuánto le debo a cada uno. Con algunos arreglamos pagar a 30 días, con
otros a 45 o 60, pero no tengo forma de saber si les estamos cumpliendo o si hay alguno al que le
venimos pagando tarde hace meses. Me gustaría poder abrir un proveedor y ver, claro: esto le
compré, esto le pagué, esto le debo, y hace cuánto. También necesito tener a mano el mail y el CUIT
de cada uno, porque hoy los buscamos en la libreta."*

**P5 — Los pagos a medias.**
*"Muchas veces no pagamos toda la factura junta: le damos algo a cuenta y el resto más adelante. En
el sistema eso queda registrado, pero yo no tengo manera de ver de una cuáles están saldadas,
cuáles van por la mitad y cuáles no se tocaron. Termino sumando a mano y siempre me da distinto."*

**P6 — Las compras que se pierden.**
*"Cuando pedimos mercadería queda registrado el pedido, pero después nadie lo sigue. No sé cuáles
se recibieron, cuáles siguen esperando y cuáles quedaron ahí sin que nadie las mire. Me pasa de
pedir dos veces lo mismo porque nadie se acordaba del primer pedido."*

**P7 — Los rubros.**
*"Quiero saber cuánto gasto en cada tipo de producto (cuánto en pinturas, cuánto en herramientas,
cuánto en sanitarios) y no puedo. Cada uno cargó las categorías como se le ocurrió, y ahora tengo
el mismo rubro escrito de cinco maneras y varios productos sin nada cargado. Cuando sumo por rubro
me quedan pedazos sueltos por todos lados."*

**P8 — Los avisos que nadie mira.**
*"El sistema tiene una bandeja donde caen mensajes: avisos de que algo está por vencer, y reclamos
de los propios proveedores cuando les debemos. El tema es que nadie entra ahí, así que nos
enteramos cuando el proveedor llama enojado. Todos los días entra alguno nuevo. Necesitaríamos que
eso nos llegue de alguna forma que lo veamos, y saber cuáles quedaron sin resolver."*
El problema no es la bandeja: es que **vive dentro de un sistema al que nadie entra**. Por eso el
aviso tiene que salir de la pantalla del sistema, no ser otra bandeja más.

**P9 — No tener control.**
*"Hoy todo lo hacemos a mano: armar un recibo para un proveedor, registrar que pagamos algo,
ajustar un monto. Queremos poder hacer esas cosas nosotros mismos desde un solo lugar, sin pedirle
a nadie que nos edite un archivo. También queremos poder ajustar nosotros mismos algunos parámetros
(cada cuánto se actualiza el sistema, a partir de qué monto nos tiene que avisar algo) sin depender
de que alguien nos reprograme algo."*

**P10 — Los accesos.**
*"Hoy entramos todos con el mismo usuario y eso ya no me sirve. (…) no quiero que Marcela ande
viendo toda la facturación y las ventas de la empresa, ni que Julián toque las cuentas de los
proveedores. Me gustaría que cada uno tenga su propio acceso y que entre sólo a la parte que le
toca, y que yo sí pueda ver todo. Que no sea que porque conocen la clave pueden entrar a cualquier
lado."*

**P11 — Las fechas.**
*"Necesitamos un calendario visual donde se vea de un vistazo cuándo vence cada factura, poder
agregar un vencimiento nuevo o mover uno si se reprogramó, y que si dos personas de nuestro equipo
lo están mirando al mismo tiempo, ambas vean los cambios en el momento, no que una tenga que
refrescar la página para enterarse."*

**P12 — Los recibos.**
*"Cuando una factura vence, tenemos que generarle un recibo al proveedor (no un pago, un recibo: el
comprobante de que la recibimos y va a ser pagada). Eso se puede generar en cualquier momento hasta
la fecha de vencimiento. El problema es que hoy, si a alguien se le pasa la fecha, nadie se entera
hasta que el proveedor llama preguntando: el sistema viejo no avisa nada. Nos gustaría que el
calendario nos muestre qué facturas ya tienen su recibo generado y cuáles todavía no, y que si se
acerca la fecha de una que sigue sin generar, nos avise antes de que sea tarde."*

### Estado de los doce problemas

Esta es la única sección del brief que **se actualiza con el tiempo**. El resto es el acuerdo tal
como se firmó y no se toca; acá se anota qué se resolvió de lo que se pidió, con la numeración que
el cliente va a usar cuando pregunte.

Lo actualiza el `Release-Manager` en `/ship`, en el mismo paso en que archiva la spec de la
feature. Un problema pasa a **Resuelto** cuando la feature que lo cubre está mergeada y desplegada,
no cuando está escrita.

| ID | Estado | Feature |
|----|--------|---------|
| P1 · Precios | Pendiente | — |
| P2 · Facturas | Pendiente | — |
| P3 · No ver nada | Pendiente | — |
| P4 · Proveedores | Pendiente | — |
| P5 · Pagos a medias | Pendiente | — |
| P6 · Compras que se pierden | Pendiente | — |
| P7 · Rubros | Pendiente | — |
| P8 · Avisos | Pendiente | — |
| P9 · Control propio | Pendiente | — |
| P10 · Accesos | Pendiente | — |
| P11 · Fechas | Pendiente | — |
| P12 · Recibos | Pendiente | — |

Estados: **Pendiente** (todavía no se empezó) · **En desarrollo** (hay una spec aprobada y la
feature se está construyendo) · **Resuelto** (entregado y en uso).

> Esto responde *"¿qué hace el sistema hoy?"* en términos del negocio. La respuesta técnica —cómo
> está construido— está en `ARCHITECTURE.md`, en el código y en sus tests.

### Lo que se midió en el origen
Estas cifras salen del relevamiento del portal SIGProv y sirven para dimensionar el trabajo. Son el
estado del origen al momento del relevamiento, no un objetivo:

| Qué | Cuánto |
|-----|--------|
| Secciones del portal a relevar | 10 pantallas |
| Frecuencia con que el portal actualiza sus contenidos | 2 veces por día |
| Productos en la lista de precios | 100, con su historial propio (entre 2 y 11 puntos cada uno; ~590 en total) |
| Registros de ventas (2023 a hoy) | 588 |
| Ventas duplicadas | 17 grupos comparando el código tal cual viene; 27 si primero se normaliza el código |
| Duplicados con datos en conflicto (mismo código, cantidades distintas) | 6 |
| Ventas con datos rotos | 3 sin fecha, 3 con fecha inexistente (31/02/2025), 3 sin total, 3 con cantidad negativa, 2 con total inflado ×10, 1 apuntando a un producto que no existe |
| Facturas | 100 — de las cuales **46 son PDF escaneado, sin una sola letra extraíble** |
| Estado de las facturas | 26 pagadas, 41 parciales, 33 impagas |
| Facturas sin recibo de recepción | 30, de las cuales **17 ya están vencidas** |
| Comprobantes de pago | 82 |
| Movimientos de cuenta corriente | 182 (todos referencian facturas y pagos existentes) |
| Grafías distintas del nombre de proveedor | 24 en facturas, 20 en órdenes de compra, 13 en remitentes de mensajes |
| Proveedores reales | **8**, con CUIT, correo, teléfono y condición de pago pactada (30, 45 o 60 días) — **confirmado por el cliente el 2026-08-29** |
| Órdenes de compra | 40 — 14 pendientes de envío, 5 enviadas, 10 confirmadas, 11 recibidas |
| Categorías de producto | 19 variantes escritas que corresponden a 7 rubros reales, más 8 productos sin categoría |
| Mensajes en la bandeja | 64 — 27 de vencimiento próximo, 21 reclamos de pago, 16 de stock bajo; 30 sin leer |
| Crecimiento diario del origen | ~3 ventas y ~1 mensaje automático por día |
| Registros que ninguna regla automática debería resolver sola | ~20 |

**Dato que reordena prioridades**: casi la mitad de las facturas (46 de 100) llegan como imagen
escaneada. La lectura automática de documentos escaneados no es un extra opcional: es el formato
más frecuente.

---

## Actores y Roles

Los tres roles salen del pedido del cliente tal como está escrito, incluidos los nombres.

### 1. El dueño
Es quien plantea el pedido. No es técnico. Necesita **ver todo** y decidir.

- **Ve**: todo el sistema, sin restricción.
- **Hace**: administra los accesos de las otras dos personas y ajusta los parámetros del sistema
  (cada cuánto se actualiza, a partir de qué monto avisar, con cuánta anticipación avisar un
  vencimiento). Es el único que toca esa configuración.
- **Su pregunta típica**: *"¿cómo venimos?"* — de un vistazo, y con números que le cierren cuando
  los verifica a mano.

### 2. Marcela — compras y proveedores
*"Tengo a Marcela, que se encarga de la parte de compras y proveedores: ella carga las facturas, ve
los vencimientos, sigue las órdenes de compra."*

- **Ve y trabaja**: proveedores y su cuenta corriente, facturas de compra, pagos, órdenes de
  compra, recibos de recepción, calendario de vencimientos, mensajes y reclamos de proveedores.
- **Ve sólo para consultar**: los precios de lista, porque los necesita para controlar lo que le
  facturan (esa información no revela nada de las ventas de la empresa). Sobre esos precios sí puede
  pedir la lista sin esperar al próximo ciclo y resolver lo que el sistema haya apartado.
- **No accede**: a las ventas ni al tablero comercial del negocio.
- **Resuelve**: las revisiones humanas que caen de su lado (proveedores ambiguos, facturas que no
  se pudieron leer del todo).

### 3. Julián — ventas y números del negocio
*"Y tengo a Julián, que lleva la parte de ventas y los números del negocio."*

- **Ve y trabaja**: ventas, tablero comercial, stock, altas de producto, rubros y catálogo.
- **Ve sólo para consultar**: el calendario de vencimientos y la evolución de los precios.
- **No accede**: a las cuentas de los proveedores ni a las facturas de compra y pagos.
- **Resuelve**: las revisiones humanas de su lado (ventas duplicadas o con datos rotos, productos
  sin rubro).

**Regla que atraviesa a los tres**: *"Que no sea que porque conocen la clave pueden entrar a
cualquier lado."* El acceso restringido tiene que ser real, no un menú que esconde opciones.

---

## Objetivos del Proyecto

### Objetivos Principales
- **Liberar los datos del portal ajeno**: que la información llegue sola y actualizada al sistema
  propio de Cordillera, sin que nadie tenga que entrar a buscarla todos los días.
- **Entregar datos en los que se pueda confiar**: unificar proveedores y rubros, detectar
  duplicados y datos rotos, y **avisar en vez de adivinar** cuando algo no se puede resolver solo.
- **Dar visibilidad de un vistazo** del estado del negocio: qué se facturó, qué se debe, qué está
  por vencer, qué quedó sin seguimiento.
- **Devolverle el control al cliente**: que pueda registrar, ajustar y configurar por su cuenta,
  sin depender de un tercero que le edite un archivo.
- **Separar los accesos de verdad** según lo que hace cada persona.

### Criterios de Éxito (aceptación de alto nivel)
- **CE-1 — Actualización desatendida**: los precios y el resto de la información del portal se
  actualizan solos, con la frecuencia configurada, sin intervención diaria de nadie. El sistema
  muestra cuándo fue la última actualización exitosa y avisa si dejó de funcionar.
- **CE-2 — Nada se descarta, nada se inventa**: ningún registro se pierde en silencio y ningún
  total se completa por suposición. Lo que no se puede interpretar queda apartado, se cuenta y se
  muestra para revisión humana. Cada indicador declara cuántos registros quedaron afuera.
- **CE-3 — Un solo proveedor por proveedor**: el cliente puede abrir un proveedor y ver, con las
  distintas formas de escribir su nombre ya unificadas: *esto le compré, esto le pagué, esto le
  debo, y hace cuánto* — con el atraso medido contra el plazo pactado con **ese** proveedor.
- **CE-4 — Los números cierran**: el saldo de cada factura (saldada, parcial, sin tocar) y los
  totales del tablero coinciden con lo que el cliente verifica a mano. Si alguna vez no cierran, el
  sistema lo señala en vez de pisar el número.
- **CE-5 — Los avisos llegan**: los vencimientos y reclamos llegan fuera del sistema, a un canal
  que el equipo mira, y se sabe cuáles quedan sin resolver y quién es responsable.
- **CE-6 — Cada uno en lo suyo**: Marcela no ve las ventas, Julián no toca las cuentas de
  proveedores, y conocer la dirección de una pantalla no alcanza para entrar.
- **CE-7 — Calendario compartido y en vivo**: dos personas mirando el calendario al mismo tiempo
  ven los cambios en el momento, sin refrescar. Se distingue de un vistazo qué factura ya tiene su
  recibo y cuál no, y se avisa antes de que se pase la fecha.
- **CE-8 — Autonomía**: el dueño cambia los parámetros del sistema (frecuencia, umbrales,
  anticipación de avisos) desde la propia aplicación, sin pedirle nada a nadie.
- **CE-9 — Entendible sin explicación**: una persona nueva en el equipo entiende cada pantalla sin
  capacitación previa.

---

## Alcance Inicial (Alto Nivel)

### En Alcance
- **Obtención automática y periódica** de la información publicada en SIGProv: precios y su
  historial, ventas, facturas y sus archivos, pagos, cuenta corriente, órdenes de compra,
  proveedores, catálogo y bandeja de mensajes.
- **Lectura de las facturas en sus tres formatos** (PDF legible, PDF escaneado y planilla), con
  carga de los datos de cabecera: número, fecha, proveedor y total.
- **Unificación de proveedores**: reconocer que las distintas formas de escribir un nombre
  corresponden al mismo proveedor, contra el padrón real de 8.
- **Unificación de rubros**, con los productos sin clasificar a la vista y no escondidos.
- **Detección de duplicados y datos rotos** en ventas, con apartado para revisión en vez de suma.
- **Cola de revisión humana**: todo lo que no se resuelve con una regla defendible queda en una
  bandeja con responsable asignado, y cada decisión que toma una persona queda como criterio para
  que el mismo caso no se pregunte dos veces.
- **Tablero del negocio** desde 2023: facturación por mes, evolución de precios, movimiento de
  stock, altas de producto — cada número declarando qué quedó excluido.
- **Ficha de proveedor** con compras, pagos, deuda, antigüedad de la deuda, atraso promedio contra
  el plazo pactado, CUIT, correo y teléfono.
- **Estado de pagos** por factura: saldada, parcial o sin tocar.
- **Seguimiento de órdenes de compra** hasta la recepción, con detección de órdenes estancadas y
  aviso de pedido repetido al mismo proveedor.
- **Avisos fuera del sistema** para vencimientos y reclamos, con estado pendiente/resuelto y
  responsable.
- **Calendario de vencimientos** visual, editable (alta y reprogramación), compartido y actualizado
  en vivo entre las personas que lo miran a la vez.
- **Recibos de recepción**: emisión hasta la fecha de vencimiento y aviso anticipado de los que
  siguen sin emitir.
- **Carga y ajuste manual** desde la propia aplicación (emitir un recibo, registrar un pago,
  ajustar un monto, cargar un vencimiento), con registro de quién lo hizo, cuándo y cuál era el
  valor anterior.
- **Tres accesos separados** con permisos reales, según los roles descritos arriba.
- **Parámetros configurables por el dueño** desde la aplicación.

### Fuera de Alcance (por ahora)
- **Escribir cualquier cosa en el portal SIGProv.** El origen es de sólo lectura. Todo lo que
  Cordillera produzca vive en su propio sistema.
- **El detalle de artículos de las facturas que llegan escaneadas.** Se carga la cabecera (número,
  fecha, proveedor, total), que es lo que alimenta la deuda, el calendario y los recibos. A la
  calidad de imagen del origen, leer la lista de artículos daría un error tan alto que habría que
  revisar todo a mano igual.
- **Conciliación bancaria.** No existe ningún dato de banco en el origen; prometerla sería inventar
  una fuente.
- **Multi-empresa o multi-sucursal.** Hoy no existe el caso.
- **Predicción de demanda o sugerencia automática de compra.** No se apoya un pronóstico sobre
  datos de ventas que todavía tienen duplicados sin resolver. Se puede reconsiderar cuando la cola
  de revisión esté vacía y haya histórico limpio.
- **Reemplazar el portal SIGProv.** El proveedor lo sigue operando; Cordillera lo sigue usando como
  origen.

---

## Dirección de Solución Propuesta

Lo que sigue es **la propuesta del Forward Deployed Engineer**, no una parte del acuerdo. El alcance
de arriba es lo que se compromete; esto es *cómo se piensa encarar*, en los términos del negocio, y
está sujeto a lo que el cliente responda en las consultas que acompañan cada punto.

Se incluye por una razón concreta: hay decisiones que **no son técnicas y sólo puede tomarlas el
cliente** —por dónde quiere que le lleguen los avisos, si acepta un costo por documento leído, si su
equipo va a instalar algo en el teléfono—. Esas decisiones cambian la solución, y conviene que estén
sobre la mesa antes de escribir la primera especificación.

**La solución general es una aplicación web hecha a medida para Cordillera**, que toma la
información del sistema viejo y la convierte en el sistema propio del negocio. El portal del
proveedor sigue existiendo y sigue siendo el origen; deja de ser el lugar donde se trabaja.

### Los precios (P1)
El sistema entra al portal por su cuenta, trae la lista del día, la ordena y actualiza los precios,
con la frecuencia que configure el dueño. La lista queda del lado nuevo, en una pantalla simple y
directa.

> **Consulta pendiente**: hace falta saber si la lista diaria **sólo cambia precios** o si también
> da de alta y de baja productos. Si el listado de productos es estable, actualizar es sencillo. Si
> se mueve, hay que decidir con el cliente qué pasa cuando un producto deja de aparecer: si se dio
> de baja de verdad, o si faltó por un error del proveedor. Esa diferencia no la puede adivinar el
> sistema.

### Las facturas y los proveedores (P2, P4)
Son la misma cosa mirada desde dos lados, y por eso se resuelven juntas. Cada proveedor tiene su
**perfil**: sus datos fiscales, su contacto, el plazo de pago acordado y todas sus facturas. Y en
paralelo hay una pantalla de **facturas** con todas juntas, ordenables, filtrables y buscables por
CUIT o razón social.

Sobre la lectura de los archivos: dado que casi la mitad llega como imagen escaneada y las planillas
vienen irregulares, **leerlas exige lectura automática asistida**, no reglas fijas. Es la parte de
mayor riesgo del proyecto y la única que puede implicar un **costo recurrente por documento leído**
— lo que choca con la restricción de presupuesto declarada más arriba y hay que conversarlo.

> **Consultas pendientes**: si las facturas llegan también por correo electrónico, y si las facturas
> reales traen el CUIT del proveedor. Lo segundo importa mucho: con CUIT, reconocer al proveedor
> deja de ser una interpretación y pasa a ser una certeza, y buena parte del riesgo de confundir
> proveedores desaparece. En las facturas de muestra el CUIT no aparece.

### Los pagos y los recibos (P5, P12)
El estado del pago **vive en la factura**, no en una lista aparte, para que no haya dos lugares
diciendo cosas distintas. Los pagos se toman de los comprobantes que ya existen en el sistema viejo
y se imputan a su factura, que queda mostrando su estado: saldada, sin tocar, o **parcial con el
porcentaje pagado a la vista**. Los recibos se leen de la misma fuente y sirven para contrastar
contra los vencimientos y avisar antes de que se pase la fecha.

Lo que se acordó el 2026-08-29, al cerrar las dudas de la feature de pagos y recibos:

- **El estado de pago lo dicen los comprobantes, no el sistema viejo.** Si el portal informa que una
  factura está pagada y sus comprobantes no llegan al total, no gana el portal: la factura queda
  señalada con los dos datos a la vista.
- **El recibo de recepción es un documento que genera el sistema**, con numeración propia y
  correlativa, y se descarga para mandárselo al proveedor. Emitirlo tarde sigue sin permitirse.
- **Una factura que se pasó de fecha sin recibo no queda trabada para siempre**: compras cierra el
  incidente explicando qué se hizo, y queda registrado quién lo cerró y cuándo.
- **La fecha de vencimiento sale siempre del plazo pactado con el proveedor**, y no de ninguna otra
  fecha que traiga el documento.
- **Un mismo pago puede cubrir varias facturas** —es habitual, corrige lo que se había supuesto del
  relevamiento— y el reparto entre esas facturas lo hace una persona, nunca el sistema.
- **La antigüedad de la deuda y el atraso promedio se cuentan desde el vencimiento**, e incluyen lo
  que se debe y ya se pasó de fecha.

### Los vencimientos (P11)
Un calendario donde se ve de un vistazo qué vence y cuándo, con los vencimientos moviéndose
arrastrándolos, y actualizándose para todos los que lo estén mirando en el momento en que alguien
cambia algo. Es la parte del sistema con más exigencia de experiencia de uso, y también la más
exigente por dentro.

### Los rubros (P7)
Como los rubros cargados son pocos, no hace falta nada sofisticado: se relevan las formas en que
están escritos y se arma una **equivalencia entre ellas**, de modo que "pinturas", "Pintura" y
"PINTURERIA" cuenten como el mismo rubro. Con eso ya se puede mostrar cuánto se gasta en cada uno.
Cuando aparezca una forma nueva que la equivalencia no conoce, se pregunta en vez de meterla en un
cajón de "otros".

### Los avisos (P6, P8, P12)
Es el mismo problema tres veces —una orden que se estancó, un reclamo que entró, un recibo por
vencer— y se resuelve una sola vez eligiendo **por dónde llega el aviso**. Hay tres caminos y cada
uno tiene su costo:

| Camino | A favor | En contra |
|---|---|---|
| **WhatsApp** | Es donde el equipo ya mira. Es el que más chance tiene de que el aviso se vea de verdad. | Puede resultar invasivo, y tiene costo por mensaje. |
| **Correo electrónico** | Sin fricción y sin costo. | Es otra bandeja — el mismo riesgo que hoy tiene la bandeja del portal, que nadie mira. |
| **La aplicación instalada en el teléfono**, avisando como avisa cualquier app | Llega al teléfono sin costo por aviso. | Sólo funciona si las tres personas la instalan y aceptan recibir avisos. |

> **Consulta pendiente, y de las importantes**: por cuál de los tres. Es la única decisión del
> proyecto que puede fallar por razones que no tienen nada que ver con la tecnología. Si el canal
> les incomoda, lo apagan, y el problema de los avisos vuelve al punto de partida.

### El control propio y los accesos (P9, P10)
Un panel donde el dueño ajusta los parámetros del sistema, y **acciones de un solo botón** para lo
que hoy se hace a mano: registrar un pago, emitir un recibo, ajustar un monto. Los accesos son los
tres descritos en *Actores y Roles*, con permisos que se verifican de verdad.

Al definir la feature de accesos (spec `002`, firmada el 2026-08-29) se resolvió cómo funciona
cada uno de esos accesos. **Son decisiones del FDE, tomadas para poder avanzar, y esperan
confirmación del cliente**:

- **Los roles son tres y el dueño es uno solo.** No hace falta un cuarto acceso técnico por encima
  de él, y no hay pantalla para armar roles nuevos: quien entra al equipo entra en uno de los tres.
- **Cada sección se habilita como consulta, o como consulta y edición.** Ver algo no habilita a
  cambiarlo.
- **A alguien nuevo lo da de alta el dueño** con su nombre, su teléfono y su rol, y esa persona
  define su propia clave desde una invitación: el dueño no conoce la clave de nadie.
- **La invitación y la recuperación de clave llegan por WhatsApp**, el mismo canal de los avisos.
  Se eligió así porque Cordillera no tiene dominio propio de correo.
- **La sesión se cierra a las ocho horas sin uso**, y probar claves hasta acertar bloquea el acceso
  un rato.

> **Consulta pendiente**: cuando el cliente dice *"hoy todo lo hacemos a mano"*, no quedó claro si
> se refiere a papel, a una planilla aparte o al sistema viejo. Las tres llevan a soluciones
> distintas y **no se asumió ninguna**.

### El tablero (P3)
Va al final, y no por importancia: el tablero muestra los datos ya limpios, así que depende de que
antes estén resueltos los proveedores, las facturas, los pagos y los rubros. Construirlo antes sería
mostrar prolijamente números que todavía no cierran.

> El detalle técnico de esta propuesta —qué herramientas, con qué mecanismo, a qué costo— **no está
> en este documento a propósito**, porque todavía no está decidido y porque este documento se firma.
> Vive en el relevamiento técnico interno del equipo, y cada decisión se toma y se justifica al
> planificar la funcionalidad que la necesita.

---

## Requisitos Clave

### Requisitos Funcionales
Numerados según el problema del cliente que resuelven.

- **RF-P1** — Actualizar los precios y su historial de forma automática y periódica, sin que nadie
  entre al portal a bajar el archivo. Mostrar la evolución por producto, la variación contra el mes
  anterior y qué productos subieron más de un porcentaje configurable.
- **RF-P2** — Recibir las facturas en sus tres formatos y llevarlas a un único lugar ordenado, sin
  duplicar. Cuando un dato no se puede leer con confianza, no se asume: se pregunta.
- **RF-P3** — Tablero desde 2023 con facturación por mes, evolución de precios, stock y altas de
  producto. Las ventas duplicadas y las que tienen datos rotos se señalan y **no se suman**; cada
  indicador informa cuántos registros excluyó.
- **RF-P4** — Unificar las distintas grafías de cada proveedor contra el padrón real, y ofrecer una
  ficha por proveedor con compras, pagos, deuda, antigüedad, atraso contra su plazo pactado, CUIT,
  correo y teléfono.
- **RF-P5** — Imputar los pagos parciales a sus facturas y calcular el saldo, mostrando tres
  estados diferenciados: saldada, parcial y sin tocar. Filtrable por proveedor y por vencimiento.
- **RF-P6** — Seguir el ciclo de vida de cada orden de compra hasta la recepción, marcar las que
  quedaron estancadas más de N días (N configurable) y avisar al registrar un pedido si ya existe
  otro parecido al mismo proveedor dentro de una ventana configurable — avisar, no bloquear.
- **RF-P7** — Unificar las variantes de categoría en los rubros reales, permitir clasificar los
  productos sin rubro con confirmación humana, y mostrar "sin rubro" como categoría visible en
  todos los cortes para que los totales por rubro sumen el total general.
- **RF-P8** — Traer los mensajes de la bandeja del portal, identificar al proveedor que los envía,
  clasificarlos por tipo, agregarles estado pendiente/resuelto y responsable, y **hacerlos llegar
  fuera del sistema** (resumen diario y aviso inmediato para reclamos y vencimientos críticos). Un
  mensaje ya visto no vuelve a avisar.
- **RF-P9** — Permitir al equipo emitir recibos, registrar pagos, ajustar montos y cargar
  vencimientos desde un solo lugar, con registro de autor, momento y valor anterior. Permitir al
  dueño editar los parámetros del sistema desde la aplicación, sin intervención técnica.
- **RF-P10** — Tres accesos individuales con permisos reales por rol, verificados en cada consulta
  y no sólo escondiendo opciones del menú.
- **RF-P11** — Calendario visual de vencimientos: alta de vencimientos propios, reprogramación
  (guardando la fecha original), y visualización compartida que se actualiza en vivo para todas las
  personas que lo estén mirando.
- **RF-P12** — Emitir el recibo de recepción en cualquier momento **hasta** la fecha de vencimiento
  y no después; mostrar en el calendario qué facturas ya lo tienen y cuáles no; avisar con N días
  de anticipación las que siguen sin emitir; y señalar como incidente las vencidas sin recibo.

### Requisitos No Funcionales
- **Claridad de uso**: *"algo visual, claro, que se entienda de un vistazo"*. Las pantallas tienen
  que ser comprensibles para gente no técnica y para personas que recién entran al equipo. Es un
  requisito explícito del cliente, no una preferencia estética.
- **Honestidad de los números**: ningún total puede mentir por omisión. Todo indicador que excluya
  registros lo declara, con acceso directo a los registros excluidos.
- **Rendimiento**: el volumen actual es chico (100 productos, 100 facturas, 588 ventas, 40 órdenes,
  64 mensajes) y crece a ~3 ventas y ~1 mensaje por día. La exigencia no es de volumen sino de que
  las pantallas de consulta respondan rápido y el trabajo pesado (obtención y lectura de documentos)
  no las trabe. *Los tiempos de respuesta objetivo quedan **pendientes de acordar con el cliente**.*
- **Seguridad**:
  - Accesos individuales por persona, con permisos verificados en cada consulta.
  - Las credenciales del portal SIGProv son de un tercero y viven **sólo en el entorno de
    ejecución**: nunca en la base de datos, nunca en el repositorio, nunca en un registro de
    actividad. Si el proveedor las cambia, se reemplazan sin tocar el sistema.
  - Toda edición manual queda registrada con autor, momento y valor anterior.
- **Disponibilidad y confianza operativa**: un proceso de actualización caído hace más daño que no
  tenerlo, porque el cliente decidiría con datos viejos creyéndolos frescos. El sistema muestra
  cuándo fue la última actualización exitosa y avisa al dueño cuando falla de forma repetida.
- **Escalabilidad**: el volumen actual está muy por debajo de cualquier límite. *Las expectativas
  de crecimiento del negocio a 2–3 años quedan **pendientes de acordar con el cliente**.*
- **Idioma**: toda la aplicación y su documentación de cara al cliente, en español.

---

## Integraciones y Automatizaciones

### Servicios/APIs Externos
- **SIGProv v2.3** (`https://prueba-tecnica-portal.vercel.app`) — **única fuente de datos**. De sólo
  lectura. **No expone API ni integración ni exportación por fuera del sistema**: la obtención de
  los datos se hace automatizando la navegación del portal como lo haría una persona, con la cuenta
  compartida que entregó el proveedor.
- **Canal de aviso fuera del sistema** (P8, P12) — necesario para que los avisos lleguen a donde el
  equipo los vea, ya que la bandeja del portal *"nadie la mira"*. **El canal concreto (mensajería,
  correo u otro) queda pendiente de acordar con el cliente**, junto con quién recibe qué.

### Automatizaciones Necesarias
- **Ninguna acordada.** No surgió de la conversación con el cliente ninguna necesidad de una
  plataforma de automatización externa. **Pendiente de acordar con el cliente** si existe alguna
  herramienta que ya usen y que deba conectarse.

### Tareas en Background
Procesos que corren solos, sin nadie mirando:

- **Actualización periódica desde SIGProv**: recorre las secciones del portal y trae lo nuevo. La
  frecuencia la configura el dueño; el origen se actualiza dos veces por día, así que no hace falta
  más que eso.
- **Lectura de los archivos de factura**, incluidos los 46 escaneados, que es el trabajo más lento
  del proceso.
- **Envío de avisos**: resumen diario de la bandeja y avisos inmediatos de reclamos, vencimientos
  críticos y recibos por vencer.
- **Control de salud del proceso**: aviso al dueño si la actualización falla de forma repetida.

---

## Restricciones Conocidas

### Restricciones Técnicas
- **El portal es de sólo lectura.** Nunca se escribe contra SIGProv.
- **El portal no ofrece API, integración ni exportación por fuera del sistema.** La única vía de
  acceso es la que usa una persona, y por eso la obtención se hace automatizando la navegación.
- **Las credenciales del portal son de un tercero y viven sólo en el entorno de ejecución.** Es una
  cuenta compartida; el proveedor puede cambiarla en cualquier momento sin avisar.
- **El portal impone su propio ritmo**: la sesión se corta por inactividad a las 8 horas, los
  enlaces de descarga de archivos caducan a los 45 segundos de generarse, y una de las secciones
  (ventas) sólo se puede recorrer página por página y en orden. Nada de esto es negociable con el
  proveedor.
- **Nada se descarta.** Un dato que no se puede interpretar no se borra ni se completa por
  suposición: queda apartado en cuarentena, contado y visible, y genera una revisión humana.
- **El contenido no se sobrescribe.** Lo que se obtiene del portal se conserva tal como llegó, de
  modo que se pueda volver a procesar todo el histórico cuando cambia un criterio, sin volver a
  pedirle nada al portal.
- **Casi la mitad de las facturas son imagen.** 46 de 100 no tienen texto extraíble; la lectura
  automática de imágenes es el camino principal, no una excepción.

### Restricciones de Negocio
- **El cliente no es técnico** y no puede exigirle cambios al proveedor dueño del portal.
- **La separación de accesos es innegociable**: es un pedido explícito del dueño, no una mejora.
- **El equipo es chico**: tres personas. Una cola de revisión que exija demasiado tiempo por caso
  se abandona — que es exactamente lo que ya pasó con la bandeja de mensajes del portal.
- **Presupuesto**: el trabajo se resuelve con herramientas sin costo de licencia. No hay
  presupuesto acordado para servicios pagos. *Cualquier costo recurrente queda **pendiente de
  acordar con el cliente**.*

### Restricciones de Tiempo
**Pendiente de acordar con el cliente.** No hay fecha límite, hitos ni fecha de puesta en marcha
definidos en la conversación inicial. Debe acordarse antes de comprometer un plan de entrega.

---

## Riesgos Conocidos

| # | Riesgo | Impacto | Cómo se acota |
|---|--------|---------|---------------|
| R1 | **El portal es de un tercero y puede cambiar sin aviso.** Cualquier rediseño de sus pantallas rompe la obtención de datos. | Alto — el sistema se queda sin datos nuevos | Depender lo menos posible de detalles frágiles de la pantalla; detectar la falla y avisar rápido en vez de seguir en silencio; conservar copias del contenido tal como llegó para poder reprocesar sin el portal |
| R2 | **46 de las 100 facturas son PDF escaneado sin texto extraíble.** La lectura automática de una imagen nunca es perfecta. | Alto — es el formato más frecuente | Se evalúa la confianza dato por dato: se carga lo confiable y se pregunta sólo por lo dudoso, mostrando el recorte de la imagen para que la persona decida en segundos. El detalle de artículos de esas facturas queda fuera de alcance |
| R3 | **Ambigüedad en los nombres de proveedor.** El mismo proveedor aparece con hasta 24 grafías distintas entre facturas, órdenes y mensajes. | Alto — con los proveedores mal resueltos se caen a la vez la deuda, las órdenes, los vencimientos y los recibos | Se resuelve contra el padrón real de 8 proveedores en lugar de adivinar cuántos hay; lo que no se resuelve con certeza va a revisión humana y la decisión queda guardada como criterio |
| R4 | **Las planillas de factura pueden cambiar de forma.** Hoy todas las relevadas tienen la misma estructura, pero el cliente advierte que llegan "armadas a las apuradas". | Medio | Un archivo con forma inesperada abre una revisión en vez de leer datos equivocados: falla ruidosa, no silenciosa |
| R5 | **Duplicados de venta sin forma honesta de resolverlos.** Hay 6 casos con el mismo código y cantidades distintas: puede ser una carga doble con un tipeo o dos ventas reales mal codificadas. | Medio | El sistema no elige: muestra las dos versiones lado a lado y espera la decisión de una persona |
| R6 | **La cuenta del portal es compartida y de un tercero.** Si el proveedor la cambia o la revoca, la actualización se detiene. | Medio | La credencial se reemplaza sin tocar el sistema; la caída se detecta y se avisa |
| R7 | **Riesgo de abandono de la cola de revisión.** Si revisar cada caso cuesta tiempo, el equipo deja de entrar — como ya pasó con la bandeja del portal. | Medio | Cada caso se resuelve en segundos, con el contexto necesario a la vista, responsable asignado y la decisión guardada para no repreguntar |
| R8 | **Trabajo atrasado visible desde el primer día.** Al encender el sistema aparecen 17 facturas ya vencidas sin recibo y 30 mensajes sin leer. | Bajo — pero puede leerse como un error del sistema | Se acuerda con el cliente que ese es el estado real heredado, y se presenta como trabajo pendiente, no como falla |

---

## Supuestos

- El portal SIGProv seguirá disponible y con la cuenta compartida activa mientras dure el proyecto.
- El contenido que publica el portal es correcto salvo lo que se identifique como sucio: no se
  audita al proveedor, se procesa lo que publica.
- El equipo se mantiene en tres personas con los roles descritos. Si se suman más, los roles
  existentes alcanzan como molde.
- El cliente tiene alguien disponible a diario para atender la cola de revisión — sin eso, los
  casos ambiguos se acumulan y los totales quedan incompletos.
- El volumen del negocio se mantiene en el orden actual durante el primer año.
- El histórico relevante arranca en 2023, como indica el cliente.

---

## Próximos Pasos

1. El Forward Deployed Engineer escribe este brief a partir de la reunión con el cliente.
2. Para cada funcionalidad se redacta una **especificación**: qué va a hacer el sistema, para
   quién y en qué casos. Va en español y sin detalle técnico, para que se pueda leer y discutir
   sin conocer el sistema por dentro.
3. Se repasa con el cliente hasta sacarle las ambigüedades, y **el cliente la aprueba**. Ese
   acuerdo es el que después se verifica contra lo construido.
4. Recién con la especificación aprobada arranca la construcción: primero se decide cómo se
   resuelve, después se escribe el código y sus pruebas.

---

## Notas

### Pendientes de acordar con el cliente
Ninguna de estas cosas surgió de la conversación inicial ni del material relevado. **No se
completaron por suposición**; hay que cerrarlas antes de comprometer un plan de entrega.

1. **Plazos, hitos y fecha de puesta en marcha.** No hay ninguna fecha definida.
2. **Quién recibe cada tipo de aviso en P6 y P8** — órdenes estancadas, reclamos de proveedores y
   el resumen diario de la bandeja. *El canal ya está acordado y los avisos de vencimiento sin
   recibo ya tienen destinatario — ver Resueltas.*
3. **Valores iniciales de los parámetros configurables**: cada cuánto actualizar, a partir de qué
   monto avisar, a partir de cuántos días una orden de compra se considera estancada, y qué
   porcentaje de suba de precio amerita destacar. *La anticipación del aviso de vencimiento sin
   recibo ya está acordada — ver Resueltas.*
4. **Tiempos de respuesta esperados** de las pantallas y expectativas de crecimiento a 2–3 años.
5. **Quién administra los accesos** en el día a día y qué pasa cuando se suma alguien nuevo.
   *La spec `002` asume que los administra el dueño y que a alguien nuevo lo da de alta él, con una
   invitación por WhatsApp para que esa persona defina su propia clave. **Falta que el cliente lo
   confirme.***
6. **Dónde y cómo se pone en marcha el sistema** (entorno, responsable de la operación).
7. **Si existe alguna herramienta que el cliente ya use** y que deba conectarse.
8. **Si la lista diaria de precios sólo actualiza precios, o también da de alta y de baja
   productos** — y con qué frecuencia y en qué horario se actualiza. *Sin esto no se puede decidir
   qué hace el sistema cuando un producto deja de aparecer en la lista.*
9. **Qué significa exactamente *"hoy todo lo hacemos a mano"*** (P9): papel, planilla aparte o el
   sistema viejo. *Las tres llevan a soluciones distintas y ninguna se asumió.*
10. **Si hace falta un cuarto acceso, técnico, por encima del dueño**, o si con los tres roles
   descritos alcanza. *Depende de quién opere el sistema en el día a día — consulta 5. La spec
   `002` asume que **no hace falta**: tres roles y un solo dueño. **Falta que el cliente lo
   confirme.***

### Resueltas con el cliente

Se cierran acá para que no queden dos versiones de la misma pregunta. Cada respuesta entró además a
la spec de la feature que la necesitaba.

| # original | Consulta | Respuesta del cliente | Fecha |
|---|---|---|---|
| 2 | Canal por el que llegan los avisos | **WhatsApp**, que es donde el equipo ya mira. El aviso de un vencimiento sin recibo lo recibe compras, con copia al dueño. Queda por definir quién recibe cada tipo de aviso en P6 y P8. **Desde el 2026-08-29 ese canal lleva además las invitaciones y las recuperaciones de clave** (P10), así que ya no sólo avisa: sin él nadie puede entrar por primera vez | 2026-08-29 |
| 3 | Con cuántos días de anticipación avisar un vencimiento sin recibo | **Tres días**, como valor inicial. El dueño lo cambia cuando quiera desde los parámetros del sistema | 2026-08-29 |
| 5 | Padrón de proveedores y condiciones de pago | **Son 8 y no más**, y los plazos que publica el portal —30, 45 o 60 días— son los vigentes. El plazo entra como valor inicial de cada ficha y se corrige desde ahí | 2026-08-29 |
| 11 | Si las facturas reales traen el CUIT del proveedor | **Algunas sí y otras no.** Con CUIT la identificación es una certeza; sin CUIT se resuelve por el nombre contra el padrón, y lo que no sea concluyente va a revisión humana | 2026-08-29 |
| 12 | Si las facturas llegan también por correo electrónico | **No.** El portal sigue siendo la única fuente y el alcance acordado no se mueve | 2026-08-29 |
| 5 | Qué hacer con las 17 facturas ya vencidas sin recibo el primer día | **Entran como trabajo pendiente señalado**, con la fecha en que se pasaron. El recibo no se emite fuera de término: compras cierra cada caso explicando qué se hizo | 2026-08-29 |
| 15 | Si acepta un costo recurrente por documento leído | **No.** La lectura se resuelve con herramientas sin costo de licencia, y se acepta la consecuencia: más facturas caen en la cola de revisión | 2026-08-29 |

### Aclaración de vocabulario
El cliente usa la palabra **recibo** en un sentido preciso, que conviene no confundir: *"no un
pago, un recibo: el comprobante de que la recibimos y va a ser pagada"*. Es el comprobante de
recepción de la factura, se emite hasta la fecha de vencimiento, y es distinto del comprobante que
se entrega al pagar. Ambos existen en el negocio y el sistema tiene que distinguirlos.

### Versionado de este documento

El brief se versiona porque el cliente lo lee y lo acuerda: sin una versión, "el brief" es
ambiguo apenas cambia una línea, y no se puede decir sobre cuál hubo acuerdo.

`MAJOR` — cambia el alcance acordado: entra o sale un problema, se mueve algo de *En alcance* a
*Fuera de alcance*.
`MINOR` — se agrega o se precisa un requisito sin mover el alcance.
`PATCH` — redacción, ejemplos, aclaraciones que no cambian lo acordado.

**Actualizar el *Estado de los doce problemas* no cambia la versión.** Esa tabla anota el avance,
no el acuerdo; por eso es la única sección que se edita sin conversarlo con el cliente.

Todo cambio de versión se acuerda con el cliente y se anota acá:

| Versión | Fecha | Qué cambió |
|---------|-------|------------|
| 1.4.0 | 2026-08-29 | Se anota lo decidido al definir la feature de accesos (P10) y queda a la espera de confirmación del cliente: tres roles con un solo dueño, permisos de consulta y de edición, alta por invitación y recuperación por WhatsApp. Se precisa que compras resuelve lo apartado de precios y que ventas consulta su evolución. El alcance acordado no se movió. |
| 1.3.0 | 2026-08-29 | Se cierran tres consultas al aclarar la feature de pagos y recibos (2, 3 y 5): el canal de avisos es WhatsApp, la anticipación arranca en tres días y las 17 facturas vencidas sin recibo entran como trabajo pendiente. Se precisa que el recibo es un documento numerado por el sistema, que el vencimiento sale siempre del plazo pactado y que un pago puede cubrir varias facturas, con el reparto a cargo de una persona. El alcance acordado no se movió. |
| 1.2.0 | 2026-08-29 | Se cierran cuatro consultas al cliente (5, 11, 12 y 15); el padrón de 8 proveedores y sus condiciones de pago dejan de ser supuestos y pasan a hecho confirmado. El alcance acordado no se movió: la vía del correo quedó descartada por el propio cliente. |
| 1.1.0 | 2026-08-28 | Se agrega *Dirección de Solución Propuesta* con el enfoque del FDE por problema, y seis consultas nuevas al cliente (10 a 15). El alcance acordado no se movió. |
| 1.0.0 | 2026-08-28 | Versión inicial, a partir de la reunión de relevamiento. |

### Criterio que gobierna todo el proyecto
El cliente lo dijo dos veces, y es el criterio que define si el sistema le va a servir o lo va a
abandonar en un mes:

> *"Que si algo no se puede resolver solo, nos avise en vez de adivinar mal."*

La diferencia entre un sistema que un dueño de PyME usa durante años y uno que abandona está en si
los números le cerraron la primera vez que los verificó a mano.
