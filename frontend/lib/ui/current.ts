/**
 * Which of a set of links corresponds to the route being looked at.
 *
 * Two navigations ask this — la barra lateral y las pestañas de una pantalla
 * con secciones— and they have to answer it the same way, so the rule lives
 * here once. Two copies of a rule are one rule and one bug.
 *
 * The rule is **the most specific link wins**. A prefix match alone would light
 * up «Configuración» *and* «Accesos» while standing on
 * `/configuracion/accesos`, which tells the person they are in two places at
 * the same time; so a link only counts as current when no other, longer link of
 * the same set also matches.
 */

/** Whether `href` names this route or an ancestor of it. */
export function isPrefixOf(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`)
}

/** Whether `href` is the most specific link of `all` that matches the route. */
export function isCurrentPath(pathname: string, href: string, all: ReadonlyArray<string>): boolean {
  if (!isPrefixOf(pathname, href)) return false
  return !all.some(
    other => other !== href && other.length > href.length && isPrefixOf(pathname, other)
  )
}
