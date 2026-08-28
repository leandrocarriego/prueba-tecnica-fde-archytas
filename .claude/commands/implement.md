---
description: "Ejecuta las tareas de una feature, cada una por su skill (argumento: 001-portal-extraction)"
---

Asumí el rol **Developer** (`agents/roles/`) y ejecutá el procedimiento de
**`agents/skills/implement.md`**, con el argumento **$ARGUMENTS**.

Leé la skill completa antes de empezar y seguí sus pasos **en orden**, incluida su validación.

Si no se pasó argumento, inferí la feature de la rama actual —`git rev-parse --abbrev-ref HEAD`,
convención `feat/<NNN-feature>`— y **decí cuál inferiste** antes de seguir. Si la rama no sigue
esa convención, listá `docs/specs/` y pedí la feature. **No adivines.**

<!--
  Este archivo es un puente, no un procedimiento.

  El procedimiento vive en `agents/skills/`, fuera de `.claude/`, porque no le pertenece a
  ninguna herramienta: integrar otro proveedor de IA es escribir estos trece punteros en su
  formato, no reescribir trece procedimientos. Es la misma razón por la que `AGENTS.md` está en
  la raíz y `.claude/CLAUDE.md` sólo lo importa.

  Si te dan ganas de agregar una regla acá, va en la skill.
-->
