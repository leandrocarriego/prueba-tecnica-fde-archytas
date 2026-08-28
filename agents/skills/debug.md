# Skill — Depurar un fallo

Tags: [debug] [transversal] [calidad]

## Objetivo

Encontrar la causa raíz de un fallo y corregirla con el cambio mínimo, dejando un test que
demuestre que el caso quedó cubierto.

Es la única skill **transversal**: se puede disparar en cualquier punto de la cadena, sin
importar en qué paso del flujo SDD esté la feature.

## Cuándo usarla

- Un test falla, un endpoint devuelve algo que no corresponde, o el frontend rompe.
- Una corrida de extracción quedó en `FAILED` en `operations.job_run`.
- Un comportamiento en producción no coincide con lo que la spec prometía.
- El build, el linter o el type-check fallan por una causa que no es obvia.

No la uses para agregar capacidades: eso es `add_backend_feature`, `add_frontend_feature` o
`add_feature`.

## Precondiciones

- Existe información real del fallo: un mensaje de error, un stack trace, un test rojo o una
  fila con `error` en `operations.job_run`.
- **Si no hay información del error, PARÁ y pedila.** Depurar sin evidencia es adivinar.

## Reglas (ESTRICTO)

- **Reproducir antes de arreglar.** Un fallo que no se pudo reproducir no se puede dar por
  corregido.
- **Leer el stack trace completo**, no su resumen. La causa raíz casi nunca está en la línea
  que se imprime primero.
- **Un fallo de extracción y un dato ilegible no son lo mismo**, aunque se parezcan en el log:
  - el portal cambió su maquetado o no respondió → fallo técnico → `ExtractionError`
  - el dato existe pero no se puede interpretar → cuarentena en `staging` + fila en `operations.exception`,
    y la ingesta **no se corta** (ver `CONVENTIONS.md`, `ERR-05`)
- **Nunca "arreglar" un dato escribiendo en `raw`.** `raw` es inmutable: la corrección va en la
  transformación hacia `staging`.
- El arreglo respeta las convenciones y las fronteras como cualquier otro cambio: un fix no es
  una excepción a `CONVENTIONS.md`.

## Pasos (ORDEN OBLIGATORIO)

### 1) Recolectar la evidencia
- Backend: `docker compose logs backend`, o la salida de `uv run uvicorn` en desarrollo.
- Worker: `docker compose logs celery_worker`.
- Base: `docker compose logs postgres`.
- Corridas fallidas: consultar `operations.job_run` filtrando por `status = 'FAILED'` y leer su columna
  `error`, que guarda el motivo precisamente para este momento.
- Frontend: consola del navegador y la salida de `npm run dev`.

### 2) Seleccionar el rol
La depuración se hace **bajo el rol del área afectada**, con sus restricciones:
- Backend, módulos, fronteras → `Backend-Architect`
- Frontend, Next.js/React → `Frontend-Architect`
- Implementación dentro de un módulo → `Developer`
- Suite de tests, fixtures, cobertura → `Tester`

### 3) Reproducir
Escribí el caso mínimo que falla. Si es reproducible desde un test, **el test es el primer
entregable**: convierte el reporte en algo verificable y evita que el fallo vuelva.

### 4) Aislar la causa raíz
- ¿Las migraciones están aplicadas? `uv run alembic current` contra `uv run alembic heads`.
- ¿Los modelos están sincronizados con las tablas? `uv run alembic check`.
- ¿Las variables de entorno están donde el código las busca? El `.env` se lee desde la raíz del
  repositorio, no desde el directorio de trabajo.
- ¿El fallo cruza una frontera entre módulos? Un import que no debería existir explica más
  bugs de los que parece.

### 5) Corregir con el cambio mínimo
Arreglá la causa, no el síntoma. Si el arreglo se está volviendo grande, es señal de que el
problema es de diseño: escalá al arquitecto en vez de seguir parchando.

### 6) Verificar
```bash
cd backend && uv run pytest -q && uv run ruff check app tests && uv run mypy app
cd ../frontend && npx tsc --noEmit && npm run lint
```

## Validación

- El fallo se reprodujo antes de tocar nada.
- Existe un test que falla sin el arreglo y pasa con él.
- La causa raíz está explicada, con la evidencia que la sostiene.
- La suite completa pasa; no se debilitó ningún test para lograrlo (`CONVENTIONS.md`, `TEST-06`).
- Si el fallo se originó en una expectativa equivocada de la spec o del plan, quedó reportado
  para el rol dueño de ese artefacto, no arreglado en silencio en el código.

## Errores comunes (evitar)

- **Arreglar el síntoma.** Silenciar una excepción o agregar un `if` defensivo sin entender por
  qué llegó ese valor.
- **Debilitar el test que descubrió el bug** (`skip`, `xfail` sin razón, assert relajado) en vez
  de corregir el código. Es Blocker en el review.
- **Confundir un dato ilegible con un fallo técnico**, y cortar la ingesta por algo que debía ir
  a cuarentena.
- **Depurar contra el portal en vivo.** Los parsers se prueban contra HTML fijado; el portal es
  de un tercero y puede cambiar entre dos corridas.
- **Arreglar sin reproducir** y declarar el trabajo terminado.

## Troubleshooting

### El fallo no se reproduce localmente
Compará entorno: versión de Python, migraciones aplicadas, contenido del `.env`, y si la base
tiene los datos que el caso supone. Si sólo ocurre en una corrida programada, revisá si depende
del estado que dejó una corrida anterior — eso suele ser una task que no es idempotente
(`CONVENTIONS.md`, `TEST-07`).

### La corrida falló pero `operations.job_run` no dice por qué
El motivo se guarda en `error` al llamar a `fail_run`. Si está vacío, el fallo ocurrió antes de
registrar la corrida o alguien capturó la excepción sin propagarla.

### El error aparece sólo con el worker, no con la API
Casi siempre es el puente async: el acceso a datos es asíncrono y el worker es sincrónico. El
único puente válido es `app/worker/bridge.py`; abrir un event loop en otro lado rompe el pool
de conexiones (`CONVENTIONS.md`, `PY-06`).
