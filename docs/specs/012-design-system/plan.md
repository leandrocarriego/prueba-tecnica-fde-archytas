# Sistema de diseño — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 012-design-system · **Spec aprobada el:** 2026-08-31 · **Fecha:** 2026-08-31

**Rol:** `Frontend-Architect`. El `Backend-Architect` no tiene nada que decidir acá y lo dice
explícitamente: **esta feature no toca el backend** — ni un endpoint, ni un evento, ni una
migración (ver *Módulos afectados*).

**Relevamiento previo:** [`research.md`](./research.md) — qué está construido, qué falta y en qué
archivo está cada cosa. Este plan lo da por leído.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | ✅ | La feature no toca la extracción ni el portal. Ningún archivo de `backend/app/modules/ingestion/` entra en el alcance. |
| II — Nada se descarta | ✅ **y lo refuerza** | `RF-14`, `RF-15`, `RF-16` y `RF-23` son este artículo hecho pantalla: el aviso va **arriba** del número, con la acción que lo resuelve, y el "cero excluidos" del tablero se dice con todas las letras en vez de callarse. Se cambia dónde se muestra lo excluido, nunca qué se excluye. |
| III — Flujo unidireccional, `raw` inmutable | ✅ | No se toca ninguna capa de datos. Cero migraciones. |
| IV — Las fronteras entre módulos son reales | ✅ | Cero cambios en `backend/app/modules/`. En el frontend la pieza compartida nueva (`lib/ui/tone.ts`) importa **sólo** los tipos generados de `lib/api/types.ts`, no de `lib/purchases/`, `lib/sales/` ni ningún otro vecino: la misma disciplina, del lado que no tiene test que la verifique. |
| V — Spec primero, y con firma | ✅ | `spec.md` en **Aprobado**, firmada por Leandro Carriego (FDE) el 2026-08-31. Este plan no agrega ni un requisito que la spec no pida. |
| VI — Lo que no está tipado y testeado no está terminado | ✅ | El grueso del plan **es** el enforcement: **cinco** chequeos estáticos nuevos que rompen el build, más **cuatro** tests de render sobre lo que puede fallar en silencio. Ningún test existente se debilita. |
| VII — Las credenciales de terceros viven sólo en el entorno | ✅ | No se tocan credenciales. Las pantallas de sesión cambian de aspecto, no de mecanismo. |
| VIII — Un idioma para cada audiencia | ✅ | Documentación y artefactos en español; código y nombres de token en inglés (`--warn-surface`, `tone`, `Amount`); los textos que ve el usuario, en español. |
| IX — Las dependencias entran por la puerta | ✅ | **Ninguna dependencia nueva.** `vitest`, `@testing-library/*` y `jsdom` entraron a `main` con su `package-lock.json` en el PR #29, junto al código que las usa. Nada por agregar acá. |

**Excepciones solicitadas:** ninguna.

## Enfoque

**El punto de partida no es cero, y no es lo que parece.** La base del sistema de diseño ya está
construida —tokens en `globals.css`, `Badge`, `Notice`, `Button` con `variant="brand"`, el test
que verifica `UI-01` y `UI-02`, las diez convenciones escritas, la guía en `docs/design/`— pero
entró entera a `main` con el PR #29 —y con ella `vitest.config.ts`, la suite del frontend y el
bloque `UI-01`…`UI-10` de `CONVENTIONS.md`—. Lo que sigue siendo cierto, y es lo que importa:
**casi no la usa nadie**. Un solo archivo de los setenta y cinco usa `<Badge>` y `<Notice>`
—`components/purchases/CalendarGrid.tsx`, que los estrenó la 006— y el único `variant="brand"` del
repositorio vive en `components/ui/confirm-dialog.tsx`. Lo que falta, entonces, no es construir el
sistema: es **adoptarlo**. Esta feature es una migración, no una construcción.

**Una migración de este tamaño no se sostiene con disciplina.** Son ~9.400 líneas de UI repartidas
en setenta y cinco archivos, y la mitad de los requisitos —"la misma píldora en las tres
pantallas", "un solo naranja por pantalla", "los importes en columna"— son exactamente el tipo de
regla que se cumple el día que se escribe y se rompe en el tercer PR siguiente. Por eso el plan
invierte primero en **convertir cada regla repetida en una sola decisión tomada en un solo
archivo**, y recién después migra:

