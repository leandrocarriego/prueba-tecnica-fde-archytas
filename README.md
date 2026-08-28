# Plataforma Cordillera

Aplicación web a medida para **Ferretería Industrial Cordillera**. Extrae la información del
portal legacy **SIGProv**, la normaliza y la convierte en un sistema operativo propio del
negocio: catálogo, compras, facturación, ventas, cuenta corriente y una cola de excepciones
donde cada decisión humana se vuelve una regla reutilizable.

No es un boilerplate. Es un producto único, para un cliente único, construido como
**monolito modular**.

## 🏗️ Arquitectura

- **Frontend**: Next.js (App Router) con React 19, shadcn/ui y Tailwind CSS
- **Backend**: FastAPI como monolito modular, SQLAlchemy 2.0 async sobre PostgreSQL
- **Extracción**: Playwright contra SIGProv (automatización de navegador, solo lectura)
- **Background**: Celery + RabbitMQ para extracción programada e ingesta

### El sistema origen

SIGProv **no es nuestro y no tiene API**. Dos restricciones que atraviesan todo el diseño:

1. **Solo lectura** — nunca se escribe contra el portal.
2. **La extracción es automatización de navegador, no un cliente HTTP** — el portal expone
   endpoints JSON internos que **no se usan**: se lo trata como el sistema viejo sin
   integración que representa, y se lee de la pantalla renderizada.

### Módulos de dominio

```
backend/app/modules/
├── identity/     usuarios, roles, sesión (RBAC)
├── portal/       extracción: cliente Playwright + parsers por sección
├── ingestion/    raw → staging → core: hash, tipado, cuarentena
├── suppliers/    padrón + resolución de entidades
├── catalog/      productos, precios, categorías
├── purchasing/   órdenes de compra y recepciones
├── billing/      facturas, comprobantes de pago, estado de cuenta
├── sales/        ventas y deduplicación
├── messaging/    mensajes internos
├── triage/       cola de excepciones y reglas aprendidas
└── operations/   jobs, parámetros, auditoría
```

**La regla que sostiene la modularidad**: un módulo **nunca importa otro módulo**. Lo que uno
necesita contarle al resto es un evento de dominio publicado en `app/shared/events`; quien lo
necesite se suscribe. La única excepción es `dependencies.py`, porque autorizar una request es
una pregunta síncrona que un evento no llega a contestar.

### Flujo de datos

```
SIGProv ──(Playwright)──> raw ──> staging ──> core
                           │        │
                           │        └── cuarentena ──> operations.exception ──> revisión humana
                           └── verbatim + hash · nunca se sobrescribe
```

Nada se descarta: lo que no se puede interpretar va a cuarentena y genera una excepción para
revisión humana.

📖 Detalle completo en [ARCHITECTURE.md](./ARCHITECTURE.md)

## 🚀 Inicio rápido

### Prerrequisitos

