# Arquitectura — Plataforma Cordillera

## Propósito

Este repositorio es la **plataforma web de Ferretería Industrial Cordillera**: una aplicación
a medida que extrae la información del portal legacy SIGProv, la normaliza y la convierte en
un sistema operativo propio para el negocio.

No es un boilerplate ni una plantilla: es un producto único hecho a medida, para un cliente único.

Propiedades clave:
- **Monolito modular**: una sola aplicación desplegable, dividida en módulos de dominio autocontenidos
- Full-stack: frontend Next.js + backend FastAPI + workers Celery
- Extracción por automatización de navegador (Playwright) contra un portal de **solo lectura**
- Type safety: TypeScript estricto (frontend) y type hints de Python (backend)
- Infraestructura reproducible (Docker, PostgreSQL, RabbitMQ)

## El sistema origen (SIGProv)

La plataforma se alimenta del portal SIGProv, que **no es nuestro y no tiene API**. Dos
restricciones que atraviesan toda la arquitectura:

1. **Solo lectura.** Nunca se escribe contra SIGProv. Toda operación de escritura vive en
   nuestra base de datos.
2. **La extracción es automatización de navegador, no un cliente HTTP.** El portal expone
   endpoints JSON internos: **no se usan**. Se lo maneja como lo que representa, un sistema
   viejo sin integración, y se lee de la pantalla renderizada.

## Gobernanza (Spec-Driven Development)

El desarrollo se dirige por specs, con un gate explícito de aprobación del cliente:

- Principios no-negociables (autoridad): `CONSTITUTION.md`
- Punto de entrada, orden de autoridad, flujo SDD y enforcement de los agentes: `AGENTS.md`
  (lo carga `.claude/CLAUDE.md`, que sólo lo importa)
- Convenciones de código (fuente única, por identificador): `CONVENTIONS.md`
- Skills y procedimientos: `agents/skills/`
- Roles y responsabilidades: `agents/roles/`
- Brief del proyecto: `docs/PROJECT_BRIEF.md`
- Relevamiento técnico preliminar del FDE: `docs/FDE_ASSESSMENT.md` — **no vinculante**: son
  hipótesis previas a la primera spec, y cada una muere cuando la feature que la toca tiene su
  `plan.md`. Si contradice al brief, gana el brief; si contradice a un `plan.md`, gana el plan.
- Specs por feature: `docs/specs/<NNN-feature>/` (ver `docs/specs/README.md`)

Al ser un proyecto único, las specs viven en **un solo árbol numerado**.

## Principios centrales

1. **Monolito modular**: un despliegue, módulos con fronteras reales. La modularidad se
   sostiene con disciplina de dependencias.
2. **Módulos autocontenidos**: cada módulo de dominio agrupa sus rutas, schemas, servicio,
   repositorio, modelos y tasks.
3. **Comunicación por eventos**: un módulo **nunca importa otro módulo**. Publica un evento de
   dominio y sigue; quien lo necesite se suscribe. Es la regla que hay que defender en el review.
4. **Type safety**: TypeScript estricto y type hints completos en Python.
5. **Sincronización de base de datos**: los modelos DEBEN estar sincronizados con las tablas
   mediante migraciones de Alembic.
6. **Nada se descarta**: un dato que no se puede interpretar va a cuarentena y genera una
   excepción para revisión humana. Nunca se pierde silenciosamente.
7. **Testing**: cobertura > 80%, siguiendo principios de TDD.

## Estructura del repositorio

