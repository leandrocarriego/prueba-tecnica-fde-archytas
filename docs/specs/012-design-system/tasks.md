# Sistema de diseño — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada. Si una tarea no tiene skill, o no
  corresponde al proyecto, o falta la skill: preguntá antes de inventarla.
-->

**Feature:** 012-design-system · **Plan:** `plan.md` · **Fecha:** 2026-08-31

## Orden

Esta feature es una **migración**, no una construcción: las primitivas ya existen y no las usa
nadie. Por eso el orden real de ejecución es el de las **cinco olas** del plan, y no el de las
historias: cada pantalla toca H1, H2, H3 y H4 a la vez, y una pantalla migrada a medias no es
entregable.

Las tablas de abajo agrupan por historia, como pide la skill, y **la columna `Ola` dice cuándo se
ejecuta cada tarea**. La numeración es global y sigue la ola: se ejecuta por número, de 1 a 44.

| Ola | Qué | Tareas |
|---|---|---|
| **0 · Cimientos** | Rama, tokens, `tone.ts`, `amount.tsx`, `state.tsx` y los cinco chequeos nuevos del test | 1 – 6 |
| **1 · Shell y sesión** | Layout privado, raíz, menú con Ventas, las cuatro pantallas de sesión | 7 – 13 |
| **2 · La plata** | Facturas, órdenes, proveedores, calendario y sus componentes | 14 – 21 |
| **3 · Las decisiones** | Las nueve rutas donde el naranja tiene prohibido aparecer | 22 – 30 |
| **4 · El resto** | Rubros, historial, precios, mensajes, accesos, configuración, salud y —último— el tablero | 31 – 44 |

**Ninguna ola empieza con la anterior a medias.** Cada una se cierra con `npm run build`,
`npm test` y el recorrido del `Tester` con Playwright sobre sus pantallas: las tareas de recorrido
(13, 21, 30, 43) son ese cierre, no un trámite al final.

**La tarea 6 es un gate.** Los cinco chequeos estáticos tienen que estar verdes **antes** de que se
toque la primera pantalla: el test existe para que la migración lo obedezca, y si llega después
sólo sirve para descubrir lo que ya se hizo mal.

**Qué queda entregable, y cuándo.** Estas seis historias son transversales —H1 se completa recién
con la última pantalla— así que el corte entregable no es una historia, es una ola. Al terminar la
**ola 1** el cliente ya tiene la plataforma entera sobre un solo shell, con la barra lateral de las
dieciséis secciones (Ventas incluida) y las pantallas de ingreso con la identidad visual: H6 queda
cerrada completa y H1 queda cerrada en todo lo que se ve en todas las pantallas.

Dentro de cada tarea el orden del plan es migración → backend → frontend → tests. **Acá no hay
migración ni backend**: esta feature no toca `backend/` ni un archivo, y `alembic check` tiene que
seguir limpio al cerrarla.

**Dos ajustes de detalle sobre las olas del plan**, por la regla de una tarea por pantalla:

- `SalesReview` figura en la ola 2 y `ventas/revision` en la ola 3. Como la pantalla (56 loc) es un
  envoltorio del componente (216 loc), migrar uno sin el otro deja media pantalla: van juntos en la
  **ola 3**, que es la ola de `RF-21`, el requisito que gobierna esa ruta.
- `InvoiceTable` lo comparten `/facturas` y `/proveedores/[supplierId]`. Se migra con `/facturas`
  (tarea 14); la ficha del proveedor (tarea 19) lo adopta ya migrado.

Los componentes que no importa ninguna pantalla directamente —`SupplierCorrection`,
`SaleCorrection`, `JobRunCard`, `useLiveCalendar`— viajan con la tarea de la pantalla que los
alcanza.

---

### H1 — Todas las pantallas hablan el mismo idioma visual

