# Relevamiento técnico preliminar — Plataforma Cordillera

- **Versión**: 1.1.0 · **Fecha**: 2026-08-29 · *(D1 decidida; hipótesis de P2 corregidas por medición)*
- **Autor**: Forward Deployed Engineer — Archytas
- **Cliente**: Ferretería Industrial Cordillera
- **Estado**: preliminar · **no acordado con el cliente** · **no vinculante**

---

## Qué es este documento, y qué no es

Es la **foto del día del relevamiento**: lo que el FDE vio del portal SIGProv, lo que dedujo, y
hacia dónde le parece que va cada solución. Se escribe una vez, después de la reunión con el
cliente y del recorrido por el portal, y sirve para tres cosas:

1. **Dimensionar** el trabajo antes de que exista una sola spec.
2. **Ordenar** las features: qué desbloquea qué, y qué no se puede empezar sin una respuesta del
   cliente.
3. **Dejar por escrito las consultas** que hay que llevarle al cliente, con el motivo por el que
   cada una importa. Una consulta sin motivo se responde con cualquier cosa.

**Qué no es:**

- **No es el acuerdo con el cliente.** Ese es `docs/PROJECT_BRIEF.md`, y es el único que se firma.
  Si este documento y el brief se contradicen, gana el brief.
- **No es una decisión de arquitectura.** Las decisiones técnicas se toman en el `plan.md` de cada
  feature, con su Constitution Check. Acá hay **hipótesis**, y una hipótesis no obliga a nadie.
- **No es una fuente de verdad que se mantenga al día.** No se actualiza. Cada hipótesis de acá
  **muere** el día en que la feature que la toca tiene su `plan.md`: a partir de ahí, la verdad es
  el plan.

> **Por qué existe separado del brief.** El brief promete en su encabezado que el *cómo* queda
> afuera, y lo promete porque el cliente lo firma: un documento contractual que mezcla lo acordado
> con lo que todavía se está pensando no se puede firmar sin ambigüedad. Pero el trabajo de pensar
> el *cómo* igual ocurrió, y tirarlo sería perder el relevamiento. Vive acá.

### Cómo leer cada sección

Cada problema del cliente (`P1` a `P12`, con la numeración del brief) lleva tres bloques:

- **Hipótesis de solución** — hacia dónde parece ir. No comprometido.
- **A definir en el `plan.md`** — la decisión técnica concreta, y quién la toma.
- **Consultas al cliente** — lo que no se puede decidir sin una respuesta, y **por qué** importa.

Las consultas que llegaron al brief están marcadas con → *brief*, con el número del pendiente al
que corresponden en `docs/PROJECT_BRIEF.md` → *Pendientes de acordar con el cliente*.

---

## Forma general de la solución

Una **aplicación web a medida** para Cordillera, que consume los datos del sistema viejo y los
convierte en el sistema propio del negocio. SIGProv queda como origen de sólo lectura; todo lo que
el cliente produce vive del lado nuevo.

Eso no es una hipótesis: es el Artículo I de la constitución y está acordado en el brief. Lo que
sigue sí lo es.

---

## P1 — Los precios

### Hipótesis de solución
Una lista de precios actualizada del lado nuevo, con una interfaz limpia y directa. Detrás, un
proceso programado que entra al portal, baja el archivo del día, normaliza los datos y actualiza
los precios.

### A definir en el `plan.md`
- **Frecuencia y horario del proceso programado.** Depende de la respuesta del cliente: hoy sólo
  sabemos que el portal se actualiza dos veces por día, no a qué hora.
- **Estrategia de actualización.** Si el padrón de productos es estable, alcanza con actualizar
  precios. Si el archivo diario también da de alta y de baja productos, hace falta una estrategia
  que contemple altas, bajas y productos que dejan de aparecer sin estar dados de baja.
- **Enlaces de descarga que caducan a los 45 segundos** (relevado en el portal): el proceso tiene
  que generar y consumir el enlace sin pasos intermedios lentos.