```
.
├── frontend/                   # Aplicación Next.js
│   ├── app/                    # App Router
│   │   ├── (auth)/             # Rutas públicas: login, reset-password
│   │   ├── (private)/          # Rutas protegidas
│   │   │   ├── layout.tsx      # Chequeo de autenticación
│   │   │   ├── page.tsx        # Dashboard
│   │   │   └── <modulo>/       # Una carpeta por módulo de dominio
│   │   ├── api/                # API routes (proxy y auth de sesión)
│   │   ├── actions/            # Server Actions
│   │   └── layout.tsx          # Layout raíz
│   ├── components/
│   │   ├── ui/                 # Primitivas de shadcn/ui
│   │   └── <modulo>/           # Componentes por módulo de dominio
│   └── lib/                    # Utilidades, cliente de API, tipos generados
│
├── backend/                    # Aplicación FastAPI
│   ├── app/
│   │   ├── main.py             # Composition root: registra los routers y los errores
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── database.py         # Engine y sesión async
│   │   ├── logging.py          # Logging estructurado
│   │   ├── models.py           # Registro de modelos para el mapper y Alembic
│   │   ├── shared/             # Kernel: errores, repositorio base, normalización
│   │   │   ├── events/         # El bus y el catálogo de eventos de dominio
│   │   │   ├── parameters.py   # Catálogo de parámetros del negocio: rango y valor inicial
│   │   │   ├── sections.py     # Las secciones del negocio, vocabulario de nadie
│   │   │   └── corrections.py  # Forma de una corrección manual: estados y motivos
│   │   ├── worker/             # Celery: app, puente async, scheduler
│   │   └── modules/            # Módulos de dominio
│   │       ├── identity/       # Usuarios, roles, sesión (RBAC)
│   │       ├── portal/         # Extracción: cliente Playwright + parsers por sección
│   │       ├── ingestion/      # raw → staging → core: hash, tipado, cuarentena
│   │       ├── catalog/        # Productos, precios, rubros y stock
│   │       ├── purchases/      # Padrón, facturas, pagos, recibos, calendario y órdenes
│   │       ├── sales/          # Ventas, deduplicación y tablero comercial
│   │       ├── messaging/      # La bandeja de mensajes del portal
│   │       ├── notifications/  # Avisos al equipo por WhatsApp (Evolution API)
│   │       ├── triage/         # Cola de excepciones y reglas aprendidas
│   │       └── operations/     # Jobs, parámetros, auditoría
│   ├── alembic/                # Migraciones
│   └── tests/                  # unit · integration · e2e
│
├── agents/                     # Cómo se trabaja
│   ├── roles/                  # Autoridad y responsabilidades de cada rol
│   └── skills/                 # Procedimientos paso a paso
├── docs/                       # Qué se construye
│   ├── PROJECT_BRIEF.md        # Definición acordada con el cliente
│   ├── FDE_ASSESSMENT.md       # Relevamiento preliminar del FDE (interno, no vinculante)
│   └── specs/                  # Specs por feature (árbol único numerado)
│       ├── <NNN-feature>/      # spec.md + plan.md + tasks.md + diagrams/
│       └── archive/            # Features ya entregadas
├── scripts/                    # Utilidades: diagramas y entregable del cliente
├── .claude/                    # Puente a Claude Code: CLAUDE.md, comandos, permisos
├── .vscode/                    # Extensiones recomendadas y ajustes del workspace
├── dist/                       # GENERADO y gitignorado: el entregable del cliente
└── docker-compose.yml          # Entorno de desarrollo
```

### Anatomía de un módulo

```
backend/app/modules/<module>/
├── __init__.py
├── routes.py          # Endpoints de FastAPI
├── schemas.py         # Schemas de Pydantic (contrato HTTP)
├── service.py         # Lógica de negocio · privado del módulo
├── handlers.py        # Reacciones a eventos de otros módulos (si el módulo escucha algo)
├── repository.py      # Acceso a datos · privado del módulo
├── models.py          # Modelos de SQLAlchemy · privados del módulo
└── tasks.py           # Tasks de Celery (si el módulo tiene trabajo en background)
```

No todos los módulos necesitan todas las piezas. `handlers.py` sólo existe si el módulo reacciona
a algo que pasó en otro lado. `portal`, por ejemplo, no expone `routes.py`
porque no tiene superficie HTTP propia: es un servicio de extracción que consumen las tasks.
Un módulo puede sumar las piezas que su dominio pida: `security.py`, `parsers/` y similares,
privadas como el repositorio y los modelos. La excepción es `dependencies.py`, que es
composición HTTP sobre el servicio y **sí** puede montarse desde `app/main.py` o desde el router
de otro módulo — es lo que permite que una ruta declare su autorización sin cruzar la frontera.
Lo verifica `backend/tests/architecture/test_module_boundaries.py`, que es la autoridad sobre
qué es privado.

## Fronteras entre módulos (ESTRICTO)

La regla es una sola y se verifica en cada review:

> **Un módulo nunca importa otro módulo. Se comunican por eventos.**

Concretamente:
- ❌ `from app.modules.purchases.service import PurchasesService`
- ❌ `from app.modules.purchases.repository import PurchasesRepository`
- ❌ `from app.modules.purchases.models import Supplier`
- ✅ `from app.shared.events import events, InvoicesRegistered`

Todo lo que hay dentro de un módulo es privado, `service.py` incluido. Lo genuinamente transversal
—normalización de texto, tipos de dinero, paginación, errores de dominio, el bus— vive en
`app/shared/`, que **no** importa de `modules/`. `main.py` es el *composition root*: registra el
router de cada módulo, importa sus handlers y mapea los errores de dominio a códigos HTTP. Es el
único lugar que conoce a todos los módulos.