| # | Ola | Tarea | Skill | Rol | Cubre |
|---|-----|-------|-------|-----|-------|
| 1 | 0 | Separar los cimientos del sistema de diseño en la rama `feat/012-design-system` y commitearlos. **Lo que falta commitear es menos de lo que dice el plan**: `globals.css`, `badge.tsx`, `notice.tsx`, `button.tsx`, `card.tsx` e `input.tsx` **ya están en `main`**. Lo que está suelto en `fix/extractions-were-wedged` es `frontend/tests/` (5 archivos), `vitest.config.ts`, `package.json` + `package-lock.json` (vitest, `@testing-library/*`, jsdom — juntos, Artículo IX), `docs/design/README.md` y el bloque `UI-01`…`UI-10` de `CONVENTIONS.md`. Lo que sea de la corrección de extracciones se queda en su rama | `ship_changes` ¹ | Release-Manager | — *(precondición)* |
| 2 | 0 | Los dos hex sueltos de `globals.css` pasan a token con nombre semántico: `--muted-ink` (hoy `#8a8e93` en `.section-label`) y `--draft-border` (hoy `#c6c0b4` en `.pill-draft`), y su significado se escribe en `docs/design/README.md` (`UI-09`) | `add_frontend_feature` | Developer | RF-01, RF-08 |
| 5 | 0 | `components/ui/state.tsx` con `<Loading>`, `<ErrorState>` y `<Empty>`, más `app/(private)/loading.tsx` y `app/(private)/error.tsx`, que Next.js aplica a todo el árbol privado de una sola vez. Hoy no existe ninguno de los tres en todo `app/` | `add_frontend_feature` | Developer | RF-19, RF-15 |
| 7 | 1 | `app/(private)/layout.tsx`: el fondo de aplicación y el ancho los pone el shell, y ninguna pantalla pone el suyo. `components/common/NoPermission.tsx` —que importan trece pantallas— toma la forma de `<ErrorState>` | `add_frontend_feature` | Developer | RF-01, RF-02, RF-19 |
| 8 | 1 | `app/(private)/page.tsx` deja de ser la pantalla de andamio (`text-4xl`, `min-h-screen`, dos enlaces subrayados) y pasa a `redirect('/tablero')`. No es contenido nuevo: es sacar del medio una pantalla que nunca fue del producto | `add_frontend_feature` | Developer | RF-01, RF-02 |
| 10 | 1 | `AuthLayout` y `lib/branding.ts` —la excepción del test, que aplica el color **en línea**— toman sus valores de los tokens y no inventan ninguno; `app/(auth)/login/page.tsx` queda con la identidad visual del resto | `add_frontend_feature` | Developer | RF-05, RF-01, RF-11 |
| 11 | 1 | Las otras tres pantallas de sesión —`invitacion/[token]`, `recuperar/[token]`, `reset-password`— con `LoginForm`, `PasswordForm` y `ResetPasswordForm` (389 loc, la más pesada de las tres). Una sola acción de acento por pantalla: la que entra o la que guarda | `add_frontend_feature` | Developer | RF-05, RF-11, RF-12, RF-19 |
| 13 | 1 | Test de render de `AuthLayout` (`RF-05`) y **recorrido de cierre de la ola 1** con Playwright: el shell, la raíz que redirige, y las cuatro pantallas de sesión, con el sistema operativo en modo oscuro para `RF-20` | `add_tests` | Tester | RF-01, RF-02, RF-05, RF-19, RF-20 |
| 35 | 4 | `precios/configuracion/page.tsx` (18 loc): forma de tarjeta y una sola acción de acento | `add_frontend_feature` | Developer | RF-01, RF-11 |
| 38 | 4 | `configuracion/page.tsx` con `ParameterRow` y `AlertRoutes`: tarjeta, las tres caras de pantalla y una sola acción de acento | `add_frontend_feature` | Developer | RF-01, RF-11, RF-19 |
| 39 | 4 | `mi-cuenta/page.tsx` con `PasswordForm`: tarjeta y una acción de acento —guardar— | `add_frontend_feature` | Developer | RF-01, RF-11 |
| 40 | 4 | `health/page.tsx` con `ApiStatusCard` y `JobRunCard`: sólo forma y las tres caras de pantalla; `ApiStatusCard` ya usa tokens | `add_frontend_feature` | Developer | RF-01, RF-19 |
| 43 | 4 | **Recorrido final completo**, con **dos accesos**: uno de dueño para las dieciséis secciones, Mi cuenta y las de sesión (`RF-01`…`RF-16`), y uno de Ventas para el recorte del menú (`RF-17`, `RF-18`, `RF-22`). Con un solo acceso los tres últimos pasan por default sin probar nada. Las tres pantallas de más riesgo: `historial` (360 loc), `CalendarGrid` (536) y `CaseCard` (354) | `add_tests` | Tester | RF-01…RF-23 |
| 44 | 4 | Cierre documental: *Estado de la aplicación* de `docs/design/README.md` deja de decir que la adopción es la 012, y los tokens nuevos quedan con su significado escrito | `add_or_update_skill` ² | Frontend-Architect | RF-01 |