### Consultas al cliente
1. **¿La lista diaria sólo actualiza precios, o también agrega y elimina productos?** → *brief*
   *Por qué importa*: cambia la estrategia entera. Un `update` de precios es trivial; un padrón que
   se mueve exige decidir qué pasa con un producto que desaparece del archivo — ¿se da de baja, se
   marca inactivo, o quedó afuera por un error del proveedor? Esa última pregunta la contesta el
   cliente, no el sistema (Artículo II: no se descarta).
2. **¿Cuántas veces por día se actualiza, y en qué horario aproximado?** → *brief*
   *Por qué importa*: con el horario se afina el proceso programado. Sin él, hay que sobre-consultar
   el portal, que es de un tercero y con cuenta compartida.

---

## P2 — Las facturas

### Hipótesis de solución
Una entidad **Proveedor** del lado nuevo, con sus facturas asociadas. Dos pantallas:

- **Proveedores** — un perfil por proveedor, con sus datos fiscales y su listado de facturas.
- **Facturas** — todas las facturas juntas, con ordenamiento, filtros y búsqueda por CUIT o razón
  social.

Para leer los archivos, la lectura determinista no alcanza: con 46 de 100 facturas en imagen
escaneada, y planillas "armadas a las apuradas", hace falta lectura asistida por modelo — OCR para
las imágenes y los PDF, y un modelo que interprete las planillas irregulares (fila de títulos
corrida, filas vacías en el medio).

> **Corregido el 2026-08-29 por medición.** La segunda mitad de esa hipótesis era falsa: la planilla
> se resuelve buscando las etiquetas por su nombre en toda la hoja, sin ningún modelo. Y la primera
> quedó más chica de lo que parecía, porque **los cuatro datos de cabecera ya están en la tabla
> renderizada de las 100 facturas**: el archivo se lee igual, pero como segunda lectura que confirma
> o manda a revisión, no como única fuente. Ver `004-invoices-suppliers/research.md`.

### Hallazgo que corrige una hipótesis previa
La primera idea fue **identificar al proveedor por el CUIT de la factura**, lo que evitaría tener
que resolver las 24 grafías distintas del nombre con un modelo.

**Las facturas de muestra relevadas no traen el CUIT.** Una factura real normalmente lo lleva, pero
las que publica el portal, no. Con lo cual:

- El CUIT sirve como identificador **cuando está**, y es el camino preferido porque es determinista.
- Cuando no está —que hoy es el caso de la muestra completa—, hay que resolver contra el padrón de
  8 proveedores por otro medio, y lo que no se resuelva con certeza va a revisión humana.

Esto hay que verificarlo sobre el universo real de facturas antes de planificar, no sobre la
muestra.

### A definir en el `plan.md`
- ~~**Qué modelo y qué OCR.**~~ **Decidido el 2026-08-29** (D1): `pypdf` para el PDF con texto,
  **Tesseract 5 + `spa`** para el escaneado, `openpyxl` para la planilla y `rapidfuzz` para la
  grafía del proveedor. **Ningún modelo de lenguaje.** Sobre las 12 facturas escaneadas medidas,
  Tesseract acertó los 48 datos de cabecera en 0,22 s cada una. La evidencia y las alternativas
  descartadas están en `docs/specs/004-invoices-suppliers/research.md`.
- **Umbral de confianza por dato.** El brief ya compromete el comportamiento (se carga lo confiable,
  se pregunta lo dudoso, mostrando el recorte de la imagen); falta el número y cómo se calibra.
- **Reproceso.** Como `raw` es inmutable y el contenido se conserva tal como llegó, un cambio de
  modelo o de umbral se puede aplicar a todo el histórico sin volver a pedirle nada al portal. Eso
  debería ser una capacidad explícita, no un efecto colateral.

### Consultas al cliente
*Las dos quedaron **contestadas el 2026-08-29**; se dejan con su respuesta para que no se vuelvan a
preguntar.*

3. ~~**¿Las facturas llegan por correo electrónico?**~~ → **No.** El portal sigue siendo la única
   fuente y el alcance acordado no se movió.
   *Por qué importaba*: si llegaran por mail, se podría escuchar la casilla en vez de ir a buscarlas
   al sistema viejo — el archivo llega en su formato original, sin pasar por el portal.
   **Advertencia**: adoptar eso **cambia el alcance acordado**. El brief dice hoy que SIGProv es la
   *única fuente de datos*, y sumar una segunda fuente es un cambio `MAJOR` del brief, con su
   propia conversación. Se releva la respuesta; no se implementa por iniciativa propia.
