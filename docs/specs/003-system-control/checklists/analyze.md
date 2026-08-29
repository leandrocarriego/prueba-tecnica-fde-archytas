# 003-system-control — Consistencia spec ↔ plan ↔ tasks

<!-- ARTEFACTO INTERNO. Hallazgos de `/analyze`. Los registra el Lead; los corrige el rol dueño de cada documento. -->

**Feature:** 003-system-control · **Corrido el:** 2026-08-29 · **Rol:** Lead

## Veredicto: **consistente** (2.ª corrida, 2026-08-29)

La primera corrida dio **inconsistente** con dos hallazgos. Los dos están corregidos y las tres
decisiones que quedaban abiertas las tomó el humano el mismo día. El detalle de cada hallazgo se
conserva abajo: sirve para entender por qué los documentos dicen lo que dicen.

## Hallazgos

### H-1 · Las tareas 15 y 16 dejarían la pantalla de Marcela vacía

**Documento a corregir:** `tasks.md` · **Rol dueño:** Frontend-Architect · **Bloquea `/implement`:** sí, para H3.

RF-20 pide reunir en una pantalla todas las cargas y correcciones disponibles, y RF-21 que cada uno
vea sólo las suyas. Las tareas 15 y 16 construyen el registro y la pantalla, pero **no dicen qué
acciones hay que dar de alta**. Las dos acciones que 003 agrega son de ventas y del dueño:

| Acción nueva | Autorización |
|---|---|
| `POST /catalog/products/{id}/corrections` | `OWNER`, `SALES` |
| `DELETE /catalog/corrections/{id}` | `OWNER` |

Si el registro se llena sólo con eso, **compras entra a la pantalla y no ve nada**, y el criterio de
aceptación de RF-21 —*"esa pantalla le muestra a Marcela acciones distintas de las que le muestra a
Julián"*— pasa de forma vacía o directamente falla.

Las acciones que faltan **ya existen en el código** y son justamente las de compras, verificado en
`triage/routes.py` y `operations/routes.py`, las dos con `require_purchasing()`:

- pedir la lista de precios ahora — `POST /price-updates`
- resolver un caso de la cola de revisión — `POST /triage/cases/{case_id}/resolution`

**Corrección:** la tarea 15 tiene que decir explícitamente que el registro nace con las acciones
que ya existen, no sólo con las de esta feature. Es una línea en la tarea, y sin ella la historia
más chica de la feature es la única que no se puede verificar.

> ✅ **Cerrado el 2026-08-29.** La tarea 15 nombra ahora las dos acciones de compras que ya existen,
> y la 17 exige que ninguno de los dos conjuntos quede vacío.

### H-2 · H2 y H4 están narradas desde Marcela, y en 003 Marcela no puede corregir nada

**Documento a corregir:** `spec.md` · **Rol dueño:** Solution-Designer · **Bloquea `/implement`:** no.

Las dos historias que tratan de corregir un dato tienen a Marcela de protagonista:

- H2 — *"Marcela corrige un monto; el dueño abre el historial…"*
- H4 — *"Como **Marcela**, quiero corregir un dato que llegó mal del portal…"*

El único dato traído del portal que existe hoy es el catálogo de productos y sus precios, y ese dato
es de **ventas**: el brief dice que Marcela *"ve sólo para consultar: los precios de lista"*. Aplicar
RF-24 —*"únicamente las personas con acceso a la sección a la que ese dato pertenece"*— da
`OWNER` + `SALES`, que es lo que el plan decidió, y por lo tanto **Marcela no tiene nada que corregir
hasta que existan las facturas**, que sí son suyas (004).

No es un error del plan ni una omisión: es la consecuencia correcta de un requisito firmado, sobre un
producto que todavía no tiene el módulo donde la historia ocurre. Lo que hay que decidir es si la
spec lo anota o se acepta tal cual — y si conviene reordenar 003 y 004, que **es una decisión del
humano y no de un rol de agente**.

> Se consideró y se descartó la lectura alternativa de RF-24: que *"acceso a la sección"* incluya el
> acceso de sólo lectura que Marcela tiene sobre los precios, y por lo tanto pueda corregirlos. El
> brief la cierra: *"ve **sólo para consultar**"*. La decisión del plan es la correcta.

> ✅ **Cerrado el 2026-08-29.** El humano decidió seguir con la 003 y anotarlo. `spec.md` lleva una
> nota fechada bajo H4 —que no toca ningún requisito ni criterio— y el plan lo registra como riesgo
> con su decisión. Se descartó reordenar 003 y 004: la 004 no tiene spec firmada.

## Decisiones que estaban abiertas

No son hallazgos nuevos —el plan y las tareas los dicen con todas las letras— pero siguen esperando
una decisión del humano y `/analyze` no los da por cerrados:

Las tres se decidieron el **2026-08-29**:

| Qué | Decisión | Dónde quedó |
|---|---|---|
| RF-23 y RF-24 se verifican por analogía: sus criterios nombran facturas, que son de la 004 | Se acepta la analogía. Se corrige la descripción de un producto y se le niega a compras corregirlo; la letra se cierra en la 004 | `plan.md` → Riesgos · `tasks.md` → Notas para `/converge` |
| Cinco de los siete parámetros no los lee ninguna funcionalidad todavía | Se muestran los siete y **la pantalla señala cuáles no tienen efecto**, desde `ParameterSpec.consumed_by` | `plan.md` → Enfoque y Riesgos · `tasks.md` → tareas 7 y 8 |
| Los cinco motivos de corrección los inventó el plan; la spec sólo dice *"una lista corta"* | Se implementan los cinco; el cliente los valida en `/converge`, mientras no haya correcciones etiquetadas | `plan.md` → Riesgos |

## Lo que sí cierra

**Alcance** — los 33 requisitos tienen lugar en el plan y al menos una tarea. Ninguna de las 30
tareas responde a algo que la spec no pida. Las cinco historias tienen tareas y tests propios.

**Trazabilidad** — la tabla de cobertura está completa: 33 de 33 con tarea y con test, sin tareas
citadas que no existan ni tareas huérfanas. Cada criterio de aceptación se corresponde con su
requisito.

**Integridad** — `spec.md` en `Estado: Aprobado`, firmada el 2026-08-29, sin marcadores y sin
decisiones técnicas. Constitution Check completo, 9 de 9 artículos, sin excepciones solicitadas.
Contexto de traspaso presente y con contenido real para las tres audiencias.

**Coherencia con el proyecto** — los cinco módulos que el plan toca existen y ninguno es nuevo. Se
verificaron contra el código las cuatro afirmaciones del plan que podían estar desactualizadas: las
dos constantes a mudar siguen en `operations/service.py`, `catalog` escribe en el schema `core`, la
página `precios/configuracion` existe y hay que darla de baja, y `notifications` ya tiene el envío
encolado que el handler de RF-29 va a reusar.