### H2 — Cada estado se dibuja siempre igual

| # | Ola | Tarea | Skill | Rol | Cubre |
|---|-----|-------|-------|-----|-------|
| 3 | 0 | `frontend/lib/ui/tone.ts`: el mapa **único** de cada enum de dominio que llega del backend —estado de factura, de venta, de precio, de caso, de orden, de mensaje— a uno de los **cinco** tonos de `Badge`, y ninguno es el naranja de marca. Incluye la señal de "sin confirmar" resuelta acá y no en cada pantalla: `is_estimated` en ventas, `HELD` en apartadas, `origin=MANUAL` en facturas y precios, `LEARNED`/`OBSERVED` en reglas y grafías. Importa **sólo** de `lib/api/types.ts`. Si al migrar aparece una entidad sin ninguna de esas señales, **no se inventa**: se deja sin punteado y se anota | `add_frontend_feature` | Developer | RF-06, RF-07, RF-08 |
| 14 | 2 | `facturas/page.tsx` con `InvoiceTable` e `InvoiceFilters`: las ocho menciones de estado pasan a `<Badge>` con el tono de `tone.ts`, los importes por `<Money>` alineados, y las tres caras de pantalla. Es la primera de las tres apariciones de la píldora "vencida" que `RF-06` pide idénticas | `add_frontend_feature` | Developer | RF-06, RF-07, RF-08, RF-09, RF-10, RF-11, RF-12, RF-19 |
| 15 | 2 | `facturas/[invoiceId]/page.tsx` con `InvoicePanel` (214 loc, 5 botones): tres estados a píldora, cuatro importes por `<Money>`, y **una** sola acción de acento entre los cinco botones | `add_frontend_feature` | Developer | RF-06, RF-08, RF-09, RF-10, RF-11, RF-12 |
| 17 | 2 | `ordenes/page.tsx` con `OrderTable`: seis menciones de estado a píldora, importes y fechas en mono alineados | `add_frontend_feature` | Developer | RF-06, RF-09, RF-10, RF-11, RF-12 |
| 19 | 2 | `proveedores/[supplierId]/page.tsx` con `SupplierContact`, `SupplierPeriod` y `SupplierCorrection`, reusando el `InvoiceTable` ya migrado. **Tercera aparición de la píldora vencida** (`RF-06`), y el punteado de lo no confirmado | `add_frontend_feature` | Developer | RF-06, RF-08, RF-09, RF-10, RF-11, RF-12 |
| 31 | 4 | `rubros/page.tsx` con `CategoryList`: forma, píldoras y una sola acción de acento. No es una de las nueve rutas de decisión | `add_frontend_feature` | Developer | RF-06, RF-11, RF-19 |
| 32 | 4 | `historial/page.tsx` (360 loc) con `AuditTable`: estados a píldora, códigos y fechas en mono, y las tres caras de pantalla. Es la pantalla más larga del árbol privado | `add_frontend_feature` | Developer | RF-06, RF-09, RF-11, RF-19 |
| 33 | 4 | `precios/page.tsx` con `PriceTable`, `UpdateNowButton` y `UpdateStatus`: píldora del estado del precio, `origin=MANUAL` punteado, y **un** solo naranja —actualizar ahora— entre los tres botones | `add_frontend_feature` | Developer | RF-06, RF-08, RF-09, RF-11, RF-12 |
| 36 | 4 | `mensajes/page.tsx` con `MessageList`: seis menciones de estado a píldora, y revisar de qué variante es el botón | `add_frontend_feature` | Developer | RF-06, RF-11, RF-12, RF-19 |
| 37 | 4 | `accesos/page.tsx` y `accesos/actividad/page.tsx` con `AccessTable` y `NewAccessForm`. Son **los dos únicos archivos que hoy escriben `.pill*` a mano**: pasan por `<Badge>`, que es lo que el chequeo de la tarea 6 exige | `add_frontend_feature` | Developer | RF-06, RF-11, RF-12, RF-19 |

### H3 — La plata y las fechas se leen en columna