4. ~~**¿Las facturas reales traen el CUIT del proveedor?**~~ → **Algunas sí y otras no.** Con CUIT
   la identificación es determinista; sin CUIT se resuelve por el nombre contra el padrón y lo que
   no sea concluyente va a revisión. **Ojo con la muestra**: el único CUIT impreso en estas facturas
   es el de Cordillera —el cliente—, no el del proveedor.
   *Por qué importaba*: si lo traen, la identificación del proveedor pasa a ser determinista y buena
   parte del riesgo R3 del brief se desarma.

---

## P4 — Los proveedores

### Hipótesis de solución
Es la contracara de P2 y refuerza la misma estructura: **un perfil por proveedor** con toda su
información — datos fiscales, contacto, condición de pago pactada — más su cuenta de compras con
estado (**pagado**, **pendiente**) y fecha.

El plazo pactado (30, 45 o 60 días) se configura en el perfil del proveedor. De ahí sale el cálculo
contra la fecha actual, y de ahí sale un indicador visible por factura: **atrasado**, **por
vencer**, al día.

Sobre eso se puede montar una notificación —por correo u otro medio— cuando algo cruza el umbral.

### A definir en el `plan.md`
- ~~Si el plazo pactado se toma del portal como valor inicial y después lo edita el cliente, o si se
  carga a mano desde el arranque.~~ **Resuelto el 2026-08-29**: el cliente confirmó que los plazos
  del portal —30, 45 o 60 días— son los vigentes; entran como valor inicial de cada ficha y se
  corrigen desde ahí (004, RF-15 y RF-16).
- Cómo se calcula el "atraso promedio contra el plazo pactado" que el brief compromete en la ficha.

---

## P5 — Los pagos a medias

### Hipótesis de solución
**El estado del pago vive en la factura, no en una entidad aparte**, para no duplicar la
información. Los pagos se toman de la pantalla *Comprobantes de Pago Emitidos* del sistema viejo y
se imputan a su factura.

En el listado, cada factura muestra su estado: saldada, sin tocar, o **pago parcial + porcentaje
pagado**.

### A definir en el `plan.md`
- Si el saldo se guarda calculado o se deriva en cada consulta.
- Qué pasa cuando la suma de los pagos no coincide con el total de la factura. El brief ya fijó el
  comportamiento (CE-4: *"se señala en vez de pisar el número"*); falta el mecanismo.

---

## P6 — Las compras que se pierden

### Hipótesis de solución
El sistema viejo ya tiene el estado de cada orden de compra (relevado: 14 pendientes de envío, 5
enviadas, 10 confirmadas, 11 recibidas). Se toma ese estado y se lo convierte en un aviso que sale
de la pantalla — mensajería, correo, o notificación push si la aplicación se instala en el teléfono.

### A definir en el `plan.md`
~~El canal, junto con P8 y P12~~ → **resuelto por D2**: WhatsApp, confirmado por el cliente el
2026-08-29 durante el `/clarify` de `007-orders-alerts`.

### Consulta técnica — **cerrada el 2026-08-29** contra el portal real
**¿El portal publica, para cada orden de compra, qué producto se pidió?** → **Sí.** Medido sobre
`/ordenes-compra` con `/portal`; el fixture quedó en
`backend/tests/fixtures/portal/purchase-orders-page-2026-08-29.html` y su lectura, en el README de
esa carpeta.

Siete columnas —`Nro. OC`, `Fecha`, `Proveedor`, `Producto/insumo`, `Cantidad`, `Monto estimado`,
`Estado`—, 40 filas, sin paginación. **Una orden es un producto** (40 números de OC distintos), y el
producto viene con el código del catálogo enlazado a su ficha (`COR-0078 …` → `/precios/p78`), así
que se cruza con precios sin adivinar por nombre. **RF-15 se sostiene tal como se firmó**, y el plan
B queda descartado.

La medición destapó además dos cosas que la spec daba por ciertas, ya corregidas en `007/spec.md`:

