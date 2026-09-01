# Quién mantiene los rubros — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada. Si una tarea no tiene skill, o no
  corresponde al proyecto, o falta la skill: preguntá antes de inventarla.
-->

**Feature:** 010-category-ownership · **Plan:** `plan.md` · **Tareas:** 16

## Estado

**Este documento se escribió antes de la implementación**, el 2026-08-31, y es el primero de la serie
que sale en orden: spec firmada → plan → tareas → código. **Las doce primeras quedaron hechas el mismo
día**, y la suite pasó a 1485 tests con 91,00 % de cobertura.

> **Cuatro tareas se agregaron el 2026-09-01, y no son alcance nuevo.** Un `/analyze` sobre esta
> feature encontró que la tabla de cobertura prometía más de lo que había: cinco requisitos —RF-04,
> RF-05, RF-06, RF-09 y RF-13— no tenían el test que esta tabla les asignaba, y RF-14, que es **lo
> único que la feature construyó de cero**, era el menos verificado de los catorce. Las tareas 13 a
> 16 son esos tests, y están abajo con lo que faltaba en cada uno. La corrección no toca ni una línea
> de código de producción: lo que estaba mal era el documento y lo que faltaba era la prueba. Doce
> tests nuevos —cinco de backend y siete de pantalla— dejan la suite en **1657 tests con 93,12 % de
> cobertura**, y ninguno de los que ya estaban cambió.

> **La fila de la matriz no rompió nada, y eso también es un resultado.** Era el cambio con el radio
> de acción más grande del changeset —nueve rutas y tres pantallas cambian de dueño con una línea— y
> la suite entera quedó verde a la primera. Es lo que se compra teniendo una sola fuente de verdad
> sobre quién llega a dónde.

> **La decisión del humano quedó verificada, no sólo implementada.** `test_purchasing_sees_its_own_rubro_change_in_the_history`
> falla si alguien devuelve el `CATEGORY_SECTION` a `SALES`, que es exactamente el refactor «de
> limpieza» que este cambio invita a hacer dentro de seis meses.

No hay migración, no hay tabla nueva, no hay evento nuevo y no hay ruta nueva. Es la señal de que la
spec dice la verdad cuando dice que corrige el acuerdo y no agrega funcionalidad: **casi todo sale de
una fila de la matriz de permisos**, y lo único que se construye de cero es media pantalla.

> **Una sola tarea construye algo que no sale de ningún RF de esta spec: la 5.** Es el `CATEGORY_SECTION`, aprobado por el
> humano el 2026-08-31 para que mover los rubros a compras no rompa RF-19 de la **003**, que también
> está firmada. Está registrada en `plan.md` → *Lo que esta feature destapa, y qué decidió el humano*.

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una: backend → frontend →
tests. No hay migración en esta feature.

> **Al terminar H1 hay algo entregable de verdad**: Marcela entra con su acceso, encuentra «Rubros»
> entre lo que le toca, agrega uno, le asigna un rubro a un producto que no tenía, y resuelve una
> forma escrita nueva desde la misma pantalla donde ya resuelve lo que la actualización aparta.

> **La tarea 1 es la que mueve casi todo, y hay que correr los tests inmediatamente después.** Es el
> cambio más chico del repositorio con el radio de acción más grande: el menú, los botones de tres
> pantallas y nueve rutas cambian de dueño con una línea.

