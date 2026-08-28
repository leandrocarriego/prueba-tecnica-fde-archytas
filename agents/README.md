# `agents/` — Cómo se trabaja

Esta carpeta define cómo deben operar los agentes de IA y las personas que trabajan en este
repositorio.

- `roles/` — autoridad, límites y responsabilidades de cada rol
- `skills/` — procedimientos operativos paso a paso

Vive en la raíz y no en `docs/` porque el repositorio separa **cómo se trabaja** de **qué se
construye**.

## Los roles no son personas

El trabajo lo lleva **de punta a punta un Forward Deployed Engineer**: del pedido del cliente a
la funcionalidad en producción, sin un analista que releve y alguien distinto que construya.

Los ocho roles de `roles/` no contradicen eso: **no son ocho personas, son ocho sombreros que se
pone la misma**. Separan *momentos del trabajo*, no gente.

Existen por una razón concreta: un mismo agente que escribe la spec, decide la arquitectura,
implementa y después se revisa a sí mismo tiende a aprobar lo que ya hizo. Ponerle un nombre a
cada momento —y un orden con dos gates— obliga a cambiar de criterio antes de avanzar:

- el `Solution-Designer` no puede resolver técnicamente lo que el cliente todavía no firmó,
- el `Code-Reviewer` mira el changeset con los ojos de quien no lo escribió,
- el `Lead` pregunta si el código es lo que se acordó, que es una pregunta distinta de si está
  bien escrito.

Es la disciplina que hace posible el end-to-end sin perder el rigor.

## Por dónde empezar

Por [`AGENTS.md`](../AGENTS.md), en la raíz: define el orden de autoridad, la cadena completa de
roles con sus dos gates, la selección automática de rol y el mapa de triggers de skills con su
rol dueño.