- **El estado de un dato → un tono, decidido una vez.** `frontend/lib/ui/tone.ts` mapea cada enum
  de dominio que llega del backend (estado de factura, de venta, de precio, de caso de revisión,
  de orden, de mensaje) a uno de los cinco tonos de `Badge`. Es la única forma de que `RF-06` sea
  cierto: mientras cada pantalla elija su color, "vencida" se va a dibujar de tres maneras otra
  vez. Cinco tonos y ni uno más, y **ninguno es el naranja de marca** (`RF-07`).
- **La plata → un componente, no una convención.** `money()` devuelve un string, y quien lo
  escribe elige con qué tipografía: esa es la razón estructural de que `RF-09` y `RF-10` no se
  cumplan hoy en catorce archivos. Se agrega `frontend/components/ui/amount.tsx` (`<Money>`,
  `<Day>`, `<Code>`), que envuelve el valor en `.amount` y ya viene alineado a la derecha cuando
  es celda de tabla. El formateo sigue viviendo en `lib/format.ts`: el componente lo usa, no lo
  reemplaza.
- **Las tres caras de una pantalla → tres componentes.** `RF-19` pide que cargando, con error y
  sin resultados se vean igual en todas partes, y hoy no existe ni uno de los tres en todo `app/`.
  Se agregan `components/ui/state.tsx` (`<Loading>`, `<ErrorState>`, `<Empty>`) más un
  `app/(private)/loading.tsx` y un `app/(private)/error.tsx`, que Next.js aplica a todo el árbol
  privado de una sola vez.

**Después, el enforcement.** `frontend/tests/design-system.test.ts` pasa de **tres casos a ocho**,
los cinco nuevos por análisis estático del texto del código —el mismo mecanismo que ya usa,
que no necesita renderizar y por eso alcanza también a las pantallas que ningún test toca:

| Chequeo nuevo | Qué decide | RF |
|---|---|---|
| Presupuesto de naranja | Para cada `app/(private)/**/page.tsx`, se recorre su árbol de imports `@/` y se cuentan los `variant="brand"`: **como mucho uno**. | `RF-11`, `UI-05` |
| Pantallas de decisión | Una lista fija de rutas —`revision`, `calendario`, `facturas/revision`, `facturas/incidentes`, `ventas/revision`, `proveedores/grafias`, `rubros/sin-clasificar`, `rubros/equivalencias`, `acciones`— tiene que dar **cero**. | `RF-21` |
| *(los dos de arriba)* | **No cuentan el naranja de una ventana de confirmación**: `components/ui/confirm-dialog.tsx` queda fuera del recorrido del árbol de imports. Lo pide la spec enmendada el 2026-08-31, y sin esto `/calendario` daría uno en vez de cero por el diálogo que la 006 dejó en `main`. | `RF-11`, `RF-21` |
| La píldora es de `Badge` | Las clases `.pill*` no aparecen fuera de `components/ui/badge.tsx` y `globals.css`. | `RF-06`, `UI-03` |
| La plata pasa por el envoltorio | `money`, `decimal` y `day` se importan de `@/lib/format` **sólo** desde `components/ui/amount.tsx` y desde una lista de excepciones fijada por nombre de archivo —las que necesitan el string, no el elemento: un `title`, un `aria-label`, un asunto de mensaje—. | `RF-09`, `RF-10`, `UI-04` |
| Un solo tema | Cero `dark:` y cero `prefers-color-scheme` fuera del comentario de cabecera de `globals.css`. Hoy ya da cero: el test lo congela. | `RF-20`, `UI-10` |

La lista de excepciones va **por nombre de archivo**, como la del test de fronteras del backend y
como las dos que ya tiene este test: ampliarla exige editar el test a propósito, que es
exactamente el punto.