### H1 — Compras mantiene los rubros

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 1 | **La fila de `MATRIX`**: `Section.PRODUCT_CATEGORIES` pasa a `{OWNER: WRITE, PURCHASING: WRITE, SALES: READ}` (`identity/permissions.py:86`), y el comentario-guía de `:56-73` deja de atribuirle los rubros a ventas — nombra los RF de la 002 que justifican cada fila y hoy miente sobre ésta. Actualizar en el mismo commit la fila duplicada de `tests/unit/identity/test_permissions.py:34`: ese test existe para obligar a editarla a propósito, **no lo generes desde `MATRIX`**. | `add_backend_feature` | Developer | RF-01, RF-02, RF-03, RF-04, RF-05, RF-09, RF-10, RF-11, RF-12 |
| ✅ 2 | Los docstrings de las cinco rutas de escritura de `catalog` dicen «el dueño y compras» donde decían «el dueño y ventas», y el comentario del bloque `# --- The rubros of the catalog (008) ---` (`routes.py:145-150`) deja de afirmar que escribir es de ventas. **Las `dependencies=[require_section(...)]` no se tocan**: ya piden `WRITE`, y quién lo tiene lo decide la matriz. | `add_backend_feature` | Developer | RF-01, RF-02, RF-03, RF-04, RF-05, RF-11 |
| ✅ 3 | **La rama `unknown_category` de `CaseCard.tsx`**, que es lo único que se construye de cero. Mostrar `payload["category_text"]`, un selector con los rubros, y resolver con `POST /triage/cases/{id}/resolution` → `{"category_id": N}` y `remember: true`, que es lo que convierte la decisión en equivalencia. **Los rubros los pasa la página como prop** —`/revision/page.tsx` pide `GET /categories`—: el componente no fetchea, igual que `AliasList` recibe `categories`. | `add_frontend_feature` | Developer | RF-06, RF-14 |
| ✅ 4 | La etiqueta de `unknown_category` en `CASE_KINDS` (`frontend/lib/triage/types.ts:15-21`). Sin ella el caso se dibuja con su `kind` crudo **en inglés**, en una pantalla que lee una persona (Artículo VIII). | `add_frontend_feature` | Developer | RF-14 |
| ✅ 5 | **`CATEGORY_SECTION = BusinessSection.PURCHASING`**, usado **sólo** por `_record_category_change` (`catalog/service.py:978-999`); los precios y los productos siguen en `CATALOG_SECTION = SALES`. Y el docstring de `shared/sections.py`, que hoy dice *«what part of the business a fact belongs to»* y pasa a admitir dos lecturas: **la corrección de ese docstring es parte de la tarea**, no un detalle. Sin esto, Marcela no ve en `/historial` los cambios que ella misma hace y RF-19 de la 003 deja de ser verdad. | `add_backend_feature` | Developer | — *(decisión del humano, ver `plan.md`)* |
| ✅ 6 | Los textos de las tres pantallas de rubros donde hablen de quién mantiene qué. Ninguna lógica: `canEdit` y el menú ya leen la matriz y no hay que tocarlos. | `add_frontend_feature` | Developer | RF-09, RF-12 |
| ✅ 7 | Tests de H1: que compras alcance las cuatro escrituras de `catalog` con `200`/`201`, que el menú de compras traiga `PRODUCT_CATEGORIES`, y **el circuito completo de una forma escrita nueva desde la pantalla** — llega una categoría desconocida, aparece el caso en `/revision`, Marcela le asigna un rubro, la equivalencia queda guardada y los productos que la esperaban quedan clasificados. Hoy los tests de la 008 llaman al **servicio** y saltean ese tramo: RF-24 y RF-25 de aquella spec están verdes por la razón equivocada. | `add_tests` | Tester | RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-09, RF-13, RF-14 |
| ✅ 8 | Test de RF-13: que la propuesta de rubro de un producto sin clasificar le llegue a compras, y que confirmarla y corregirla sean la misma llamada. | `add_tests` | Tester | RF-13 |
| ✅ 9 | Test de la tarea 5: que un cambio de rubro hecho por compras **aparezca en el historial de compras**, y que una corrección de precio siga apareciendo en el de ventas. Es lo que impide que el `CATEGORY_SECTION` se «limpie» en seis meses. | `add_tests` | Tester | — *(decisión del humano)* |

### H2 — Ventas los sigue viendo, sin poder cambiarlos

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 10 | Las tres rutas de lectura de `/categories` —`""`, `/unclassified`, `/aliases`— pasan de `Depends(get_current_user)` a `require_section(Section.PRODUCT_CATEGORIES, Level.READ)` (`catalog/routes.py:157, 169, 180`). Con la matriz nueva los tres roles tienen `READ` o más: **no cambia el comportamiento de nadie** y convierte RF-10 en una declaración verificable en vez de un permiso por omisión (`PY-09`). | `add_backend_feature` | Developer | RF-10 |
| ✅ 11 | **Tests de RF-11 y RF-12 por comportamiento.** Hoy no existe **ni un test** que haga una request real como ventas contra `/categories` y espere `403`: uno por cada una de las cuatro escrituras de `catalog`, más `PUT /products/{id}/category`. Y el que se rompe sin ruido: que las **tres lecturas sigan devolviendo `200` para los tres roles** (RF-10) — al declarar `require_section` es fácil poner `WRITE` por simetría con las escrituras y cerrarle la pantalla a ventas sin que nada se ponga rojo. | `add_tests` | Tester | RF-10, RF-11, RF-12 |
| ✅ 12 | Test de que **`PRODUCT_CATALOG` no se movió**: sigue `{SALES: WRITE, PURCHASING: NONE}`. El catálogo **no** es parte de esta spec, y «acompañar» el cambio moviendo también esa fila rompe el alcance sin que ningún test lo note. Es la verificación de que rubros y catálogo dejaron de viajar juntos, que es la consecuencia deliberada que la spec declara. | `add_tests` | Tester | — *(guarda de alcance, no un RF)* |

