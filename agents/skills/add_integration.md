# Skill — Agregar una integración con un sistema externo

Tags: [integracion] [portal] [playwright]

## Objetivo
Integrar un sistema externo respetando las reglas del dominio. La integración de referencia
—y hoy la única— es el **portal legacy SIGProv**: sin API, de **solo lectura**, leído por
**automatización de navegador** con Playwright desde el módulo `portal`.

## Cuándo usarla
- Agregar la extracción de una sección nueva de SIGProv.
- Modificar el cliente de navegación o un parser existente porque cambió el portal.
- Integrar cualquier otro sistema externo (mismo procedimiento, distinta forma de leerlo).

## Precondiciones
- La sección del portal está identificada: cómo se llega, qué filtros tiene, qué columnas
  muestra, cómo pagina.
- Hay **HTML fijado** de esa sección guardado como fixture para desarrollar y testear el parser.
- Las credenciales del portal están en el entorno (`.env`), nunca en la base ni en el repositorio.
- Está claro a qué esquema `raw` va lo extraído y qué entidad de `core` alimenta después.

## Reglas (ESTRICTO)
1. **SIGProv es solo lectura.** Nunca se escribe contra el portal. Toda escritura vive en
   nuestra base.
2. **La extracción es automatización de navegador, no un cliente HTTP.** El portal expone
   endpoints JSON internos: **no se usan**. Se lee de la pantalla renderizada.
3. **Nada se descarta.** Lo que no se puede interpretar va a cuarentena en `staging` y genera una
   fila en `operations.exception` para revisión humana.
4. **`raw` es inmutable**: guarda lo extraído verbatim más su hash, y nunca se sobrescribe ni
   se corrige.
5. **Las credenciales viven sólo en el entorno.** Nunca en la base, nunca en un log.

## Pasos (ORDEN OBLIGATORIO)

### 1) Ubicar la integración en su módulo
- La navegación y los parsers de SIGProv viven en el módulo `portal`
  (`backend/app/modules/portal/`). No tiene superficie HTTP propia: lo consumen las tasks.
- Otro sistema externo va en el módulo de la capacidad que lo necesita, o en un módulo propio
  si es una capacidad con lenguaje propio.
- Otros módulos no consumen la integración: el módulo que la aloja publica lo que extrajo.

### 2) Extender el cliente de navegación
- Agregar la navegación de la sección al cliente de Playwright: login, ir a la pantalla,
  aplicar filtros, recorrer la paginación.
- Esperar por selectores, nunca por tiempos fijos.
- Timeouts, reintentos, tamaño de página y URLs base salen de `Settings`; nada hardcodeado.
- La salida de esta capa es **HTML crudo**, no entidades del negocio.

### 3) Persistir en `raw`
- Guardar lo extraído verbatim más el hash del contenido.
- El hash es lo que hace idempotente a la extracción: si ya está, no se vuelve a insertar.
- `raw` no se corrige nunca: si la extracción salió mal, se vuelve a extraer y se agrega una
  fila nueva.

### 4) Escribir el parser
- Un parser por sección, función pura: recibe HTML, devuelve filas tipadas.
- El parser **no** toca la base ni la red: sólo interpreta.
- Lo que no se puede interpretar se marca para cuarentena; no se lanza una excepción que corte
  la ingesta.

### 5) Tipar y normalizar hacia `staging`
- Convertir a los tipos del dominio usando las utilidades de `app/shared/` (texto, dinero,
  fechas).
- Cada fila queda `valido` o `cuarentena`.
- Toda fila en cuarentena genera su fila en `operations.exception` con el motivo y la referencia a `raw`.
- Ver `add_celery_task` para el disparo en background y `add_backend_feature` para el pasaje a
  `core`.

### 6) Configurar
- Agregar a `Settings` (pydantic-settings) y a `.env.example`: URL base, usuario, contraseña,
  timeouts, límites de reintento.
- Nunca loguear credenciales ni el contenido de los campos sensibles.

### 7) Manejar los errores
- Fallo técnico de la extracción (login caído, selector inexistente, timeout) → `ExtractionError`
  de `app/shared/errors.py`, con logging estructurado y reintento de la task.
- Fallo de interpretación de un dato → **cuarentena**, no excepción.
- Un cambio del portal que rompe un parser es un fallo técnico esperable: tiene que quedar
  visible en `operations`, no silenciado.

### 8) Agregar tests
- Parsers: contra **HTML fijado** en fixtures. **Nunca contra el portal en vivo.**
- Cliente de navegación: mockeado; no se abre un navegador real en la suite.
- Casos obligatorios: página vacía, paginación de más de una página, fila con dato ilegible
  (tiene que ir a cuarentena), HTML con la estructura cambiada.

### 9) Documentar
- En la spec de la feature: qué sección se lee, con qué frecuencia, qué campos se mapean y qué
  se considera dato ilegible.
- Guardar la fixture usada, con la fecha de captura.

## Validación
- La extracción corre de punta a punta contra las fixtures y deja filas en `raw`, `staging` y `core`.
- Re-ejecutar la extracción no duplica filas (dedup por hash de `raw`).
- Un dato ilegible termina en cuarentena y con su fila en `operations.exception`; la corrida no se corta.
- No hay ninguna llamada HTTP directa a endpoints internos de SIGProv:
  ```bash
  cd backend && grep -rnE "httpx|requests\." app/modules/portal
  ```
- No hay ninguna operación de escritura contra el portal.
- No hay credenciales en el código ni en los logs; todo sale de `Settings`.
- Los tests pasan con el portal apagado.

## Errores comunes (evitar)
- Usar los endpoints JSON internos del portal porque "es más rápido".
- Escribir contra SIGProv, aunque sea para marcar algo como leído.
- Testear parsers contra el portal en vivo.
- Corregir o sobrescribir filas de `raw`.
- Descartar una fila que no se pudo interpretar en lugar de mandarla a cuarentena.
- Esperar con `sleep` en lugar de esperar por selector.
- Hardcodear URLs, credenciales o timeouts.

## Troubleshooting
- Falla el login → verificar las variables de entorno; nunca hardcodear la credencial para
  "probar rápido".
- Un parser dejó de encontrar datos → el portal cambió: actualizar la fixture, arreglar el
  parser y revisar las excepciones acumuladas en `operations`.
- La extracción trae filas duplicadas → el hash de `raw` no se está calculando sobre el
  contenido correcto.
- La corrida se corta a mitad de camino → hay un dato ilegible lanzando excepción en lugar de
  ir a cuarentena.