- Docker & Docker Compose
- Node.js 18+ (frontend)
- Python 3.12+ (backend)
- [uv](https://github.com/astral-sh/uv) (gestor de paquetes Python)

### Puesta en marcha

```bash
# 1. Configurar el entorno
cp .env.example .env    # completar credenciales del portal y de la base

# 2. Levantar la infraestructura (Postgres + RabbitMQ)
make dev

# 3. Backend
cd backend && uv sync
uv run playwright install chromium   # una sola vez
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# 4. Frontend (en otra terminal)
cd frontend && npm install && npm run dev
```

### Servicios

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **RabbitMQ**: http://localhost:15672

## 📁 Estructura del proyecto

```
.
├── frontend/         Aplicación Next.js
│   ├── app/          App Router: (auth) públicas · (private) protegidas
│   ├── components/   ui/ (shadcn) + una carpeta por módulo de dominio
│   └── lib/          cliente de API, tipos generados, utilidades
├── backend/          API FastAPI
│   ├── app/
│   │   ├── main.py   composition root: registra routers y mapea errores
│   │   ├── shared/   kernel transversal: errores de dominio, repositorio base
│   │   ├── worker/   Celery: app, puente async, scheduler
│   │   └── modules/  módulos de dominio
│   ├── alembic/      migraciones
│   └── tests/        unit · integration · e2e
├── agents/           roles y skills (cómo se trabaja)
│   ├── roles/
│   └── skills/
├── docs/             qué se construye
│   ├── PROJECT_BRIEF.md
│   └── specs/        specs por feature + archive/ de las entregadas
├── scripts/          utilidades: diagramas y entregable del cliente
├── .claude/          puente a Claude Code: CLAUDE.md, comandos y permisos
├── .vscode/          extensiones recomendadas y ajustes del workspace
└── docker-compose.yml
```

## 📐 Spec-Driven Development (SDD)

El proyecto usa **Spec-Driven Development** con [GitHub Spec Kit](https://github.com/github/spec-kit).
La *spec* por feature es la fuente de verdad que dirige plan → tasks → implementación,
manteniendo el gate de aprobación con el cliente.

```
docs/PROJECT_BRIEF.md
   → /specify     → docs/specs/<NNN-feature>/spec.md   (funcional, cara al cliente)
   → /clarify     → de-risk de la spec
   → ✍️ /approve-spec  → el cliente valida y firma spec.md  (gate)
   → /plan        → plan.md (técnico; pasa el Constitution Check)
   → /tasks       → tasks.md (mapeado a skills add_*)
   → /analyze     → consistencia spec ↔ plan ↔ tasks
   → /implement   → código en backend/app/modules/ y frontend/
   → tests        → unitarios (Developer) + suite como sistema (Tester)
   → /converge    → ¿el código es lo que se firmó?
   → /review-feature  → quality gate (¿está bien escrito?)
   → /ship        → PR contra main, y la spec pasa a docs/specs/archive/
```

> Los comandos `/specify`, `/clarify`, `/plan`, `/tasks`, `/analyze`, `/implement`,
> `/constitution` y `/checklist` son **alias** de las skills `speckit-*` de Spec Kit
> (ambos nombres funcionan). `/approve-spec`, `/review-feature`, `/converge`, `/ship` y
> `/diagram` son comandos propios del proyecto.

- Principios no-negociables: [CONSTITUTION.md](./CONSTITUTION.md)
- Punto de entrada de los agentes, orden de autoridad y reglas del dominio:
  [AGENTS.md](./AGENTS.md)
- Roles y procedimientos: `agents/roles/` y `agents/skills/`

**Idioma**: toda la documentación va en español, incluidos los artefactos internos de spec.
El código va en inglés; los strings que ve el usuario en la UI, en español.

## 🔧 Desarrollo

### Agregar una capacidad nueva

1. **Backend**: dentro del módulo que ya tenga esa responsabilidad; si no existe, un módulo
   nuevo en `backend/app/modules/<module>/` con la anatomía estándar
   (`routes` · `schemas` · `service` · `repository` · `models` · `tasks`)
2. **Frontend**: página en `frontend/app/(private)/<modulo>/` y componentes en
   `frontend/components/<modulo>/`
3. **Registrar** el router del módulo en `backend/app/main.py`

Un módulo nuevo se justifica cuando aparece una **capacidad del negocio con lenguaje propio**,
no cuando un módulo existente acumula archivos.

### Variables de entorno

Copiar `.env.example` a `.env` y configurar:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`
- `PORTAL_BASE_URL`, `PORTAL_USER`, `PORTAL_PASSWORD` — credenciales de SIGProv
- `SECRET_KEY` — backend
- `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`
- `NEXT_PUBLIC_API_URL` — frontend

⚠️ Las credenciales del portal viven **solo** en el entorno: nunca en la base, nunca en el
repositorio, nunca en un log.

## 🧪 Testing

```bash
make test              # todos los tests
make test-unit         # solo unitarios (rápidos)
make test-integration  # integración
make test-cov          # con coverage

make lint              # verificar formato y linting
make format            # formatear
```

Los parsers del portal se testean contra **HTML fijado** (fixtures), nunca contra el portal en
vivo: los tests tienen que ser reproducibles y no depender de un sistema de terceros.

## 📦 Gestión de dependencias

**Backend** — `uv` es el único gestor soportado:

```bash
cd backend
uv add <package>       # agregar
uv lock                # actualizar el lockfile
uv sync                # instalar desde el lockfile
```

**Frontend** — `npm`:

```bash
cd frontend && npm install
```

Nunca editar a mano las dependencias de `pyproject.toml` ni las versiones de `package.json`.

## 🔌 Cliente de API tipado

El frontend consume la API con tipos generados desde el schema de OpenAPI:

```bash
make dev                    # el backend tiene que estar corriendo
make frontend-api-types     # generar los tipos
```

```typescript
import { apiClient } from "@/lib/api/client";

const { data, error } = await apiClient.GET("/api/v1/suppliers");
```

## 🚢 Deploy

```bash
make prod       # docker-compose.prod.yml
make prod-down
```

## 📄 Documentación para el cliente

El cliente no recibe el repositorio: recibe lo que tiene que leer y firmar, en PDF, con los
diagramas en SVG para que pueda ampliarlos.

```bash
make client-docs                                  # todo
make client-docs FEATURE=001-portal-extraction    # una feature

make diagrams                                     # regenerar los diagramas de las specs
make diagrams-check                               # sólo validar que compilen
```

Sale a `dist/cliente/`: un PDF por spec —la unidad que se firma— más un PDF combinado con el
estado del proyecto, donde las features ya entregadas van al final. Sólo se exporta lo que es
cara al cliente: `plan.md`, `tasks.md`, `contracts/` y el resto de lo interno queda afuera.
Detalle en [docs/specs/README.md](./docs/specs/README.md).

## 🛠️ Comandos útiles

```bash
make help          # ver todos los comandos
make dev           # levantar la infraestructura
make down          # detener los servicios
make logs          # ver logs
make db-migrate    # aplicar migraciones
make clean         # limpiar volúmenes y contenedores
```

## ✅ Verificación automática

**Pre-commit** — lo rápido, antes de que el cambio salga de tu máquina: formato y lint (Ruff,
Prettier, ESLint), tipos (mypy, tsc), los tests unitarios y **los de arquitectura** —las fronteras
entre módulos y la autorización de rutas—, más la validación de los diagramas Mermaid.

```bash
make pre-commit-install   # instalar
make pre-commit-run       # ejecutar en todos los archivos
```

**CI** ([`.github/workflows/ci.yml`](./.github/workflows/ci.yml)) — lo que no entra en un commit:
la suite completa contra un Postgres de verdad, el gate de cobertura del 80%, `alembic check`
(los modelos y las tablas describen lo mismo) y el build del frontend. Corre en cada PR
contra `main`.

Los mensajes de commit siguen [Conventional Commits](https://www.conventionalcommits.org/),
en inglés:

```bash
git commit -m "feat(suppliers): add fuzzy entity resolution"
git commit -m "fix(portal): wait for table content instead of load event"
```