### Lo que faltaba probar, cerrado el 2026-09-01

Cuatro tareas de test que las 1 a 12 dieron por hechas y no estaban. Ninguna cambia el código de
producción: si alguna hubiera necesitado tocarlo, el hallazgo no habría sido de cobertura sino de
implementación.

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 13 | **La cuarta escritura de `catalog`, que era la que faltaba.** La tarea 7 prometía las cuatro con `200`/`201` y probó tres: nadie verificaba que compras pueda **clasificar** un producto, que es la mitad de H1 y la decisión más discutida de la firma —los productos sin rubro se movieron con los rubros—. Dos tests: darle un rubro a uno que no tenía, y moverle el rubro a uno ya clasificado. | `add_tests` | Tester | RF-04, RF-05 |
| ✅ 14 | **El circuito de una forma escrita nueva, por la cola y no por el servicio.** Es el punto 3 del *Contexto de traspaso → Para el Tester*, que quedó abierto: llega la lista con una forma que nadie decidió → el caso aparece en la cola de compras → Marcela le asigna un rubro desde ahí → la equivalencia queda guardada → los dos productos que la esperaban quedan clasificados. Los tests de la 008 llaman al `TriageService` y saltean exactamente ese tramo. | `add_tests` | Tester | RF-06, RF-14 |
| ✅ 15 | **Los tests de pantalla**, que son los que el backend no puede escribir: que «Rubros» le aparezca a compras y **le siga apareciendo a ventas con `READ`** (RF-09, RF-10 — si la entrada del menú exigiera edición, Julián tendría el permiso y ninguna puerta), que con nivel de lectura la pantalla no ofrezca ninguna acción y con el de compras las ofrezca todas (RF-12), y que la rama `unknown_category` de la tarjeta muestre la forma escrita, la nombre en castellano y resuelva con `{ category_id }` (RF-14, RF-06). Precedente: los dos tests de pantalla de la 006. | `add_tests` | Tester | RF-09, RF-10, RF-12, RF-14 |
| ✅ 16 | **La propuesta, del lado de compras.** La tarea 8 no se había escrito: que la cola de sin clasificar le llegue a Marcela **con la propuesta puesta**, y que confirmarla y corregirla sean la misma llamada — que es el criterio de aceptación de RF-13, palabra por palabra. Lo que la 008 prueba es de dónde sale una propuesta, no que le llegue a quien ahora decide. | `add_tests` | Tester | RF-13 |

## Cobertura de requisitos

Cada test nombrado acá se puede abrir y leer. La versión anterior de esta tabla mandaba cinco
requisitos a tests que no los cubrían, y por eso ahora la columna dice **cuál** es el test y no sólo
qué tarea debía escribirlo.

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 1, 2 | 7 — `test_purchasing_can_add_a_rubro` |
| RF-02 | 1, 2 | 7 — `test_purchasing_can_rename_one` |
| RF-03 | 1, 2 | 7 — `test_purchasing_can_delete_an_empty_one` |
| RF-04 | 1, 2 | 13 — `test_purchasing_gives_a_rubro_to_a_product_that_had_none` |
| RF-05 | 1, 2 | 13 — `test_purchasing_moves_one_that_was_already_classified` |
| RF-06 | 3 | 14 — `test_purchasing_closes_it_from_the_review_queue` · 15 — la tarjeta resuelve con `{ category_id }` |
| RF-07 | — *(ya construido en la 008)* | de la 008 — `test_it_reassigns_without_going_through_review` |
| RF-08 | — *(ya construido en la 008)* | de la 008 — `test_the_products_go_back_to_review` |
| RF-09 | 1, 6 | 7 — `test_purchasing_reaches_the_rubros_among_its_sections` · 15 — «Rubros» en la barra de compras |
| RF-10 | 1, 10 | 11 — `test_sales_still_reads_them` · 15 — «Rubros» en la barra de ventas |
| RF-11 | 1, 2 | 11 — los cuatro `test_sales_cannot_*` |
| RF-12 | 1, 6 | 11 · 15 — con nivel de lectura la pantalla no ofrece ninguna acción |
| RF-13 | — *(ya construido en la 008)* | 16 — `test_the_proposal_reaches_purchasing` y `test_confirming_and_correcting_are_the_same_call` |
| RF-14 | 3, 4 | 14 · 15 — la rama `unknown_category` de la tarjeta |

