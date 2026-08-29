# Accesos por persona — Consistencia spec ↔ plan ↔ tasks

<!-- ARTEFACTO INTERNO. Hallazgos de `/analyze`. Los registra el Lead; los corrige el rol dueño de cada documento. -->

**Feature:** 002-access-control · **Ejecutado:** 2026-08-29 · **Rol:** Lead

## Veredicto: **inconsistente** — cinco hallazgos, ninguno de alcance

> **Cerrado el 2026-08-29.** Los cinco se corrigieron, cada uno por su rol dueño: A5 y A4 en
> `spec.md` (Solution-Designer), A1 en `plan.md` (Backend-Architect), A2 y A3 en `tasks.md`
> (Frontend-Architect). Reverificado después de corregir: 41 tareas y 41 citadas sin descalce,
> 53/53 requisitos con tarea y con test, spec en `Aprobado` sin marcadores. **Los tres documentos
> quedaron consistentes y la feature está lista para `/implement`.**
>
> Lo que sigue abierto no es un hallazgo sino una dependencia externa: la **tarea 24**, elegir el
> servidor de correo, sin la cual H4 y H5 no se pueden terminar.

Los tres documentos describen el mismo producto y la trazabilidad está completa. Lo que falla es
menor y localizado: dos contradicciones entre plan y tasks, una decisión del plan sin lugar
definido, un criterio aplicado a medias y una capacidad que ningún requisito pide. **Ninguno obliga
a volver al cliente ni a rehacer la firma**, y cuatro de los cinco se arreglan en una línea.

## Lo que se verificó y pasa

| Chequeo | Resultado |
|---|---|
| Todo `RF` con al menos una tarea y un test | 53/53, sin celdas vacías |
| Tareas citadas en la cobertura que existen | 41/41 |
| Tareas que no aparecen en la cobertura | ninguna |
| Historias con tareas | 6/6 |
| Spec en `Estado: Aprobado`, sin `[NECESITA ACLARACIÓN]` | sí |
| Spec sin decisiones técnicas | sí — ni endpoints, ni tablas, ni stack |
| Constitution Check completo | 9 artículos, sin excepciones solicitadas |
| Contexto de traspaso presente y útil | Developer · Tester · Code-Reviewer |
| Módulos del plan que existen | `identity`, `notifications`, `operations` — ninguno nuevo |
| Fronteras entre módulos | sin ciclos de eventos; `main.py` está fuera de `app/modules/`, así que el test de fronteras no lo alcanza y el middleware es legal |

## Hallazgos

### A1 · El middleware de 403 no tiene domicilio — **corrige: Backend-Architect, en `plan.md`**

El plan dice *"se resuelve con un middleware registrado en `main.py`"*, y ahí se detiene. Registrado
sí, pero **escrito dónde**. La lectura literal pone la lógica —resolver quién llamaba, abrir sesión
propia, escribir en `access_event`— dentro de `main.py`, que hoy sólo importa routers y no conoce
ningún servicio. Sería el primer lugar del repositorio con lógica de dominio fuera de un módulo.

El test de fronteras no lo frena: sólo recorre `app/modules/`. Por eso hay que decidirlo a
propósito y no dejarlo a criterio del Developer, que es exactamente lo que hoy pasa.

> Lo natural es que el middleware viva **dentro de `identity`** y que `main.py` sólo lo registre:
> es la misma forma que ya tiene `dependencies.py` —composición que vive en el módulo y se monta
> desde afuera— y deja a `main.py` como lo que la arquitectura dice que es.

### A2 · El plan y las tareas no dicen lo mismo del login — **corrige: Frontend-Architect, en `tasks.md`**

- `plan.md` → *"El contrato HTTP no cambia (…) Ninguna pantalla se entera."*
- `tasks.md`, tarea 10 → *"Frontend: **login contra el nuevo flujo**…"*

Los dos no pueden ser verdad. Si el contrato no cambia, el login del frontend no se toca: lo que sí
es nuevo es cerrar sesión (`POST /auth/logout` no existía), mostrar el nombre y manejar el
vencimiento por inactividad. La tarea sobredimensiona su propio alcance, y el que la ejecute va a
tocar el único camino que hoy funciona de punta a punta.

### A3 · Nadie regenera los tipos de la API — **corrige: Frontend-Architect, en `tasks.md`**

El contrato cambia: se elimina `DELETE /users/{user_id}`, entran cinco rutas nuevas y `GET /auth/me`
cambia de forma. `frontend/lib/api/types.ts` está **generado** desde OpenAPI —existe
`npm run generate-api-types` y su entrada en el `Makefile`—, y ninguna de las 41 tareas lo
regenera.

Es Definition of Done del rol: *"si cambió el contrato del backend, se regeneran en la misma
tarea"*. Sin eso, TypeScript sigue creyendo en un endpoint que ya no existe y `TS-01` no lo ve,
porque el archivo viejo compila perfecto.

### A4 · Dos duraciones inventadas con un criterio distinto al del resto — **decide: Solution-Designer**

El plan fija la vigencia de los enlaces: **7 días** la invitación, **1 hora** la recuperación. No
salen de ningún requisito ni de ningún supuesto.

El problema no es el número, es el criterio: los otros dos valores sin respaldo del cliente —cinco
intentos, quince minutos— **sí** están declarados como supuesto en la spec, a la vista al firmar.
Estos dos no. O los cuatro son supuestos declarados, o los cuatro son defaults técnicos; hoy son
dos y dos.

> RF-41 hace la vigencia observable —*"un enlace guardado y abierto más tarde de su vigencia no
> deja cambiar la clave"*—, así que el cliente la va a experimentar aunque nunca la haya acordado.

### A5 · La tarea 9 construye algo que ningún requisito pide — **elevar al humano**

La tarea 9 crea el comando de puesta en marcha que da de alta al único acceso `OWNER` desde
variables de entorno. Está mapeada a RF-01, pero RF-01 dice *"permitir entrar únicamente con un
acceso individual"* — no dice cómo aparece el primero.

**No sobra: falta en la spec.** Toda la feature presupone que el dueño ya está adentro —él invita,
él administra, él es el único que puede—, y la spec nunca dice cómo llegó. Es un supuesto que nadie
escribió.

**Decidido el 2026-08-29 por el humano: va como supuesto declarado en la spec.** Se descartaron
anotarlo en *Fuera de alcance* —dejaba el círculo sin explicar— y convertirlo en RF-54, que habría
exigido volver a firmar la spec por algo que el cliente nunca ve.

Queda pendiente de escribir por el **Solution-Designer**, en `spec.md` → *Supuestos*: que el acceso
del dueño se crea en la puesta en marcha, fuera de la aplicación, y no desde ninguna pantalla. Es
un supuesto de manual: la feature entera lo presupone y nadie lo confirmó.

## Observación, no hallazgo

**Los requisitos de H6 se construyen en H1.** Las tareas 7 (registrar ingresos y bloqueos) y 23
(las columnas de administración) cubren RF-29, RF-47 y RF-23, que la spec mapea a H6 y H4. Es
deliberado y correcto: el registro se escribe cuando el hecho ocurre, no cuando alguien lo mira, y
la pantalla que lo muestra sí queda en H6. Queda anotado para que no se lea como una tarea fuera de
lugar.
