import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

/**
 * El sistema de diseño, verificado por un test que rompe el build.
 *
 * La constitución lo dice para las fronteras entre módulos y vale igual acá:
 * *cualquier principio que dependa sólo de que alguien lo lea es una aspiración,
 * no una regla*. Estos son los `UI-*` de `CONVENTIONS.md` que se pueden decidir
 * leyendo el código, y por eso los decide este archivo y no una revisión a ojo:
 *
 * - `UI-01` — ningún color literal en la UI.
 * - `UI-02` — ninguna clase de la paleta por defecto de Tailwind.
 * - `UI-05` — como mucho un naranja por pantalla, y ninguno en las pantallas
 *   donde se decide.
 * - `UI-03` — la píldora sale de `Badge`, no de la clase escrita a mano.
 * - `UI-04` — la plata pasa por `<Money>`, no por `money()` suelto.
 * - `UI-10` — un solo tema, y es el claro.
 *
 * Todo por **análisis estático del texto del código**: no hace falta renderizar,
 * y por eso alcanza también a las veintiocho pantallas que ningún test monta.
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

const ALL_FILES = SCANNED.flatMap(sourceFiles)
const FILES = ALL_FILES.filter(file => !ALLOWED.has(file))

const read = (file: string): string => readFileSync(join(ROOT, file), 'utf8')

/** Las coincidencias de `pattern` en `file`, con su número de línea. */
function offences(file: string, pattern: RegExp): string[] {
  return read(file)
    .split('\n')
    .flatMap((line, index) => {
      const found = line.match(new RegExp(pattern.source, 'g')) ?? []
      return found.map(hit => `${file}:${index + 1} → ${hit}`)
    })
}

/*
 * --- El presupuesto de naranja (`UI-05`, `RF-11`, `RF-21`) -------------------
 *
 * Una pantalla no es su `page.tsx`: el botón naranja casi siempre vive tres
 * componentes más adentro. Por eso cada pantalla se mide sobre **su árbol de
 * imports `@/`**, que es lo que una persona ve cuando la abre.
 */

/** Dónde se declara el naranja: `variant="brand"`, o el mismo valor en un objeto. */
const BRAND = /variant\s*=\s*"brand"|variant:\s*'brand'/g

/**
 * La ventana de confirmación no gasta el presupuesto de la pantalla.
 *
 * Es la excepción que la spec firmó el 2026-08-31: un diálogo que pregunta
 * «¿seguro?» *es* la decisión, aparece sobre la pantalla y no compite con
 * nada, porque mientras está abierto no hay otra cosa que apretar. Sin esta
 * excepción, `/calendario` —que es pantalla de decisión— daría uno por un
 * diálogo que la 006 ya había dejado en `main`.
 */
const OUTSIDE_THE_BUDGET = new Set(['components/ui/confirm-dialog.tsx'])

/** Las nueve rutas donde se decide, y donde el naranja tiene prohibido aparecer. */
const DECISION_ROUTES = [
  'revision',
  'calendario',
  'facturas/revision',
  'facturas/incidentes',
  'ventas/revision',
  'proveedores/grafias',
  'rubros/sin-clasificar',
  'rubros/equivalencias',
  'acciones',
]

const PRIVATE_PAGES = ALL_FILES.filter(
  file => file.startsWith(join('app', '(private)')) && file.endsWith('page.tsx')
)

