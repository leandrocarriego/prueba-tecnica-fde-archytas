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
│   ├── PROJECT_BRIEF.md    lo acordado con el cliente (se firma)
│   ├── FDE_ASSESSMENT.md   relevamiento técnico preliminar (interno, no vinculante)
│   └── specs/        specs por feature + archive/ de las entregadas
├── scripts/          utilidades: diagramas y entregable del cliente
├── .claude/          puente a Claude Code: CLAUDE.md, comandos y permisos
├── .vscode/          extensiones recomendadas y ajustes del workspace
└── docker-compose.yml
```

## 📐 Spec-Driven Development (SDD)

La *spec* por feature es la fuente de verdad que dirige plan → tasks → implementación,
manteniendo el gate de aprobación con el cliente.

El flujo está **inspirado en [GitHub Spec Kit](https://github.com/github/spec-kit)** —de ahí salen
la cadena de comandos y la idea de historias de usuario priorizadas y entregables de forma
independiente— pero los comandos y las plantillas son **propios**: en español, con la estructura de
carpetas de este repositorio y con los dos gates que el proyecto necesita.

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

> Los trece comandos viven en `.claude/commands/` y no dependen de ninguna herramienta externa.
> Las plantillas de `spec.md`, `plan.md` y `tasks.md` están en `docs/specs/`.

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

Un solo `docker-compose.yml` con tres modos, así que no hay dos archivos que se desincronicen:

```bash
make dev     # Postgres + RabbitMQ; backend y frontend nativos (día a día)
make full    # todo en contenedores en esta máquina, sin reverse proxy
make deploy  # el servidor: lo mismo, con el frontend detrás de Traefik
make tools   # suma Flower para mirar la cola
make down    # baja todo, sea cual sea el modo
```

`make deploy` **se corre en el servidor**, no desde una laptop: necesita la red `traefik`, que es
compartida por todos los proyectos del host, y un `.env` con `DOMAIN`. Verifica las dos cosas
antes de tocar nada, **trae los cambios con `git pull --ff-only`** y recién ahí reconstruye: lo
que se despliega es lo que está en git, y dejar eso como un paso aparte es cómo un servidor
termina corriendo algo que nadie puede señalar. Si encuentra cambios sin commitear en el
servidor, se detiene.

Y **limpia lo que ensucia**: cada rebuild deja atrás la imagen anterior sin su tag, unos 660 MB
por vez, y nadie las junta. `make deploy` borra las que quedaron sin tag **de este proyecto**,
leyendo la etiqueta que Compose le puso al contenedor que acaba de crear. Nunca borra volúmenes
ni toca imágenes de otros stacks: el VPS es compartido, y los volúmenes sueltos que hay ahí son
bases de datos de otros proyectos.

Actualizar el deploy es entonces una sola línea:

```bash
ssh <servidor> 'cd /srv/projects/<org>/<proyecto> && make deploy'
```

Después de desplegar quedan dos pasos que el target no hace solo, a propósito: `make db-migrate`
aplica las migraciones, y `make db-owner` crea el primer acceso —el del dueño, el único que no
puede nacer de una pantalla porque a todos los demás los invita él—. El segundo es idempotente y
se corre una sola vez.

El `.env` del servidor necesita, además de `DOMAIN`, tres cosas sin las cuales la plataforma
levanta pero **nadie puede entrar**: `FRONTEND_URL=https://$DOMAIN` (a dónde apuntan los enlaces
que salen por WhatsApp), `EVOLUTION_API_KEY` con `NOTIFICATIONS_WHATSAPP_TO` (el canal por el que
viaja la invitación) y `OWNER_EMAIL`/`OWNER_NAME`/`OWNER_PHONE` (a quién se le entrega). Están
todas en `.env.example`.

### WhatsApp

Todo lo que la plataforma tiene que decirle a una persona sale por ahí, y quien lo pone en el
cable es **Evolution API**, un servicio más de este `docker-compose.yml`. Sostiene una sesión de
WhatsApp real, así que **no se publica**: no tiene router de Traefik y su puerto va a loopback.
Se la alcanza por el túnel SSH que ya te trae al servidor.

Vincular el teléfono es un paso manual y de una sola vez —una sesión de WhatsApp la abre una
persona—, y está en `agents/skills/deploy.md`. Hasta que el estado de la instancia sea `open`,
`NOTIFICATIONS_TO_DISK=true` deja cada mensaje como archivo en el worker en lugar de mandarlo:
un canal a medio configurar que dice haber mandado algo es peor que uno apagado.

Guarda la instancia y nada más. Los mensajes, los contactos y los chats quedan desactivados a
propósito: son de quien está conversando, no nuestros.

**Sólo el frontend queda publicado.** La API no tiene router: el navegador habla con Next, y sólo
Next habla con la API por la red interna, a través de `app/api/proxy/[...path]`, que además le
adosa el token de sesión. No hay nginx. El TLS lo resuelve Traefik por labels, con el certificado
emitido por desafío DNS contra Cloudflare.

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
make dev           # levantar la infraestructura (Postgres + RabbitMQ)
make full          # levantar todo el stack en contenedores
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