### La única excepción: autorización

`dependencies.py` sí se monta desde fuera. Una request tiene que saber si puede continuar **antes**
de que corra su handler, y un evento no responde eso a tiempo. La excepción está fijada por nombre
de archivo en `backend/tests/architecture/test_module_boundaries.py`: ampliarla exige editar el test
a propósito, que es exactamente la fricción que se busca.

### Cómo se comunican, entonces

```
  ingestion.service                 app.shared.events            purchases.handlers
        │                                  │                              │
        │  publish(InvoicesNormalized)     │                              │
        ├─────────────────────────────────►│                              │
        │                                  │   await handler(event, ss)   │
        │                                  ├─────────────────────────────►│
        │                                  │                              │
        └──────────────── misma sesión · misma transacción ───────────────┘
```

- **El catálogo es compartido.** Los eventos viven en `app/shared/events/catalog.py`, no dentro del
  módulo que los publica: si `purchases` tuviera que importar `ingestion.events`, volvería el
  acoplamiento que la regla prohíbe. Es el precio de que los módulos no se conozcan.
- **Un evento es un hecho consumado.** Va en pasado (`InvoiceRegistered`, no `RegisterInvoice`), es
  inmutable, y lleva identificadores y valores planos — nunca un modelo de SQLAlchemy.
- **Los handlers comparten la transacción del publicador**, y si uno falla, la aborta. Un evento no
  es un lugar donde el trabajo se pierde en silencio.
- **Lo que no puede bloquear al publicador encola una task de Celery** y vuelve enseguida.
- **Publicar sin oyentes es legal**: un módulo informa un hecho, no exige audiencia.

### Cómo se lee lo que es de otro

Sin imports, una lectura sincrónica entre módulos deja de ser gratis. El módulo que necesita datos
ajenos mantiene su **propia proyección**, alimentada por los eventos a los que se suscribe: es su
tabla, en su schema, con la forma que su dominio necesita.

Cuando eso parece imposible —cuando dos módulos necesitan leerse mutuamente todo el tiempo— casi
siempre significa que son en realidad uno solo, y la respuesta es corregir la frontera, no agregar
el import. Escalá al `Backend-Architect` antes de romper la regla.

Hoy hay cuatro proyecciones, y cada una existe por una lectura que no podía ser un evento:

| Proyección | La mantiene | Alimentada por | Contesta |
|---|---|---|---|
| `staging.resolution_rule` | `ingestion` | `QuarantineCaseResolved`, `QuarantineRuleRevoked` | ¿alguien ya decidió sobre una fila así? |
| `core.category_alias` | `catalog` | los mismos, más `QuarantineRuleRedecided` | ¿a qué rubro corresponde esta forma escrita? |
| `core.messaging_supplier` | `messaging` | `SuppliersNormalized` | ¿quién de los proveedores mandó este mensaje? |
| `core.sales_product` | `sales` | `ProductsRegistered` | ¿existe el producto que esta venta menciona? |

Y cuatro tablas de parámetros —`catalog_setting`, `purchase_setting`, `sales_setting`,
`notification_setting`— por lo mismo: los parámetros son de `operations`, y cada módulo guarda los
que lee, alimentado por `BusinessParameterChanged`.

**El resumen diario es el caso raro y vale leerlo.** Es un mensaje sobre el negocio de dos módulos
que no pueden leerse entre sí, y que quien lo manda tampoco puede leer. Se arma **preguntando**:
`notifications` publica `DailyDigestRequested`, cada módulo que tiene algo que decir contesta con un
`DailyDigestContribution`, y como el bus es en proceso y sincrónico, para cuando `publish` vuelve ya
están todas las respuestas.

## Flujo de datos

La extracción no escribe nunca directamente sobre el modelo canónico. Atraviesa cuatro
esquemas de PostgreSQL, en un solo sentido:

```
SIGProv ──(Playwright)──> raw ──> staging ──> core
                           │        │
                           │        └── cuarentena ──> operations.exception ──> revisión humana
                           └── verbatim + hash · nunca se sobrescribe
```

**Siete secciones del portal recorren ese camino**, y todas de la misma forma: `portal` navega y
guarda, `ingestion` tipa, y el módulo de negocio se queda con lo que se pudo leer.