**Cómo nace verde un test que describe el final, escrito al principio.** Dos de los cinco chequeos
—la píldora y la plata— son falsos hoy, y siguen siéndolo hasta la última ola: `.pill*` está escrito
a mano en dos archivos que se migran en la tarea 37, y catorce archivos importan de `@/lib/format`
hasta la tarea 41. Un test que arranca en rojo no es un gate: es ruido que se aprende a ignorar, y
además dejaría el build roto durante toda la migración, contra el Artículo VI.

Por eso los dos nacen con su **lista de excepciones sembrada con exactamente los archivos que
todavía no se migraron**, y **cada tarea de pantalla saca los suyos de esa lista en el mismo
commit en que migra la pantalla**. La lista es el mapa de lo que falta: empieza con dieciséis
entradas y tiene que llegar a cero —salvo las que el propio chequeo admite para siempre, las que
necesitan el string y no el elemento—. El día que la ola 4 cierra, la lista queda vacía y el
chequeo pasa a ser lo que dice ser.

Los otros tres nacen verdes de verdad y no necesitan siembra: el presupuesto de naranja y las rutas
de decisión, con la ventana de confirmación excluida, dan cero hoy; el tema único ya daba cero.

**Ninguna excepción se agrega después.** Sembrar la lista es un acto único de la tarea 6, con el
árbol de hoy a la vista; a partir de ahí sólo se sacan entradas. Una entrada nueva significa que
alguien escribió una pantalla nueva sin las primitivas, y eso es lo que el chequeo existe para
frenar.

**Lo que el análisis estático no puede decidir se prueba renderizando.** Cuatro tests de React
Testing Library en tres archivos, sobre lo único que puede fallar en silencio: que las pantallas de
sesión tomen la identidad visual (`RF-05`); que el menú muestre Ventas y esconda
lo que no corresponde (`RF-17`, `RF-18`, `RF-22`); que en el tablero el aviso salga **antes** que
el importe en el orden del DOM y que el "cero excluidos" aparezca (`RF-14`, `RF-16`); y que fuera
del tablero un total sin exclusiones no dibuje ningún aviso (`RF-23`).

**Y recién entonces, la migración, en cinco olas por valor.** El orden no es alfabético: primero
lo que se ve en todas las pantallas, después la plata, después las decisiones.

| Ola | Qué | Por qué va acá |
|---|---|---|
| 0 · Cimientos | `lib/ui/tone.ts`, `components/ui/amount.tsx`, `components/ui/state.tsx`, `loading.tsx`/`error.tsx`, tokens `--muted-ink` y `--draft-border` para los dos hex sueltos de `globals.css` (`UI-09`), y los cinco chequeos nuevos del test | Nada de lo que sigue se puede hacer bien sin esto, y el test tiene que existir antes de la migración para que la migración lo obedezca |
| 1 · Shell y sesión | `app/(private)/layout.tsx`, `Navigation.tsx` (+ Ventas), `app/(private)/page.tsx`, las cuatro pantallas de sesión, `AuthLayout`, `LoginForm`, `ResetPasswordForm`, `NoPermission` | Es lo que se ve en **todas** las pantallas y en el primer segundo de la sesión: `RF-01` a `RF-05`, `RF-22` |
| 2 · La plata | `facturas/*`, `ordenes`, `proveedores/*`, `calendario` y sus componentes (`InvoiceTable`, `InvoicePanel`, `OrderTable`, `HeldVouchers`, `CalendarGrid`, `SalesReview`) | Es donde `RF-09` y `RF-10` valen plata de verdad, y donde vive la píldora "vencida" que `RF-06` pide idéntica en tres lugares |
| 3 · Las decisiones | `revision`, `ventas/revision`, `facturas/revision`, `facturas/incidentes`, `proveedores/grafias`, `rubros/*`, `acciones`, y `CaseCard`, `ReviewQueue`, `UnclassifiedQueue`, `SpellingList`, `SaleCorrection`, `CorrectionDialog` | `RF-21` y `RF-12`: son las pantallas donde el naranja tiene prohibido aparecer, y las que más botones tienen |
| 4 · El resto | `tablero`, `precios/*`, `historial`, `mensajes`, `accesos/*`, `configuracion`, `mi-cuenta`, `health` | El tablero va **último a propósito**: `RF-14`/`RF-16` son el requisito más delicado y conviene resolverlo con `<Notice>` ya rodado en el resto |

