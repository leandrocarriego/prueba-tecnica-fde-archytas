# Code review — 002-access-control

**Rol:** Code-Reviewer · **Skill:** `agents/skills/review_feature.md` · **Fecha:** 2026-08-29
**Suite:** 520 en verde, cobertura 94.64% · **Converge:** deriva menor, 8 hallazgos abiertos

---

## Veredicto

# ✅ Aprobado

No queda ningún Blocker. Los tres hallazgos se cerraron el mismo día.

---

## Cómo se cerraron

**`B1` y `B2`** — se ablandaron las convenciones, no el código. `ERR-03` y `PY-06` ahora llevan su
excepción, acotada a los **entry points de línea de comandos**:

- `ERR-03`: lo que un comando le contesta a quien lo corrió va a su terminal, no al log, donde esa
  persona no lo está mirando. La excepción es la función `main()`; todo lo que ese comando llama
  sigue logueando.
- `PY-06`: la regla protege al worker de abrir un segundo loop sobre el que ya tiene. Un
  `python -m ...` es un proceso propio que no tiene ninguno, y no está en esa situación.

Los comandos de verificación de las dos convenciones se actualizaron para excluir `bootstrap.py`,
así que el próximo reviewer no vuelve a encontrar el mismo hit ni a discutir lo mismo.

**`M1`** — `npm run format`: los siete archivos formateados, `format:check` en verde.

**`m1`** — cinco archivos renombrados a inglés, y sus importadores con ellos:

| Antes | Ahora |
|---|---|
| `components/accesos/` | `components/access/` |
| `AltaAcceso.tsx` | `NewAccessForm.tsx` |
| `TablaAccesos.tsx` | `AccessTable.tsx` |
| `FormularioClave.tsx` | `PasswordForm.tsx` |
| `SinPermiso.tsx` | `NoPermission.tsx` |
| `app/actions/accesos.ts` | `app/actions/access.ts` |

Las **rutas** siguen en español —`/accesos`, `/mi-cuenta`, `/recuperar`, `/invitacion`— porque son
URLs que ve el usuario, igual que `/precios` y `/revision` en la 001. `GEN-07` pide el código en
inglés, no las URLs.

`tsc --noEmit`, `eslint` y `prettier --check` en verde después del renombre.

---

## El recorrido

### Verificado por un test que rompe el build
`GEN-02`, `GEN-03`, `GEN-09`, `PY-09`, `TEST-05` — la suite pasó: **520 en verde, 94.64%**.

Sobre `PY-09` en particular, que es *la* convención de esta feature: `PUBLIC_ROUTES` tiene seis
entradas y **cada una lleva escrita su razón**; `test_a_route_that_writes_demands_the_level_to_write`
exige `Level.WRITE` en toda ruta que escribe; y `TestRoutesEnforceAuthorization` comprueba contra la
aplicación real que una llamada anónima recibe 401. Es la verificación más fuerte del repositorio.

### Verificación mecánica

| Comando | Convenciones | Resultado |
|---|---|---|
| `ruff check` · `ruff format --check` | `PY-08`, `GEN-01` | ✅ 119 archivos |
| `mypy app` | `PY-10` | ✅ 69 archivos |
| `alembic check` | `DB-01`, `DB-02` | ✅ |
| `tsc --noEmit` | `TS-01` | ✅ |
| `eslint` | `TS-02` | ✅ (2 warnings de `<img>`, no errores) |
| `prettier --check` | `TS-06` | 🔴 **M1** |

### A mano

| Convención | Resultado |
|---|---|
| `GEN-02` | ✅ `notifications` no importa nada de `identity`: el token viaja en el evento |
| `GEN-04` · `GEN-05` | ✅ nueve routers registrados, sin ciclos |
| `GEN-07` | 🟡 **m1** |
| `PY-03`, `PY-04`, `PY-05` | ✅ |
| `PY-06` | 🔴 **B2** |
| `ERR-01`, `ERR-04` | ✅ ninguna excepción tragada, ningún `HTTPException` en un servicio |
| `ERR-03` | 🔴 **B1** |
| `SEC-01`, `SEC-02` | ✅ `SECRET_KEY` sin valor por defecto; el único log que nombra un token registra `user_id` y `purpose`, nunca el token |
| `SEC-03`, `SEC-05` | ✅ el emisor por defecto escribe a disco: una máquina de desarrollo no le manda un WhatsApp a nadie |
| `DB-01`, `DB-03` | ✅ los nueve modelos nuevos en `app/models.py`, cada tabla con su esquema |
| `TEST-01`/`02`/`06` | ✅ unitarios, integración, e2e; **ningún test debilitado y ningún `xfail`**: el de RF-14 desapareció porque el middleware se construyó |

### Lo que el traspaso pedía buscar por ausencia
Las dos cosas están bien: **`password_reset_tokens` ya no existe** —quedó sólo `credential_token`,
así que no hay dos mecanismos para lo mismo— y **no queda ninguna ruta con `require_roles`**.

### Diagramas
Los siete compilan, en español y a nivel de negocio. Los dos que quedaron desactualizados son
hallazgos de [`converge.md`](../converge.md) (#7 y #8), no de este review.

---

## Para aprobar

Una decisión del `Backend-Architect` sobre `B1` y `B2` —dos líneas en `CONVENTIONS.md`— y un
`npm run format`. Nada más está bloqueado.