- **El portal no publica desde cuándo una orden está en su estado**: la única fecha es la del pedido.
  El reloj del estancamiento pasa a ser del sistema, que cuenta desde que observa el estado por sí
  mismo (RF-05, RF-10, RF-48).
- **Con el límite en 15 días, las 29 órdenes en curso quedarían señaladas el primer día** —la más
  nueva tiene 22 días, la mediana 147, y ni con 90 días baja de 26—. El reloj propio lo resuelve: el
  día uno no hay nada señalado. El arrastre del sistema viejo se lista con su antigüedad a la vista
  (RF-49).
- Dato para el `Tester`: **ninguna de las 40 repite el par (proveedor, producto)**. El caso que RF-15
  detecta no existe en los datos reales y su fixture hay que derivarlo a mano.

---

## P7 — Los rubros

### Hipótesis de solución
Los rubros cargados **no son muchos** (relevado: 19 variantes escritas que corresponden a 7 rubros
reales, más 8 productos sin categoría). Con ese volumen no hace falta un modelo: alcanza con relevar
las variantes y armar un **diccionario de sinónimos** que las matchee de forma programática.

Sobre los rubros ya unificados se arma el tablero de gasto por rubro, agrupando las compras hechas.

### A definir en el `plan.md`
- Dónde vive el diccionario: si es configuración editable por el cliente o si vive en el código. Se
  inclina hacia lo primero, porque el brief compromete que *cada decisión humana queda como criterio
  para que el mismo caso no se pregunte dos veces*.
- Qué pasa con una variante nueva que el diccionario no conoce: va a revisión humana, no a un rubro
  "otros" (Artículo II).

> Los 8 productos sin categoría **no se esconden**: el brief compromete "sin rubro" como categoría
> visible, para que los totales por rubro sumen el total general.

---

## P8 — Los avisos que nadie mira

### Hipótesis de solución
Tres canales posibles, y ninguno está decidido:

| Canal | A favor | En contra |
|---|---|---|
| **WhatsApp** | Es donde el equipo ya mira. Es el canal con más chance de que el aviso llegue de verdad. | Puede leerse como invasivo. Tiene costo por mensaje y requiere una cuenta de negocio. |
| **Correo electrónico** | Sin fricción, sin costo, sin permisos. | Es otra bandeja — exactamente el problema que P8 describe. Puede terminar igual que la bandeja del portal. |
| **Aplicación instalable con notificaciones push** | Llega al teléfono sin depender de un tercero ni pagar por mensaje. | Exige que las tres personas la instalen y acepten las notificaciones. Si no lo hacen, no llega nada. |

**Opinión del FDE**: WhatsApp es el que más probabilidades tiene de funcionar, y por eso es el que
más hay que consultar antes de construir. El riesgo R7 del brief (*abandono de la cola de
revisión*) es el mismo riesgo con otro nombre: un aviso en un canal que no se mira es una bandeja
más.

### Consultas al cliente
5. **¿Por qué canal quieren recibir los avisos, y quién recibe qué?** → *brief*
   *Por qué importa*: es la única decisión de este proyecto que puede fallar por razones que no son
   técnicas. Si el canal les resulta invasivo, lo apagan, y P8 vuelve al día uno.

---

## P9 — No tener control

### Hipótesis de solución
Dos piezas distintas:

1. **Un panel de configuración general** del sistema, para los parámetros que el brief ya enumera
   (frecuencia de actualización, umbrales de aviso, días de anticipación, días para considerar
   estancada una orden, porcentaje de suba destacable).

   > **Coordinación con las specs, al 2026-08-29.** `003-system-control` está firmada con **siete**
   > parámetros identificados, y fija la regla de que *cada funcionalidad que necesite un valor
   > ajustable lo publica ahí*. `007-orders-alerts` aporta **dos más**: la ventana de pedido
   > repetido (valor inicial 15 días) y la franja horaria en la que puede sonar un aviso inmediato
   > (valor inicial lunes a viernes de 8:00 a 18:00). El panel arranca entonces con **nueve**.
   > No contradice a `003` —es lo que esa regla prevé—, pero la lista de siete de su `spec.md` deja
   > de ser el inventario completo. Lo verifica el `Lead` en el `/analyze` de las dos features.
