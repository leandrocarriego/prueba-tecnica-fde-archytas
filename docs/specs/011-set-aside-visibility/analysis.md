# Lo apartado se ve — Análisis de consistencia

**Feature:** 011-set-aside-visibility · **Rol:** Lead · **Fecha:** 2026-08-31
**Veredicto:** **Consistente** — se habilita `/implement`.

## 1. Alcance

- Los **23 requisitos** de la spec tienen tarea y test en `tasks.md`. La única fila sin trabajo por
  construir es **RF-04** (órdenes de compra), y está justificada: el código ya lo cumple desde la
  007 y la enmienda de la spec lo dice. Verificado en el código —
  `triage/handlers.py::open_unreadable_order_rows` existe y abre el caso.
- Las **cinco historias** tienen tareas. H1 es entregable de punta a punta por sí sola.
- **Ninguna tarea sin requisito.** Las tres que a primera vista parecen alcance extra —13b (el nav),
  13c (el fetch de reglas) y 12 (la autorización de las rutas)— responden a RF-06 y RF-12: sin
  ellas el requisito está en el backend y no llega a la persona.

## 2. Trazabilidad

La tabla de cobertura está completa y los criterios de aceptación son uno por requisito, sin
huérfanos en ninguna de las dos direcciones.

## 3. Integridad de los documentos

- `spec.md` en **Estado: Aprobado**, firmada el 2026-08-31, sin `[NECESITA ACLARACIÓN]` y sin
  decisiones técnicas — las tres preguntas abiertas quedaron resueltas en *Decisiones tomadas*.
- El **Constitution Check** del plan recorre los nueve artículos y no declara excepciones.
- El **Contexto de traspaso** está, y está dividido por rol.

## 4. Coherencia con el proyecto

Se verificó contra el código, no sólo contra los documentos. Todo lo que el plan afirma es cierto:

| Afirmación del plan | Verificado |
|---|---|
| Los `kind` existentes son **siete** | Sí — `triage/service.py`, líneas 33-50 |
| `SaleRowsQuarantined` se publica y **nadie lo escucha** | Sí — sólo aparece en el catálogo y en `ingestion/service.py:774` |
| `_quarantined_of` ya existe y lo usan tres normalizaciones | Sí — `ingestion/service.py:780` |
| `normalize_supplier_ledger` y `normalize_messages` apartan sin publicar | Sí — no llaman a `_quarantined_of` |
| `visible_sections(user)` existe en la frontera permitida | Sí — `identity/dependencies.py:121` |
| `CATEGORY_SECTION` dice `PURCHASING` | Sí — `catalog/service.py:202` |

Ningún módulo nuevo, ningún import cruzado nuevo: los cuatro eventos son la única vía entre
`ingestion`/`purchases`/`sales` y `triage`.

## Observaciones menores (no bloquean)

1. **Tarea 16 no nombra `section` en `CaseRead`.** El plan sí lo pide (*«`CaseRead` gana `section`,
   `waiting_days` y `is_stale`»*) y las tareas 11 y 13 lo dan por hecho. Se implementa donde el plan
   lo pone; no hace falta corregir el documento.
2. **RF-22 se testea en la tarea 14** (`test_rbac.py`, backend). El filtro de la UI (tarea 13) no
   tiene test propio, a diferencia de 13b y 13c, que sí lo tienen en 14b. Queda anotado para el
   Tester, no para el Developer.

---

## Lo que este análisis no vio, y la implementación sí (2026-08-31)

Dos defectos del plan aparecieron recién al escribir el código. Quedan acá y no
en un comentario suelto porque el veredicto de arriba dijo «consistente» y no lo
era del todo: un análisis que no se corrige a sí mismo es un análisis en el que
no se puede confiar la próxima vez.

Los dos se me pasaron por el mismo motivo, y vale nombrarlo: verifiqué que **lo
que el plan afirma del código existe**, no que **lo que el plan propone
funcione**. Las seis filas de la tabla de coherencia son todas de la primera
clase.

### 1. El área de un caso de precios contradice la matriz de permisos

El plan archiva los cuatro `kind` de precios bajo `BusinessSection.SALES`.
`identity.permissions.Section.PRICES` es `WRITE` para **compras** y sólo `READ`
para ventas. Con ese mapeo, la cola de precios cambia de dueño: se la saca a
Marcela, que la vacía hoy, y se la da a Julián, que no puede escribir ahí.