| # | Ola | Tarea | Skill | Rol | Cubre |
|---|-----|-------|-------|-----|-------|
| 4 | 0 | `components/ui/amount.tsx` con `<Money>`, `<Day>` y `<Code>`: envuelven el valor en `.amount` y ya vienen alineados a la derecha cuando son celda de tabla. **El formateo sigue en `lib/format.ts`**: el componente lo usa, no lo reemplaza —hay catorce archivos que necesitan el string y no el elemento— | `add_frontend_feature` | Developer | RF-09, RF-10 |
| 16 | 2 | `facturas/pagos/page.tsx` con `HeldVouchers` (7 llamadas a `money`, 2 tablas): importes por `<Money>`, el estado `HELD` punteado como no confirmado, y ningún aviso si no quedó nada afuera | `add_frontend_feature` | Developer | RF-08, RF-09, RF-10, RF-11, RF-23 |
| 18 | 2 | `proveedores/page.tsx`: dos tablas con importes en columna y las píldoras de estado | `add_frontend_feature` | Developer | RF-06, RF-09, RF-10, RF-19 |
| 20 | 2 | `calendario/page.tsx` con `CalendarGrid` (536 loc, 10 botones, 7 llamadas a `money`): importes y días en mono, la señal del día vencido es la píldora, y **ningún naranja** —es una de las nueve rutas de decisión— | `add_frontend_feature` | Developer | RF-06, RF-09, RF-10, RF-19, RF-21 |
| 21 | 2 | **Recorrido de cierre de la ola 2** con Playwright, en este orden: (1) una factura vencida en `/facturas`, en `/calendario` y en `/proveedores/[id]` es la **misma** píldora roja; (2) una tabla con un importe de cuatro dígitos y otro de siete, comas alineadas; (3) un dato sin confirmar se distingue de uno confirmado sin leer la etiqueta; (4) ningún botón que guarda, corrige o borra usa el color de enlace | `add_tests` | Tester | RF-06, RF-08, RF-09, RF-10, RF-13 |
| 34 | 4 | `precios/[productId]/page.tsx` (256 loc, 2 tablas) con `CorrectionDialog` y `RevertCorrectionButton`: importes de las dos tablas en mono y alineados, y el botón de revertir —que modifica— en tinta o contorno, nunca en color de enlace | `add_frontend_feature` | Developer | RF-09, RF-10, RF-11, RF-12, RF-13 |

### H4 — Una sola acción naranja por pantalla

| # | Ola | Tarea | Skill | Rol | Cubre |
|---|-----|-------|-------|-----|-------|
| 6 | 0 | `frontend/tests/design-system.test.ts` pasa de 3 a 8 casos, todos por análisis estático —el mismo mecanismo que ya usa, que alcanza también a las pantallas que ningún test renderiza—: **(a)** presupuesto de naranja: por cada `app/(private)/**/page.tsx` se recorre su árbol de imports `@/` y se cuentan los `variant="brand"`, como mucho uno; **(b)** las nueve rutas de decisión —`revision`, `calendario`, `facturas/revision`, `facturas/incidentes`, `ventas/revision`, `proveedores/grafias`, `rubros/sin-clasificar`, `rubros/equivalencias`, `acciones`— dan cero; **(c)** `.pill*` no aparece fuera de `badge.tsx` y `globals.css`; **(d)** `money`/`decimal`/`day` se importan de `@/lib/format` sólo desde `amount.tsx` y una lista de excepciones **por nombre de archivo**; **(e)** cero `dark:` y cero `prefers-color-scheme` fuera del comentario de cabecera de `globals.css`. Cada hallazgo reporta archivo y línea, para que un falso positivo se lea en un segundo. **Es el gate de toda la migración: verde antes de la tarea 7** | `add_tests` | Tester | RF-06, RF-09, RF-10, RF-11, RF-20, RF-21 |
| 22 | 3 | `revision/page.tsx` con `CaseCard` (354 loc, 8 botones) y `RuleList`: **cero naranja** —es una lista de decisiones—, cada caso ofrece su acción en tinta o contorno, píldoras de estado del caso, y las tres caras de pantalla | `add_frontend_feature` | Developer | RF-06, RF-09, RF-12, RF-13, RF-19, RF-21 |
| 23 | 3 | `facturas/revision/page.tsx` con `ReviewQueue` (255 loc, 3 botones): cero naranja, importes en mono | `add_frontend_feature` | Developer | RF-09, RF-10, RF-12, RF-21 |
| 24 | 3 | `facturas/incidentes/page.tsx` con `IncidentList`: cero naranja, píldora del incidente, importe en mono | `add_frontend_feature` | Developer | RF-06, RF-09, RF-12, RF-21 |
| 25 | 3 | `ventas/revision/page.tsx` con `SalesReview` (216 loc, 6 llamadas a `money`, 6 tablas) y `SaleCorrection`: cero naranja, importes en columna, y `is_estimated` punteado como no confirmado. Es el destino de la entrada Ventas del menú | `add_frontend_feature` | Developer | RF-06, RF-08, RF-09, RF-10, RF-12, RF-21 |
| 26 | 3 | `proveedores/grafias/page.tsx` con `SpellingList`: cero naranja, y `LEARNED`/`OBSERVED` punteados frente a `SEED` | `add_frontend_feature` | Developer | RF-08, RF-12, RF-21 |
| 27 | 3 | `rubros/sin-clasificar/page.tsx` con `UnclassifiedQueue`: cero naranja y las tres caras de pantalla | `add_frontend_feature` | Developer | RF-12, RF-19, RF-21 |
| 28 | 3 | `rubros/equivalencias/page.tsx` con `AliasList`: cero naranja, y las equivalencias aprendidas punteadas | `add_frontend_feature` | Developer | RF-08, RF-12, RF-21 |
| 29 | 3 | `acciones/page.tsx`: una acción manual por fila, ninguna en naranja, y las tres caras de pantalla | `add_frontend_feature` | Developer | RF-12, RF-19, RF-21 |
| 30 | 3 | **Recorrido de cierre de la ola 3** con Playwright: se cuentan los botones naranjas en las nueve rutas de decisión y el resultado es cero en las nueve; y ningún `variant="link"` ejecuta una acción que guarda, corrige o borra | `add_tests` | Tester | RF-12, RF-13, RF-21 |