2. **Acciones de un solo botón** para lo que hoy se hace a mano: *Registrar pago*, *Emitir recibo*,
   *Ajustar monto*.

### Consultas al cliente
6. **Cuando el cliente dice *"hoy todo lo hacemos a mano"*, ¿a qué se refiere exactamente?** →
   *brief*
   *Por qué importa*: **este punto quedó sin entender en el relevamiento.** No está claro si "a
   mano" significa en papel, en una planilla aparte, o dentro del sistema viejo pantalla por
   pantalla. Las tres cosas llevan a soluciones distintas: si hoy se hace en papel, hay que cargar
   un histórico que no existe en ningún sistema; si se hace en el sistema viejo, ese dato ya está
   en el origen y se puede traer. **No se asume ninguna de las tres.**

---

## P10 — Los accesos

### Hipótesis de solución
Roles de usuario con permisos reales. El relevamiento apuntó a **tres**, que se corresponden con
los actores del brief:

| Rol del relevamiento | Actor del brief |
|---|---|
| Administrador / dueño | El dueño — ve todo, administra accesos y parámetros |
| Compras | Marcela — proveedores, facturas, pagos, órdenes, recibos, calendario |
| Ventas | Julián — ventas, tablero, precios, stock, rubros, catálogo |

La nota del relevamiento mencionaba además un **Superadmin** por encima del dueño.

### Consultas al cliente
7. **¿Hace falta un cuarto acceso técnico, por encima del dueño?** → *brief*
   *Por qué importa*: el brief define hoy tres actores y le da al dueño la administración de los
   accesos. Un Superadmin sólo se justifica si alguien de fuera del negocio va a operar el sistema
   —quién administra el sistema en el día a día ya es un pendiente abierto del brief—. Si no, es un
   rol de más, y un rol de más es superficie de permisos que hay que defender sin que nadie la use.

---

## P11 — Las fechas

### Hipótesis de solución
Un calendario de vencimientos **editable y en tiempo real**, alimentado por las facturas y los pagos
registrados. Visible sólo para el dueño y para compras; ventas lo consulta.

Dos exigencias que el cliente puso explícitamente y que condicionan la solución:

- **En vivo**: dos personas mirándolo a la vez ven el cambio en el momento, sin refrescar. Eso
  empuja hacia una conexión persistente entre el navegador y el servidor, no hacia consultas
  periódicas.
- **Buena experiencia de uso**, con arrastrar y soltar para reprogramar un vencimiento.

### A definir en el `plan.md`
El mecanismo de tiempo real es una decisión del `Frontend-Architect` y del `Backend-Architect`
juntos, y es la decisión técnica de mayor peso de todo el proyecto: es lo único del alcance que no
se resuelve con un ciclo de pedido y respuesta. Conviene que su plan sea el primero en escribirse
después de P1.

> El brief ya compromete que al reprogramar **se guarda la fecha original**. Arrastrar y soltar no
> puede borrar el historial de lo que se movió.

---

## P12 — Los recibos

### Hipótesis de solución
Se toman también los datos de los recibos del sistema viejo, para contrastarlos contra las fechas de
vencimiento de las facturas y disparar los avisos de vencimiento próximo.

Es el mismo canal de P8 y la misma fuente de P5: no es una tercera integración, es la misma leída
con otra pregunta.

### A definir en el `plan.md`
- El brief compromete que el recibo se puede emitir **hasta** la fecha de vencimiento y no después.
  Esa es una regla de negocio con borde duro y necesita su prueba.
- Al arrancar hay **17 facturas ya vencidas sin recibo**. Qué hace el sistema con ellas el primer
  día es un pendiente abierto del brief, no una decisión del plan.

---

## P3 — No ver nada

No surgieron hipótesis técnicas en el relevamiento: el tablero se apoya en datos que primero tienen
que estar limpios. **Depende de P2, P4, P5 y P7**, y conviene que sea de lo último que se construya.

Lo único ya comprometido por el brief, y que condiciona cualquier diseño posterior: las ventas
duplicadas y las rotas **se señalan y no se suman**, y cada indicador informa cuántos registros
excluyó.

---

## Decisiones transversales que no están tomadas

Cuatro decisiones atraviesan varias features. Ninguna se toma en una spec: se toman una vez y valen
para todo el proyecto.