**Tres requisitos no tienen tarea de construcción, y es correcto.** RF-07 (cambiar el rubro al que
apunta una equivalencia), RF-08 (dejarla sin efecto) y RF-13 (la propuesta) **ya están construidos en
la 008**, y sus rutas ya piden `Section.PRICES` en escritura — que es dueño y compras—. La 010 no los
mueve: hace que el resto coincida con lo que ahí ya pasaba. Lo único que les faltaba a RF-07 y RF-08
era que ventas dejara de ver botones que el backend le rechazaba, y eso lo cierra la tarea 1.

**RF-13 es la excepción de esa lista, y por eso sí tiene test propio.** Está construido en la 008,
pero lo que la 010 le cambia es **el destinatario**: la propuesta que allá se le presentaba a ventas
acá se le presenta a compras. Un test de la 008 sobre el servicio no puede decir nada de eso.

**Los catorce requisitos tienen test, desde el 2026-09-01.** Cinco no lo tenían: la tabla anterior se
los atribuía a tareas que no los cubrían y nadie lo había verificado. Ninguno de los catorce tenía
test **por comportamiento** antes de esta feature.

**Las tareas 5 y 9 no aparecen en esta tabla, y es correcto.** Son el `CATEGORY_SECTION` y su test: no salen de ningún RF de la 010, sino de la decisión que el humano tomó el 2026-08-31 para que esta feature no rompa **RF-19 de la 003**. Están registradas en `plan.md` → *Lo que esta feature destapa, y qué decidió el humano*. Es lo único del changeset que **construye** sin requisito propio: cualquier otra cosa que aparezca así es alcance que nadie aprobó.

**La tarea 12 tampoco aparece, y por otra razón.** No construye nada ni prueba un requisito: prueba
que una fila que esta spec **no** toca siga como está. Sale de *Fuera de alcance* —«el catálogo y las
correcciones de producto siguen siendo de ventas»—, que es parte de lo firmado aunque no sea un RF.
Antes figuraba bajo RF-12 y no era cierto: RF-12 es que a ventas no se le ofrezca ninguna acción
sobre los rubros, y esa fila habla del catálogo.

## Notas para `/converge`

- **Nueve requisitos de la 008 quedan enmendados** —RF-05, RF-06, RF-07, RF-13, RF-15, RF-20, RF-24,
  RF-28 y RF-30 de aquella spec—, y la tabla de correspondencia está en `spec.md`. Un converge que lea
  la 008 sola va a encontrar contradicciones que **no son deriva**: donde las dos specs difieren, gana
  ésta, que es posterior.
- **Los hallazgos 1, 2, 3 y 4 de la *Deriva* de la 008 dejan de ser deriva** el día que esta feature
  esté construida: eran el síntoma de esta spec faltando. Los del 5 al 11 siguen siendo de la 008 y
  esta feature no los toca.
- **La tarea 5 es la única cosa del changeset que no sale de un RF de esta spec.** La aprobó el humano
  el 2026-08-31 y está registrada en el plan. Si aparece cualquier otra cosa sin RF —una tabla, una
  migración, una ruta— se amplió el alcance sin permiso.
- **Un `alembic/versions/0014_*.py` en este changeset es una señal de alarma.** Esta feature no crea
  ninguna tabla y no escribe ninguna migración.
- **Una tarea marcada ✅ no es un test que exista.** Es lo que dejó el `/analyze` del 2026-09-01: las
  tareas 7, 8 y 11 estaban cerradas y entre las tres prometían cinco tests que nadie había escrito.
  Se descubrió leyendo la suite, no leyendo este documento — que es la única forma de descubrirlo—.
  Un `/converge` sobre esta feature abre los tests que la tabla de cobertura nombra; ahora los
  nombra uno por uno justamente para que eso se pueda hacer.