`shared/sections.py` documenta la regla que decide el empate —cuando «de qué
área es el dato» y «quién lo decide» divergen, gana el segundo, que es por lo
que los rubros de la 010 van a `PURCHASING`— y por esa regla los cuatro `kind`
serían `PURCHASING`.

> **Resuelto por el Lead el 2026-08-31, y el diagnóstico estaba a medio hacer.**
> Escalé esto como «el plan contradice a la matriz», y no era ahí. El plan
> implementaba fielmente lo que la spec decía; la que se había desviado era la
> **spec**, que en cuatro lugares pone los pendientes de precios del lado de
> Julián. `PROJECT_BRIEF.md` dice lo contrario con las palabras del cliente:
> sobre los precios de lista, Marcela *«sí puede pedir la lista sin esperar al
> próximo ciclo y resolver lo que el sistema haya apartado»*.
>
> Me faltó abrir el brief. Miré el plan contra el código y no contra el
> documento que el plan está obligado a respetar — y el brief es autoridad 6 de
> `AGENTS.md`, lo que hace que esto no sea un descuido menor sino un paso del
> procedimiento que salteé. Fallo: los siete `kind` existentes son
> `PURCHASING`; `spec.md` enmendada, `plan.md`, la migración y los handlers
> corregidos.

### 2. RF-20 no tiene con qué cerrarse del lado de los pagos

El plan hace que `purchases` publique el cierre automático «cuando un pago
retenido se imputa o se reparte», y que `triage` cierre el caso que coincida.
Los dos extremos existen; **no son el mismo caso**. Un comprobante ilegible
nunca llega a ser un `Payment`: se queda apartado en `staging`, que es
exactamente el silencio que esta feature cierra abriéndole un caso. Un
comprobante **retenido** sí es un `Payment`, y no abre ningún caso.

El criterio de aceptación de RF-20 usa justamente el ejemplo de los pagos, así
que ese requisito no se puede cumplir sin alcance nuevo: que un comprobante
retenido abra caso. Del lado de ventas sí cierra, y está construido.

### 3. RF-01 estaba construido y no podía dispararse

Apareció recién al escribir los tests, y es el más incómodo de los tres porque
todo lo que se ve desde arriba estaba bien: el evento en el catálogo, la
publicación en `ingestion`, la suscripción en `triage`, el `kind`, el área. Lo
que faltaba estaba **debajo** de la feature: `parse_supplier_ledger` descartaba
el motivo del saldo ilegible con un `balance, _`, así que ninguna fila del padrón
llegaba nunca a cuarentena y el evento no tenía cómo existir.

Ni la spec, ni el plan, ni las tareas podían verlo: los tres hablan de «cuando el
sistema aparte una fila del padrón», y nadie preguntó si el sistema **puede**
apartar una fila del padrón. Lo encontró la primera medición contra los
fixtures —cero filas en cuarentena en cuatro de las cinco pantallas— y no una
lectura de los documentos.

### Lo que habría que agregarle al procedimiento

El paso 4 de `analyze` («coherencia con el proyecto») alcanza para saber si el
plan describe un código que existe. No alcanza para saber si el plan describe un
código que **anda**. Dos preguntas lo habrían cazado, y las dos son baratas:

- Cuando el plan mueve una autorización, ¿el área nueva se la da a la misma
  persona que **el brief**, y a la misma que la matriz? Preguntar sólo por la
  matriz encuentra el síntoma y deja la causa en pie: la matriz también podría
  estar mal, y sin el brief no hay con qué decidir cuál de las dos. (Defecto 1.)
- Cuando el plan conecta dos módulos por una clave, ¿los dos módulos **tienen**
  esa clave, y hablan de la misma entidad? (Defecto 2.)
- Cuando un requisito empieza con «cuando el sistema aparte…», ¿el sistema puede
  apartar eso hoy? Se contesta midiendo y no leyendo: correr el pipeline contra
  los fixtures y contar lo que queda en cuarentena, antes de escribir la primera
  línea. (Defecto 3, y de paso hubiera mostrado que cuatro de las cinco páginas
  fijadas no tenían con qué probar nada.)
