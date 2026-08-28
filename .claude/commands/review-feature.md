---
description: Quality gate del Code-Reviewer sobre un changeset (argumento opcional: 001-portal-extraction)
---

Asumí el rol **Code-Reviewer** (`agents/roles/`) y ejecutá el procedimiento de
**`agents/skills/review_feature.md`**, con el argumento **$ARGUMENTS**.

Leé la skill completa antes de empezar y seguí sus pasos **en orden**, incluida su validación.

Si no se pasó argumento, revisá el cambio de la rama actual contra `main`.

<!--
  Este archivo es un puente, no un procedimiento.

  El procedimiento vive en `agents/skills/`, fuera de `.claude/`, porque no le pertenece a
  ninguna herramienta: integrar otro proveedor de IA es escribir estos trece punteros en su
  formato, no reescribir trece procedimientos. Es la misma razón por la que `AGENTS.md` está en
  la raíz y `.claude/CLAUDE.md` sólo lo importa.

  Si te dan ganas de agregar una regla acá, va en la skill.
-->