### Dónde se resuelve cada requisito

Los veintitrés, para que ninguno dependa de que alguien lo recuerde:

| RF | Dónde se resuelve | Quién lo verifica |
|---|---|---|
| `RF-01` | Olas 1 a 4: todas las pantallas adoptan tokens y primitivas | `UI-01`/`UI-02` (test) + recorrido del Tester |
| `RF-02` | Ola 1: el fondo lo pone el shell (`layout.tsx`), ninguna pantalla pone el suyo | Code-Reviewer sobre el `<main>` de cada pantalla |
| `RF-03` | Ya cumplido en `Navigation.tsx`; la ola 1 sólo le agrega Ventas | Test de render del menú |
| `RF-04` | Ya cumplido en `Navigation.tsx` | Test de render del menú |
| `RF-05` | Ola 1: las cuatro pantallas de sesión + `AuthLayout` + `branding.ts` | Test de render de `AuthLayout` + recorrido |
| `RF-06` | Ola 0 (`lib/ui/tone.ts`) y olas 2 a 4 | Chequeo "la píldora es de `Badge`" + recorrido en tres pantallas |
| `RF-07` | Ola 0: cinco tonos en `tone.ts`, y `Badge` no tiene tono naranja | El tipo de `tone` lo hace imposible de violar |
| `RF-08` | Ola 2: `pill-draft` sobre lo no confirmado, previa verificación del dato | Recorrido del Tester |
| `RF-09` | Ola 0 (`<Money>`, `<Day>`, `<Code>`) y olas 2 a 4 | Chequeo "la plata pasa por el envoltorio" |
| `RF-10` | Ola 0: el envoltorio ya alinea a la derecha en celda de tabla | Ídem + recorrido con cifras de distinto largo |
| `RF-11` | Olas 1 a 4: un `variant="brand"` por pantalla; el de una ventana de confirmación no cuenta | Chequeo "presupuesto de naranja", con los diálogos excluidos |
| `RF-12` | Olas 1 a 4: toda acción secundaria a `default`, `outline`, `ghost` o `link` | Presupuesto de naranja + `UI-05` en el review |
| `RF-13` | Olas 2 a 4: `variant="link"` sólo navega o consulta; lo que guarda, corrige o borra va en tinta o contorno | `UI-06`, **Code-Reviewer**: no es decidible estáticamente, y está dicho en su traspaso |
| `RF-14` | Ola 4 (tablero): `<Notice>` por encima del importe | Test de render: orden del DOM |
| `RF-15` | Ola 0: `<Notice>` tiene `action` en su firma; olas 2 a 4 la completan | `UI-07` en el review |
| `RF-16` | Ola 4 (tablero): "no se excluyó ningún registro" explícito | Test de render con cero exclusiones |
| `RF-17` | Ya cumplido en `Navigation.tsx` (`canSee`) | Test de render con permisos de Ventas |
| `RF-18` | Ya cumplido en `Navigation.tsx` (grupo vacío filtrado) | Ídem |
| `RF-19` | Ola 0: `<Loading>`, `<ErrorState>`, `<Empty>` + `loading.tsx`/`error.tsx` del árbol privado | Recorrido del Tester |
| `RF-20` | Ya cumplido: cero `dark:`, cero `prefers-color-scheme` | Chequeo "un solo tema" lo congela |
| `RF-21` | Ola 3, salvo `calendario` que va en la ola 2 (tarea 20) | Chequeo "pantallas de decisión": cero naranjas en nueve rutas, sin contar el de la ventana de confirmación |
| `RF-22` | Ola 1: grupo Ventas + `/ventas` redirect | Test de render del menú (dieciséis entradas con acceso de dueño) |
| `RF-23` | Olas 2 a 4: fuera del tablero, cero exclusiones no dibujan nada | Test de render + `UI-07` en el review |
| `RF-24` | Ola 1 (tarea 8): la raíz privada redirige al tablero | Recorrido de cierre de la ola 1 (tarea 13) |