/** La ruta que sirve un `page.tsx`, tal como se escribe en la barra del navegador. */
function routeOf(page: string): string {
  return page
    .replace(join('app', '(private)'), '')
    .replace(/\/page\.tsx$/, '')
    .replace(/^\//, '')
}

/** El archivo al que apunta un import `@/…`, con su extensión resuelta. */
function resolve(specifier: string): string | null {
  const base = specifier.replace(/^@\//, '')
  for (const candidate of [
    base,
    `${base}.tsx`,
    `${base}.ts`,
    join(base, 'index.tsx'),
    join(base, 'index.ts'),
  ]) {
    const path = join(ROOT, candidate)
    if (existsSync(path) && statSync(path).isFile()) return candidate
  }
  return null
}

/** Todo lo del proyecto que una pantalla arrastra, ella incluida. */
function importTree(entry: string): string[] {
  const seen = new Set<string>()
  const pending = [entry]
  while (pending.length > 0) {
    const file = pending.pop() as string
    if (seen.has(file) || OUTSIDE_THE_BUDGET.has(file)) continue
    seen.add(file)
    for (const match of read(file).matchAll(/from '(@\/[^']+)'/g)) {
      const target = resolve(match[1])
      if (target && !seen.has(target)) pending.push(target)
    }
  }
  return [...seen]
}

/** Cada naranja que se ve al abrir una pantalla, con el archivo que lo pone. */
function brandUses(page: string): string[] {
  return importTree(page).flatMap(file => offences(file, BRAND))
}

/*
 * --- Las dos listas que se vacían solas -------------------------------------
 *
 * Los dos chequeos que siguen describen **el final** de la migración, y son
 * falsos el día que se escriben: hay dos archivos que dibujan la píldora a mano
 * y trece que le piden el string a `lib/format`. Nacen, entonces, con esos
 * archivos sembrados como excepción, y **cada pantalla que se migra saca los
 * suyos en el mismo commit**. Cuando la lista queda vacía, la migración terminó.
 *
 * No se agrega ninguna entrada después de este commit: sembrarlas es un acto
 * único, con el árbol de hoy a la vista. Una entrada nueva significaría una
 * pantalla escrita sin las primitivas, que es lo que estos chequeos existen
 * para frenar.
 */

/**
 * La píldora es de `Badge`. `globals.css` es donde vive el estilo.
 *
 * Busca la **clase**, no la palabra: los modificadores siempre, y `pill` sola
 * únicamente cuando está adentro de comillas, que es como se escribe una clase.
 * Sin eso, cualquier comentario que nombre la píldora sería un hallazgo, y un
 * chequeo que grita por prosa se termina desactivando.
 */
const PILL = /\bpill-(?:ok|info|warn|danger|draft)\b|(?<=['"`])pill(?=[\s'"`])/g
const PILL_HOME = new Set(['components/ui/badge.tsx', 'app/globals.css'])

/**
 * Vacía, y ése era el punto.
 *
 * Nació con los dos archivos que dibujaban `.pill` a mano —la tabla de accesos y
 * el registro de actividad— y los dos salieron en la tarea 37, en el mismo
 * commit que los migró. Se deja declarada y vacía a propósito: si alguna vez
 * hay que volver a agregar una entrada acá, eso es la conversación que este
 * chequeo existe para provocar.
 */
const PILL_BY_HAND = new Set<string>([])

/** El formateo de plata, fechas y decimales sale de `<Money>`, `<Day>`, `<Decimal>`. */
const RAW_FORMAT = /import\s*\{[^}]*\b(?:money|decimal|day)\b[^}]*\}\s*from '@\/lib\/format'/g
const FORMAT_HOME = new Set(['components/ui/amount.tsx'])

/**
 * Lo que le pide el string a `lib/format`, y no el elemento.
 *
 * Empezó con trece archivos —los que había el día que se escribió este
 * chequeo— y cada tarea de pantalla fue sacando los suyos en el mismo commit
 * que los migraba. Queda **uno**, y no es una pendiente: es la excepción que el
 * chequeo admite para siempre.
 *
 * `components/categories/CategoryList.tsx` también importa de ahí y nunca estuvo
 * en la lista: sólo usa `count`, que no es plata ni fecha y que este chequeo no
 * gobierna.
 */
const FORMAT_BY_HAND = new Set([
  /*
   * `CalendarGrid` es una excepción **permanente**, no una pendiente: usa
   * `day()` y `money()` para un `title` y un `aria-label`, que no pueden llevar
   * un elemento adentro. Todo lo que se ve en pantalla ya pasa por `<Day>` y
   * `<Money>`.
   */
  'components/purchases/CalendarGrid.tsx',
])

/** Un solo tema, y es el claro (`UI-10`, `RF-20`). */
const TWO_THEMES = /\bdark:[a-z[]|prefers-color-scheme/g

/**
 * La cabecera de `globals.css` cuenta por qué se sacó el tema oscuro, y para
 * contarlo lo nombra. Se saltea el comentario de cabecera, y sólo ése.
 */
function outsideTheHeader(file: string, pattern: RegExp): string[] {
  const found = offences(file, pattern)
  if (file !== 'app/globals.css') return found
  const source = read(file)
  const header = source.slice(0, source.indexOf('*/')).split('\n').length
  return found.filter(hit => Number(hit.split(':')[1]) > header)
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
    const css = read('app/globals.css')
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
      '--muted-ink',
      '--draft-border',
    ]) {
      expect(css, `falta el token ${token}`).toContain(`${token}:`)
    }
  })

  it('UI-05 · ninguna pantalla gasta más de un naranja', () => {
    const found = PRIVATE_PAGES.flatMap(page => {
      const uses = brandUses(page)
      return uses.length > 1 ? [`${routeOf(page)} usa ${uses.length}: ${uses.join(' · ')}`] : []
    })
    const why = 'El naranja es la tarea principal de la pantalla; el resto va en contorno'
    expect(found, why).toEqual([])
  })

  it('RF-21 · las pantallas donde se decide no tienen ningún naranja', () => {
    const found = PRIVATE_PAGES.filter(page => DECISION_ROUTES.includes(routeOf(page))).flatMap(
      page => brandUses(page).map(use => `${routeOf(page)} → ${use}`)
    )
    const why = 'Una lista de decisiones no tiene una decisión más importante que otra'
    expect(found, why).toEqual([])
  })

  it('UI-03 · la píldora sale de Badge, no de la clase escrita a mano', () => {
    const found = FILES.filter(file => !PILL_HOME.has(file) && !PILL_BY_HAND.has(file)).flatMap(
      file => offences(file, PILL)
    )
    const why = 'Usá <Badge tone="…">, que es lo que hace que el estado sea el mismo'
    expect(found, why).toEqual([])
  })

  it('UI-04 · la plata pasa por <Money>, no por money() suelto', () => {
    const found = FILES.filter(file => !FORMAT_HOME.has(file) && !FORMAT_BY_HAND.has(file)).flatMap(
      file => offences(file, RAW_FORMAT)
    )
    const why = 'money() devuelve un string y cada pantalla elige su tipografía: usá <Money>'
    expect(found, why).toEqual([])
  })

  it('UI-10 · hay un solo tema, y es el claro', () => {
    const found = FILES.concat('app/globals.css').flatMap(file =>
      outsideTheHeader(file, TWO_THEMES)
    )
    expect(found, 'Un tema que se enciende solo y se ve mal es peor que no tenerlo').toEqual([])
  })
})