| Sección | `raw` | `staging` | `core` |
|---|---|---|---|
| `/precios` | `PRICES` | `price_row` | `catalog` |
| pantalla de historial de un producto | `PRICE_HISTORY` | `price_history_row` | `catalog` |
| `/facturas` | `INVOICES` | `invoice_row` | `purchases` |
| el archivo de cada factura | `INVOICE_FILE` | `invoice_file_read` | `purchases` |
| `/estado-cuenta` | `SUPPLIER_LEDGER` | `supplier_row`, `payment_row` | `purchases` |
| `/ordenes-compra` | `PURCHASE_ORDERS` | `purchase_order_row` | `purchases` |
| `/mensajes` | `MESSAGES` | `message_row` | `messaging` |
| `/ventas` | `SALES` | `sale_row` | `sales` |

El archivo de la factura es el único que no es una pantalla: es la evidencia que la revisión le
muestra a una persona, y se guarda como todo lo que viene de afuera.

| Esquema | Contenido | Regla |
|---|---|---|
| `raw` | Lo extraído tal cual, más un hash del contenido | Lo extraído es inmutable: contenido, hash, tipo y fecha de llegada nunca se sobrescriben ni se corrigen. Una columna de contabilidad del pipeline sí se escribe, y el test enumera cuáles no (Art. III). |
| `staging`  | Tipado y normalizado; cada fila queda `valido` o `cuarentena` | Reproducible: se puede reconstruir desde `raw`. |
| `core` | Modelo canónico del negocio | Solo se alimenta de filas `valido`. |
| `operations`  | Jobs, excepciones, parámetros, auditoría | Es el sistema operando sobre sí mismo. |

## Flujo de desarrollo (Spec-Driven Development)

1. **PROJECT_BRIEF** → necesidades y alcance acordados con el cliente
2. **`/specify` + `/clarify`** → `docs/specs/<NNN-feature>/spec.md` (español, funcional)
3. **`/approve-spec`** → el cliente valida y firma la spec (gate; estado `Aprobado`)
4. **`/plan` → `/tasks` → `/analyze` → `/implement`** → construcción a partir de la spec aprobada
5. **Tests** → el Developer cubre su lógica; el Tester, la suite como sistema
6. **`/converge`** → el código implementado corresponde a lo que el cliente firmó
7. **`/review-feature`** → quality gate previo al merge
8. **`/ship`** → commit + push + PR, y la spec se mueve a `docs/specs/archive/`

**Lineamientos de idioma:**
- **Toda la documentación va en español**: `README.md`, `ARCHITECTURE.md`, `AGENTS.md`,
  `CONSTITUTION.md`, `CONVENTIONS.md`, `agents/**` y todos los artefactos de spec
  (`spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/`, `diagrams/`)
- **El código va en inglés**: nombres, comentarios, docstrings, mensajes de commit
- Excepción: los strings que ve el usuario en la UI van en español

### Agregar un módulo o una feature

**Backend** — dentro de un módulo existente si la capacidad ya tiene dueño; si no, un módulo
nuevo bajo `backend/app/modules/<module>/` siguiendo la anatomía de arriba y registrando su
router en `app/main.py`.

**Frontend** — página en `frontend/app/(private)/<modulo>/`, componentes en
`frontend/components/<modulo>/`, acceso a datos en `frontend/lib/`.

Un módulo nuevo se justifica cuando representa una **capacidad del negocio** con lenguaje
propio, no cuando simplemente hay muchos archivos.

## Estrategia de testing

- **Tests unitarios**: lógica pura, servicios, normalización (rápidos, sin dependencias externas)
- **Tests de integración**: endpoints, repositorios, migraciones (base real, servicios externos mockeados)
- **Tests de extracción**: parsers del portal contra HTML fijado (fixtures), nunca contra el portal en vivo
- **Tests E2E**: flujos completos críticos
- **Objetivo de cobertura**: > 80%

## Estrategia de base de datos

- **ORM**: SQLAlchemy 2.0 en modo **async** (`asyncpg`)
- **Migraciones**: Alembic
- **Esquemas**: `raw`, `staging`, `core`, `operations` (ver Flujo de datos)
- **Regla crítica**: los modelos DEBEN estar sincronizados con las tablas
- **Flujo**: modificar el modelo → crear la migración → correr la migración → verificar la sincronización

## Trabajo en background

- **Broker**: RabbitMQ
- **Ejecutor**: Celery (worker + beat para la extracción programada)
- **Puente async**: los workers de Celery son sincrónicos y el acceso a datos es async. El
  puente es **uno solo**, en la base de las tasks (`app/worker/`), y las tasks llaman a los
  servicios async a través de él. No se dispersan `asyncio.run()` por el código.