**Cómo se desglosa esto en tareas** (decidido el 2026-08-31, para que `/tasks` no lo vuelva a
abrir): **una tarea por pantalla**, no una pasada por historia. La skill de `tasks` agrupa por
historia de usuario, y acá cada pantalla toca H1, H2, H3 y H4 a la vez: se agrupan bajo la historia
que más pesa y cada tarea declara todos los `RF` que cubre. La razón es que **una pantalla migrada
a medias no es entregable** —queda con la mitad de los estados en píldora y la otra mitad no—,
mientras que una pasada por historia toca los mismos setenta y cinco archivos cinco veces y no deja
nada terminado hasta el final.

**Dos aclaraciones de alcance**, porque son las dos tentaciones de una migración así:

1. **No se reorganiza el contenido de ninguna pantalla.** La spec lo pone fuera de alcance con
   todas las letras. Cambia con qué se dibuja cada cosa; no qué información hay ni en qué orden
   —con la única excepción que la spec *sí* pide: el aviso sube por encima del número (`RF-14`).
2. **`app/(private)/page.tsx` es el único archivo que se reemplaza en vez de migrarse.** Es una
   pantalla de andamio ("Bienvenido, {email}", dos enlaces subrayados) que no es ninguna de las
   dieciséis secciones y que hoy es lo primero que ve alguien que entra. Pasa a redirigir a
   `/tablero`. No es contenido nuevo: es sacar del medio una pantalla que nunca fue del producto.

### La entrada de Ventas (`RF-22`)

Es la única decisión de este plan que no es puramente de presentación, así que va explícita.

`Navigation.tsx` lista **quince** entradas y la spec habla de dieciséis secciones. La que falta es
Ventas. Y la ruta `/ventas` **no existe**: lo único que existe es `/ventas/revision`.

**Decisión:** se agrega al menú un grupo propio `Ventas` con una entrada
`{ href: '/ventas', label: 'Ventas', section: 'SALES' }`, y `app/(private)/ventas/page.tsx` es un
**redirect** a `/ventas/revision`. Grupo propio porque `RF-03` pide agrupar por área del negocio y
el backend ya modela `SALES` como una de las tres (`BusinessSection: PURCHASING | SALES | SYSTEM`);
redirect porque mantiene el `href` del menú estable, hace que el resaltado de "sección actual"
funcione para `/ventas/revision` por prefijo, y **no inventa una pantalla**.

Se descartó construir un listado de Ventas nuevo: sería una capacidad, no presentación, y la spec
pone las capacidades nuevas fuera de alcance. Si el cliente quiere una pantalla de Ventas propia,
es su spec.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| **backend (todos)** | **Nada.** Ni un archivo. | — |
| `frontend/app/(private)/` | Las veintiocho pantallas adoptan las primitivas. `page.tsx` pasa a redirect; se agregan `loading.tsx`, `error.tsx` y `ventas/page.tsx` | 3 archivos |
| `frontend/app/(auth)/` | Las cuatro pantallas de sesión toman la identidad visual (`RF-05`) | — |
| `frontend/components/ui/` | `amount.tsx` (`<Money>`, `<Day>`, `<Code>`) y `state.tsx` (`<Loading>`, `<ErrorState>`, `<Empty>`) | 2 archivos |
| `frontend/components/*` (11 carpetas) | Los 43 componentes de dominio adoptan `Badge`, `Notice`, `Button` y los envoltorios | — |
| `frontend/lib/ui/` | `tone.ts`: el mapa estado de dominio → tono, único | 1 carpeta, 1 archivo |
| `frontend/app/globals.css` | Dos tokens nuevos (`--muted-ink`, `--draft-border`) para los dos hex sueltos (`UI-09`) | — |
| `frontend/tests/` | `design-system.test.ts` pasa de 3 a 8 casos; cuatro tests de render nuevos | 3 archivos |
| `docs/design/README.md` | Al cerrar, *Estado de la aplicación* deja de decir "la adopción es la 012" | — |

Ningún módulo nuevo: no aparece ninguna capacidad del negocio con lenguaje propio. `lib/ui/` no es
un módulo, es la carpeta donde vive una decisión de presentación compartida.

