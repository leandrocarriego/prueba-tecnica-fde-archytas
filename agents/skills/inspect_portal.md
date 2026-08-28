# Skill — Verificar la estructura de una sección de SIGProv

Tags: [portal] [extracción]

Rol dueño: **Developer**.

## Objetivo
Verificar contra el portal en vivo la estructura real de una sección, antes de escribir o
corregir su parser.

## Cuándo usarla
- Antes de escribir el parser de una sección nueva.
- Cuando un parser empieza a fallar y hay que confirmar si el portal cambió.

## Precondiciones
- Credenciales del portal en el entorno (`PORTAL_USER`, `PORTAL_PASSWORD`). **Nunca en el
  repositorio, nunca en un log** (Artículo VII).
- Chromium instalado (`make playwright-install`).

## Reglas (ESTRICTO)
- **SIGProv es de sólo lectura**: se navega y se lee, nunca se escribe (Artículo I).
- **No se usan sus endpoints JSON internos.** Se lee de la pantalla renderizada, con
  automatización de navegador.
- Lo observado se guarda como **HTML fijado** para los tests: los parsers nunca se testean contra
  el portal en vivo (`TEST-03`).

## Pasos (ORDEN OBLIGATORIO)
1. Navegar a la sección con Playwright y esperar el contenido, no el evento de carga.
2. Registrar la estructura real: columnas, tipos, formatos de fecha y de número, paginación,
   y qué aparece cuando no hay datos.
3. Anotar las diferencias contra lo que el parser (o la spec) supone.
4. Guardar una muestra del HTML como fixture.

## Validación
- [ ] La estructura observada quedó documentada, con fecha.
- [ ] Existe el fixture de HTML fijado para los tests.
- [ ] No se escribió nada contra el portal, y ninguna credencial quedó en un archivo ni en la
      salida.

## Errores comunes (evitar)
- Tomar el JSON interno porque es más cómodo que leer la tabla renderizada.
- Testear el parser contra el portal en vivo: el test deja de ser reproducible.