| # | Decisión | Afecta | Quién la toma |
|---|---|---|---|
| D1 | ~~**Qué OCR y qué modelo** para leer facturas escaneadas y planillas irregulares~~ → **Tesseract 5 + `spa`, `pypdf`, `openpyxl` y ningún modelo de lenguaje**, decidido por el Backend-Architect el 2026-08-29 sobre medición, en `docs/specs/004-invoices-suppliers/research.md`. El cliente ya había respondido que **no** acepta costo por documento | P2 (y por dependencia, P3, P4, P5) | El arquitecto — el **costo recurrente** lo aprobaba el cliente, y quedó en cero |
| D2 | ~~**Canal de avisos** fuera del sistema~~ → **WhatsApp. Cerrada**: el cliente la confirmó el 2026-08-29 en el `/clarify` de `007-orders-alerts`, con sus tres bordes definidos — avisos a los **números personales** de cada persona, **reclamos y vencimientos a compras** y **resumen diario al dueño**, y ningún aviso inmediato fuera de la franja **lunes a viernes de 8:00 a 18:00** | P6, P8, P12 | El cliente ✅ |
| D3 | **Mecanismo de tiempo real** para el calendario compartido | P11 | Los dos arquitectos |
| D4 | **Aplicación instalable en el teléfono**, sí o no | P8, P11 (si el calendario se usa en el teléfono) | El cliente, con el costo de que las tres personas la instalen |

**D1 dejó de bloquear P2**: se midió contra el portal real y las cuatro piezas elegidas son libres,
así que la restricción de presupuesto del brief se cumple sin recortar la feature. **D2 quedó
decidida a favor de WhatsApp**, lo que desbloquea la planificación de P6, P8 y P12 — y hace que D4
deje de ser necesaria para los avisos, aunque siga abierta para el calendario en el teléfono. **El
cliente confirmó D2 el 2026-08-29**, así que ya no espera nada.

Lo único que D2 deja abierto no es el canal sino su costo: WhatsApp cobra por mensaje y exige una
cuenta de negocio. **Ese gasto recurrente lo aprueba el cliente**, como el de D1 — que terminó en
cero.

---

## Orden sugerido de construcción

No es un compromiso de entrega —el brief no tiene plazos acordados— sino el orden en que las
dependencias se desatan solas:

1. **P1 — Precios.** No depende de nada, valida el camino de extracción del portal de punta a punta,
   y es el pedido que el cliente puso primero.
2. **P10 — Accesos.** Cuanto antes, mejor: agregar permisos reales sobre pantallas que se
   construyeron sin ellos es rehacerlas. Y es innegociable para el cliente.
3. **P2 + P4 — Facturas y proveedores.** Van juntas: son la misma entidad mirada desde dos lados.
   ~~Bloqueadas por D1.~~ **Desbloqueadas el 2026-08-29.**
4. **P5 + P12 — Pagos y recibos.** Se apoyan en las facturas ya cargadas.
5. **P11 — Calendario.** Necesita facturas, vencimientos y recibos para tener algo que mostrar.
6. **P6 + P8 — Órdenes y avisos.** ~~Bloqueadas por D2.~~ **Desbloqueadas el 2026-08-29**, y con la
   verificación del portal ya hecha (P6 → *Consulta técnica cerrada*). `007-orders-alerts` está sin
   preguntas abiertas, a la espera de sus diagramas y de la firma.
7. **P7 — Rubros.** Independiente y de bajo riesgo; puede adelantarse si algo de lo anterior se
   traba.
8. **P3 — Tablero.** Al final: es la vista de todo lo demás ya limpio.

---

## Cierre

Todo lo de este documento es **preliminar**. Lo que el cliente firma es `docs/PROJECT_BRIEF.md`; lo
que obliga al equipo es la constitución y el `plan.md` de cada feature.

Las consultas de acá que necesitan una respuesta del cliente ya están volcadas al brief, en
*Pendientes de acordar con el cliente*, que es el lugar donde se las va a buscar cuando haya
reunión. **Las de P2 —el correo y el CUIT— ya están contestadas** y figuran en *Resueltas con el
cliente* del brief 1.2.0.