## Eventos de dominio

**Ninguno.**

Y es una afirmación, no una omisión: esta feature no cruza ninguna frontera de módulo porque no
toca el backend. No publica, no consume, no agrega nada al catálogo de `app/shared/events/`.

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| — | — | — | — |

## Datos

**Ninguna tabla nueva, ninguna columna nueva, ninguna migración.** `alembic check` tiene que seguir
limpio después de esta feature; si alguien necesita una migración para cerrarla, algo se salió del
alcance y hay que frenar.

Lo único parecido a un dato que agrega la feature es **presentacional y vive en el frontend**: el
mapa estado de dominio → tono de `lib/ui/tone.ts`. Sus claves son los enums que ya llegan en
`lib/api/types.ts`, generados del OpenAPI del backend.

### Qué cuenta como "sin confirmar" (`RF-08`)

Verificado sobre `lib/api/types.ts`: **la API ya expone la señal, pero no como un campo uniforme**.
No hay ningún `confirmed: boolean`; cada entidad lo dice a su manera. La decisión —tomada el
2026-08-31, y por eso `RF-08` no necesita nada del backend— es **usar la señal que cada entidad ya
trae**, resuelta una sola vez en `lib/ui/tone.ts`:

| Entidad | Qué dice "sin confirmar" | Píldora |
|---|---|---|
| Venta | `is_estimated: true` — el valor lo estimó una persona | `pill-draft` |
| Venta apartada | estado `HELD` (frente a `COUNTED`) | `pill-draft` |
| Factura, precio | `origin` en `MANUAL` (frente a `PORTAL` / `INVOICE`) | `pill-draft` |
| Regla, grafía | `LEARNED` / `OBSERVED` (frente a `SEED`) | `pill-draft` |

Lo demás —lo leído del portal y ya contado— va con su tono de estado normal. Si al migrar aparece
una entidad que no trae ninguna de estas señales, **no se inventa una**: se deja sin punteado y se
anota, porque agregar el campo sería backend y esta feature no lo toca.

## Contratos

**Ningún endpoint nuevo, ninguno modificado, ninguna autorización que cambie.** `PY-09` no aplica
porque no hay ruta de backend en el alcance.

Del lado del frontend, las dos rutas que cambian de forma:

| Ruta | Antes | Después | Autorización |
|---|---|---|---|
| `/` (raíz privada) | Pantalla de andamio | `redirect('/tablero')` | La del layout privado: sesión válida. Sin cambios |
| `/ventas` | No existe (404) | `redirect('/ventas/revision')` | Entrada del menú filtrada por `canSee(SALES)`; la negativa sigue siendo del backend en `/ventas/revision` |

Los permisos **no cambian**: `RF-17` esconde lo que no se puede abrir, y esconder un enlace sigue
siendo una comodidad, nunca la restricción. `lib/auth/permissions.ts` no se toca.

## Alternativas descartadas

- **Dejar `UI-03` a `UI-10` al ojo del `Code-Reviewer`.** Es lo que dicen hoy las convenciones, y
  alcanza para una pantalla nueva. Para una migración de setenta y cinco archivos no: la regla que
  se verifica leyendo se cumple el día que se escribe. El propio `docs/design/README.md` ya lo
  dice —"no con disciplina: con reglas y con un test"—; este plan extiende ese test a las cuatro
  reglas que se pueden decidir estáticamente y deja al reviewer las que no.
- **Una regla de ESLint en vez de un caso de test.** Un plugin propio de ESLint con AST sería más
  preciso que buscar texto. También es un paquete nuevo (Artículo IX), un archivo de configuración
  y una herramienta más que mantener, para ganar precisión sobre un patrón —`variant="brand"`— que
  se escribe de una sola manera. El proyecto ya tiene el patrón "test que rompe el build" andando
  en el backend y en `UI-01`/`UI-02`: se reusa ese, no se estrena otro.
- **Adoptar un design system de terceros (shadcn como paquete, un preset de Tailwind).** Los
  tokens ya viven en `globals.css` a propósito: es un producto de un cliente único que no comparte
  paleta con nadie, y el costo de una dependencia con su ciclo de versiones no compra nada.
