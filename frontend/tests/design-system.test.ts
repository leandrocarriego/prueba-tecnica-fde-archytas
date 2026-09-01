import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

/**
 * El sistema de diseño, verificado por un test que rompe el build.
 *
 * La constitución lo dice para las fronteras entre módulos y vale igual acá:
 * *cualquier principio que dependa sólo de que alguien lo lea es una aspiración,
 * no una regla*. Estas son las dos convenciones de `CONVENTIONS.md` marcadas
 * Blocker que se pueden decidir leyendo el código, y por eso las decide este
 * archivo y no una revisión a ojo:
 *
 * - `UI-01` — ningún color literal en la UI.
 * - `UI-02` — ninguna clase de la paleta por defecto de Tailwind.
 *
 * Los colores del producto viven en `app/globals.css` y se usan por su nombre
 * (`bg-warn-surface`, `text-danger`, `pill-ok`). Un color escrito a mano dentro
 * de un componente no se puede cambiar desde la paleta, y es así como once
 * pantallas terminan dibujando el mismo estado de tres maneras distintas.
 *
 * Si una pantalla necesita un color que no existe, **se agrega el token**; no se
 * escribe el color en el componente.
 */

const ROOT = join(__dirname, '..')
const SCANNED = ['app', 'components', 'lib']

/**
 * `globals.css` es donde los colores tienen que estar, y `branding.ts` los
 * necesita como string porque las pantallas de ingreso los aplican en línea.
 * Son las dos únicas excepciones, y están acá por nombre para que ampliarlas
 * exija editar este test a propósito.
 */
const ALLOWED = new Set(['app/globals.css', 'lib/branding.ts'])

/** La paleta por defecto de Tailwind: la que el producto reemplazó. */
const TAILWIND_PALETTE =
  /\b(?:bg|text|border|ring|from|via|to|decoration|outline|shadow|fill|stroke|divide|accent|caret|placeholder)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/g

/** Un color literal: `#c24b15`, `rgb(…)`, `hsl(…)`, `oklch(…)`. */
const LITERAL_COLOR = /#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab)\s*\(/g

function sourceFiles(dir: string): string[] {
  const absolute = join(ROOT, dir)
  return readdirSync(absolute).flatMap(entry => {
    const path = join(absolute, entry)
    if (statSync(path).isDirectory()) return sourceFiles(join(dir, entry))
    return /\.(tsx?|css)$/.test(entry) ? [join(dir, entry)] : []
  })
}

const FILES = SCANNED.flatMap(sourceFiles).filter(file => !ALLOWED.has(file))

/** Las coincidencias de `pattern` en `file`, con su número de línea. */
function offences(file: string, pattern: RegExp): string[] {
  return readFileSync(join(ROOT, file), 'utf8')
    .split('\n')
    .flatMap((line, index) => {
      const found = line.match(new RegExp(pattern.source, 'g')) ?? []
      return found.map(hit => `${file}:${index + 1} → ${hit}`)
    })
}

describe('el sistema de diseño', () => {
  it('UI-01 · no hay ningún color literal fuera de la paleta', () => {
    const found = FILES.flatMap(file => offences(file, LITERAL_COLOR))
    expect(found, 'Usá un token de app/globals.css, o agregá el que falte').toEqual([])
  })

  it('UI-02 · no se usa la paleta por defecto de Tailwind', () => {
    const found = FILES.flatMap(file => offences(file, TAILWIND_PALETTE))
    expect(found, 'Los estados son bg-ok-surface, text-danger, pill-warn…').toEqual([])
  })

  it('los tokens que el resto del sistema da por hechos existen', () => {
    // Si alguien renombra un token, esto falla acá y no repartido por la app.
    const css = readFileSync(join(ROOT, 'app/globals.css'), 'utf8')
    for (const token of [
      '--brand',
      '--link',
      '--ok',
      '--info',
      '--warn',
      '--destructive',
      '--ok-surface',
      '--info-surface',
      '--warn-surface',
      '--danger-surface',
    ]) {
      expect(css, `falta el token ${token}`).toContain(`${token}:`)
    }
  })
})