### H5 — El aviso va antes que el número

| # | Ola | Tarea | Skill | Rol | Cubre |
|---|-----|-------|-------|-----|-------|
| 41 | 4 | `tablero/page.tsx` (7 llamadas a `money`, 2 tablas) con `PeriodPicker`. Hoy lo excluido va **debajo** del número, en un `<p class="text-sm">`: pasa a `<Notice>` **por encima** del importe, con la acción que lleva a resolverlo, y un indicador sin exclusiones lo dice con todas las letras en vez de callarse. Importes en mono. **Va último a propósito**: es el requisito más delicado y se resuelve con `<Notice>` ya rodado en el resto. Única excepción del alcance: acá sí cambia el orden del contenido, porque la spec lo pide | `add_frontend_feature` | Developer | RF-09, RF-10, RF-11, RF-14, RF-15, RF-16 |
| 42 | 4 | Dos tests de render, sobre lo único que puede fallar en silencio: en el tablero con exclusiones, el aviso está **antes** que el importe en el orden del DOM y con su acción; con cero exclusiones, el "no se excluyó ningún registro" aparece. Y su opuesto: **fuera** del tablero, un total con cero exclusiones no dibuja ningún aviso. `RF-16` y `RF-23` dicen lo contrario a propósito y hay que probar los dos con datos que den cero | `add_tests` | Tester | RF-14, RF-15, RF-16, RF-23 |

### H6 — La barra lateral muestra sólo lo que puedo abrir

| # | Ola | Tarea | Skill | Rol | Cubre |
|---|-----|-------|-------|-----|-------|
| 9 | 1 | `components/auth/Navigation.tsx` lista **quince** entradas y la spec habla de dieciséis: falta Ventas. Se agrega el grupo propio `Ventas` con `{ href: '/ventas', label: 'Ventas', section: 'SALES' }` —grupo propio porque el backend ya modela `SALES` como una de las tres áreas— y `app/(private)/ventas/page.tsx` es un `redirect('/ventas/revision')`: mantiene el `href` estable, hace que el resaltado por prefijo funcione, y **no inventa una pantalla**. `canSee` y el filtrado del grupo vacío ya andan y no se tocan; `lib/auth/permissions.ts` tampoco | `add_frontend_feature` | Developer | RF-03, RF-17, RF-18, RF-22 |
| 12 | 1 | Test de render del menú: con acceso de dueño lista **dieciséis** entradas exactas y Ventas entre ellas; con acceso de Ventas no lista Facturas, Órdenes ni Accesos, y el grupo que queda vacío no muestra su título; el nombre de quien trabaja y la salida se ven sin abrir ningún desplegable | `add_tests` | Tester | RF-03, RF-04, RF-17, RF-18, RF-22 |

---

¹ **`ship_changes` se usa parcial, y a propósito.** Es la única skill de git del proyecto, y de sus
pasos acá aplican el 1, el 2 y el 3 —inspeccionar el árbol, crear `feat/012-design-system`,
commitear con un commit por propósito—; **no** el push ni el PR, que son el cierre de la feature y
los hace `/ship`. No se inventa una skill: si separar trabajo suelto entre dos ramas vuelve a
aparecer, se le agrega el paso a `ship_changes` con `add_or_update_skill`.