- **Rehacer las pantallas desde los mockups de `docs/design/ui-cordillera.html`.** Es lo que el
  material invita a hacer, y es exactamente lo que la spec pone fuera de alcance: los mockups
  muestran capacidades que no existen (el buscador general, la presencia en vivo, los asistentes).
  Se toman de ahí la forma y la señal; no el contenido.
- **Una pantalla de Ventas nueva para `RF-22`.** Ver *La entrada de Ventas*: sería una capacidad y
  necesita su propia spec.
- **Hacer que `money()` devuelva JSX.** Resolvería `RF-09` sin componente nuevo, pero rompe los
  catorce usos donde el valor se necesita como string (un `title`, un asunto de mensaje) y
  convierte una función pura y testeada en una de presentación. El envoltorio deja `lib/format.ts`
  como está.
- **Migrar por carpeta alfabética en vez de por olas.** Deja el shell y las pantallas de sesión
  para el final, que es lo que se ve en todas partes; y deja el tablero —el requisito más
  delicado— para cuando ya no queda margen.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| ~~La base del sistema de diseño está sin commitear~~ **Cerrado el 2026-08-31** | — | El PR #29 llevó a `main` los tokens, las primitivas, `design-system.test.ts`, `vitest.config.ts`, `docs/design/README.md`, el bloque `UI-*` de `CONVENTIONS.md` y las devDependencies con su lock. La 012 arranca sobre un árbol que ya los tiene, y la tarea 1 quedó sin objeto |
| **La 006 dejó en `main` el único `variant="brand"` del repositorio, dentro de `confirm-dialog.tsx`, y llega a `/calendario`** | Medio: leída al pie de la letra, la spec obligaba a despintarlo y a dejar sin acento a toda pantalla cuya acción principal viva en un diálogo | Cerrado por enmienda de la spec del 2026-08-31, firmada: la ventana de confirmación no cuenta (`RF-11`, `RF-21`). El chequeo la excluye, y por eso las dos reglas del naranja nacen verdes |
| Migrar setenta y cinco archivos rompe una pantalla en silencio: la UI no tiene tests de regresión salvo los cuatro que existen | Alto: una tabla que deja de renderizar no la ve nadie hasta producción | Las olas se cierran de a una con `npm run build`, `npm test` y un recorrido manual del `Tester` con Playwright sobre las pantallas de esa ola. Ninguna ola empieza con la anterior a medias |
| El presupuesto de naranja se cuenta sobre el árbol de imports, no sobre el DOM: un componente compartido por dos pantallas puede contar dos veces, o un `variant` calculado en runtime puede escaparse | Medio: falsos positivos que molestan, o un naranja de más que el test no ve | El test reporta archivo y línea de cada naranja que cuenta, así que un falso positivo se lee en un segundo. Y `variant` se escribe literal por convención: si alguien lo calcula, `UI-05` es Major y lo agarra el reviewer |
| ~~`RF-08` asume que la API dice qué está confirmado~~ **Cerrado el 2026-08-31** | — | Verificado sobre el contrato: la señal existe, heterogénea por entidad. El mapa quedó decidido en *Datos → Qué cuenta como "sin confirmar"*, y vive en un solo archivo |
| Las pantallas de sesión aplican el color **en línea** desde `lib/branding.ts`, que es excepción del test | Medio: son las cuatro pantallas donde `UI-01` no protege nada | `RF-05` se verifica a mano y con un test de render sobre `AuthLayout`; `branding.ts` toma sus valores de los tokens y no inventa ninguno |
| La spec habla de "las dieciséis secciones" y hoy el menú tiene quince | Bajo, ya resuelto | Ventas es la dieciseisava. Con ella el menú cierra en dieciséis exactas, y así lo verifica el test de render del menú |
| El `Tester` no puede recorrer dieciséis secciones con un solo acceso | Bajo | Se recorre con dos: uno de dueño (ve todo, `RF-01` a `RF-16`) y uno de Ventas (`RF-17`, `RF-18`, `RF-22`) |

## Contexto de traspaso