- **Idempotencia**: toda task debe poder re-ejecutarse sin duplicar efectos. La deduplicación
  se apoya en el hash de `raw`.

## Estrategia de deploy

**Un solo `docker-compose.yml`, tres modos**, para que no haya dos archivos que se desincronicen:

| Comando | Qué levanta | Para qué |
|---|---|---|
| `make dev` | PostgreSQL + RabbitMQ | Trabajo diario: la app va **nativa** en el host, con recarga en caliente y debugger |
| `make full` | además backend, Celery worker, Celery beat y frontend | El stack completo en esta máquina, con los puertos publicados en loopback y sin reverse proxy |
| `make deploy` | trae los cambios de git y levanta lo mismo, con el frontend detrás de **Traefik** | El servidor. Corre **en** el VPS, no desde una laptop |
| `make tools` | además Flower | Inspeccionar las tasks de extracción en vuelo |

`full` y `deploy` comparten backend, worker y beat; se diferencian sólo en cómo se llega al
frontend —puerto publicado contra Traefik—, y por eso son dos servicios y no uno: la red
`traefik` es externa y sólo existe en el servidor, así que `full` tiene que poder ignorarla.

**Sólo el frontend se publica.** La API no tiene router propio en ningún modo: el navegador habla
con Next, y sólo Next habla con la API por la red interna. Eso ya lo hace
`app/api/proxy/[...path]`, que además le adosa el token de sesión — algo que un reverse proxy no
puede hacer, porque no puede leer una cookie httpOnly. No hay nginx.

El TLS lo resuelve Traefik por labels, y el certificado se emite por **desafío DNS contra
Cloudflare**: el registro puede quedar proxeado y nada tiene que responder en el puerto 80.

No existe un modo intermedio "la app en contenedores con recarga en caliente": Compose no permite
condicionar `volumes` ni el `target` de un build con una variable, así que sostenerlo obligaba a
duplicar cada servicio. Para desarrollar, la app va nativa.

Los puertos de Postgres y RabbitMQ se publican en `127.0.0.1`, no en `0.0.0.0`: en local alcanza
para que el backend nativo se conecte, y en producción evita exponer la base por olvido.

## Stack tecnológico

### Frontend
- **Framework**: Next.js (App Router)
- **Librería de UI**: React
- **Estilos**: Tailwind CSS
- **Componentes**: shadcn/ui
- **Lenguaje**: TypeScript

### Backend
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 async + asyncpg
- **Migraciones**: Alembic
- **Extracción**: Playwright
- **Background**: Celery + RabbitMQ
- **Lenguaje**: Python
- **Gestor de paquetes**: uv

### Infraestructura
- **Base de datos**: PostgreSQL
- **Message broker**: RabbitMQ
- **Contenedores**: Docker Compose

## Convenciones de código

Los estándares de Python y de TypeScript, el manejo de errores, la configuración y secretos, las
reglas de tests, la gestión de dependencias (uv / npm) y las convenciones de git viven en
**`CONVENTIONS.md`**, que es su fuente única. Cada convención tiene ahí un identificador estable
(`PY-04`, `TS-02`, `DB-01`, …), su severidad y el comando que la verifica.

Este documento explica **la arquitectura**: qué módulos hay, dónde están sus fronteras y por qué el
flujo de datos va en un solo sentido. `CONVENTIONS.md` explica **cómo se escribe el código** dentro
de esa arquitectura, y su única regla arquitectónica es `GEN-02` — un módulo nunca importa otro
módulo —, que está ahí porque la verifica
`backend/tests/architecture/test_module_boundaries.py`.

## Flujo de Git

Un solo producto, un solo flujo:

1. Crear una rama de feature desde `main`: `git checkout -b feat/<NNN-feature>`
2. Implementar según `tasks.md`, con tests
3. `/review-feature` como quality gate
4. `/ship` → commit + push + PR contra `main`
5. Merge una vez aprobado

`main` es la rama estable y desplegable. No se commitea directo a `main`.

## Actualización de la documentación

Al hacer cambios estructurales:
- Actualizar `ARCHITECTURE.md` si cambian los módulos o sus fronteras
- Actualizar `AGENTS.md` si cambian los flujos operativos o el enforcement
- Actualizar `CONVENTIONS.md` si cambia una convención de código (y sólo ahí: es la
  fuente única; los identificadores no se reutilizan)
- Actualizar las skills/roles correspondientes si cambian los procedimientos