² **`add_or_update_skill` para `docs/design/README.md`.** Ese archivo es la fuente del *significado*
de las convenciones `UI-*`, y actualizarlo es exactamente lo que esa skill cubre ("agregar o
actualizar skills/convenciones"). El rol dueño acá es el `Frontend-Architect` y no el
`Backend-Architect` del mapa: el sistema de diseño es suyo, y así lo dice el traspaso del plan.

## Cobertura de requisitos

<!--
  Todo requisito funcional de la spec tiene al menos una tarea que lo construye y
  al menos un test que lo verifica. Un RF sin fila acá es alcance firmado que nadie
  se comprometió a hacer — y es exactamente lo que /converge va a encontrar.
-->

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 — toda la plataforma con la guía visual acordada | 2, 7, 8, 10, 11, y todas las de pantalla (14–41) | 13, 43 · más `UI-01`/`UI-02`, que ya rompen el build |
| RF-02 — un solo fondo de aplicación y una sola tarjeta | 7, 8 | 13, 43 |
| RF-03 — barra lateral fija, agrupada, con la sección actual | 9 *(ya cumplido salvo Ventas)* | 12 |
| RF-04 — nombre de quien trabaja y salida, siempre visibles | — *(ya cumplido en `Navigation.tsx`)* | 12 |
| RF-05 — las pantallas de sesión con la misma identidad | 10, 11 | 13 |
| RF-06 — un estado, una píldora, un color, en todas las pantallas | 3, 14, 15, 17, 18, 19, 20, 24, 25, 31, 32, 33, 36, 37 | 6 *(la píldora sale de `Badge`)*, 21 *(la misma en tres pantallas)* |
| RF-07 — cinco significados de color, y el naranja no es uno | 3 | 6 · el tipo de `tone` lo hace imposible de violar; 43 |
| RF-08 — lo no confirmado se distingue de lo confirmado | 2, 3, 15, 16, 19, 25, 26, 28, 33 | 21, 43 |
| RF-09 — importes, fechas y códigos en mono tabular | 4, 14–20, 22–25, 32, 33, 34, 41 | 6 *(la plata pasa por el envoltorio)*, 21 |
| RF-10 — la columna de importes queda en columna | 4, 14, 16, 17, 18, 19, 20, 23, 25, 34, 41 | 6, 21 *(cuatro dígitos contra siete)* |
| RF-11 — como mucho un naranja por pantalla, y es el de la tarea principal | 10, 11, 14–20, 31–41 | 6 *(presupuesto de naranja)* |
| RF-12 — toda acción secundaria en contorno, gris o enlace | 11, 14–20, 22–29, 33, 34, 36, 37 | 6, 30 |
| RF-13 — el color de enlace no modifica datos | 22, 34 | 21, 30 · **y el `Code-Reviewer` (`UI-06`)**: no es decidible estáticamente, y está dicho en su traspaso |
| RF-14 — el aviso va por encima del total | 41 | 42 *(orden del DOM)* |
| RF-15 — todo aviso lleva su acción | 5 *(`<Notice>` ya tiene `action` en su firma)*, 22, 41 | 42, 43 · `UI-07` en el review |
| RF-16 — un indicador sin exclusiones lo dice | 41 | 42 |
| RF-17 — el menú esconde lo que no se puede abrir | 9 *(ya cumplido: `canSee`)* | 12 |
| RF-18 — un grupo sin entradas visibles no muestra su título | 9 *(ya cumplido)* | 12 |
| RF-19 — cargando, con error y sin resultados, iguales en todas partes | 5, 7, 14, 18, 20, 22, 27, 29, 31, 32, 36, 37, 38, 40 | 13, 43 |
| RF-20 — un solo tema, y es el claro | — *(ya cumplido: cero `dark:`, cero `prefers-color-scheme`)* | 6 *(lo congela)*, 13, 43 *(con el SO en modo oscuro)* |
| RF-21 — cero naranja en las pantallas de decisión | 20, 22, 23, 24, 25, 26, 27, 28, 29 | 6 *(las nueve rutas dan cero)*, 30 |
| RF-22 — Ventas es una entrada más del menú | 9 | 12 |
| RF-23 — fuera del tablero, cero exclusiones no muestran nada | 16, y toda pantalla con total (18, 19, 34, 41) | 42 |