**Para el Developer** — Los cimientos ya están en `main` (PR #29): no hay nada que rescatar de
ninguna rama, arrancás por la ola 0 completa —`lib/ui/tone.ts`, `components/ui/amount.tsx`,
`components/ui/state.tsx`, los cinco chequeos nuevos del test— y **recién ahí** tocás una pantalla:
el test tiene que existir antes de la migración para que la migración lo obedezca. Las olas van en
orden y no se solapan.

Lo que más se malinterpreta de la tarea 6: los chequeos de la píldora y de la plata **nacen con una
lista de excepciones sembrada** con los archivos que todavía no migraste, y **cada pantalla que
migrás saca los suyos en el mismo commit**. Si terminás una pantalla y el test sigue verde sin que
hayas tocado la lista, la migraste a medias.

Lo que **no** tocás: el backend, entero. Ningún cálculo, ninguna validación, ningún permiso
(`lib/auth/permissions.ts` se queda como está). Ningún contenido de pantalla: no agregues, no
saques ni reordenes información — la única excepción que la spec pide es que el aviso suba por
encima del número en el tablero (`RF-14`). Si una pantalla te parece mal armada, es otra spec.

Decisiones ya tomadas, que no hace falta rediscutir: los cinco tonos y que ninguno es el naranja;
que el naranja va una vez por pantalla y cero en las pantallas de decisión; que la plata pasa por
`<Money>` y no por `money()` suelto; que Ventas entra como grupo propio con `/ventas` redirigiendo
a `/ventas/revision`; que `app/(private)/page.tsx` se reemplaza por un redirect a `/tablero`.

Si te falta una señal visual, **no la improvises en el componente**: se agrega el token en
`globals.css` con nombre semántico (`UI-09`) y su significado en `docs/design/README.md`, y esa
decisión es del `Frontend-Architect`.

**Para el Tester** — Lo que se rompe de verdad en una migración así es una pantalla que deja de
renderizar, y de eso no avisa nadie: recorrelas con Playwright ola por ola, no al final. Las tres
que más riesgo tienen son `historial` (360 líneas), `CalendarGrid` (536) y `CaseCard` (354).

Los casos borde que importan, en este orden:
1. **`RF-06` en tres lugares a la vez**: una factura vencida en `/facturas`, en `/calendario` y en
   `/proveedores/[id]` tiene que ser la misma píldora roja. Es el requisito más fácil de romper
   sin que se note.
2. **`RF-10` con cifras de distinto largo**: una tabla con un importe de cuatro dígitos y otro de
   siete, y las comas alineadas.
3. **`RF-16` y `RF-23` son opuestos**: en el tablero, cero exclusiones **se dicen**; fuera del
   tablero, cero exclusiones **no muestran nada**. Probá los dos, con datos que den cero.
4. **`RF-17`, `RF-18` y `RF-22` necesitan un acceso de Ventas**, no el de dueño: con el de dueño
   no se esconde nada y los tres pasan por default sin probar nada.
5. **`RF-20`**: poné el sistema operativo en modo oscuro y recorré. La plataforma se sigue viendo
   clara.

No hay HTML fijado en esta feature: no toca ningún parser del portal.

**Para el Code-Reviewer** — Las convenciones en juego son las diez `UI-*`, y esta feature existe
para que se cumplan. Mirá primero `frontend/tests/design-system.test.ts`: si sus ocho casos no
están o alguno se debilitó para pasar el gate, ahí termina la revisión (Artículo VI). Segundo,
`frontend/lib/ui/tone.ts`: si el mapa estado → tono no es único —si alguna pantalla eligió su
propio color— `RF-06` es falso por más que la píldora sea la misma. Tercero, el diff del backend:
tiene que estar **vacío**; cualquier archivo de `backend/` en este changeset es alcance que se
escapó.

Lo que el test **no** puede decidir y te queda a vos: `UI-06` (el color de enlace no ejecuta
acciones — buscá `variant="link"` en botones que guardan o borran), `UI-07` (el aviso va antes del
dato que califica, y lleva su acción), `UI-08` (radios y espaciados de la escala) y que el naranja
de cada pantalla sea de verdad el de la tarea principal y no el primer botón que apareció.
