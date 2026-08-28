# CLAUDE.md — puente hacia AGENTS.md

Este archivo **no tiene contenido propio**. Su única función es cargar las reglas del
proyecto, que viven en `AGENTS.md`, en la raíz del repositorio.

@../AGENTS.md

> **Por qué existe.** Claude Code lee `CLAUDE.md`, **no** `AGENTS.md`. Sin este import, las
> reglas operativas —el orden de autoridad, la cadena de roles, el mapa de skills, las reglas
> del dominio— no entrarían en contexto y dependerían de que alguien se acuerde de abrir el
> archivo.
>
> **Por qué `@../AGENTS.md` y no `@AGENTS.md`.** El import se resuelve **relativo al archivo
> que lo contiene**, y este vive en `.claude/`. `AGENTS.md` se queda en la raíz porque es la
> convención agnóstica que leen las demás herramientas: esto es sólo el adaptador de Claude
> Code, y por eso vive en la carpeta de Claude Code.
>
> **Qué no va acá.** Ninguna regla, ningún flujo, ninguna convención, ninguna descripción del
> proyecto. Todo eso va en `AGENTS.md` o en los documentos a los que ese archivo delega
> (`CONSTITUTION.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `agents/`, `docs/`). Lo que se
> documente acá queda invisible para cualquier herramienta que no sea Claude Code.

<!-- SPECKIT START -->
Para contexto adicional sobre las tecnologías a usar, la estructura del proyecto,
los comandos de shell y otra información importante, leer el plan actual
<!-- SPECKIT END -->
