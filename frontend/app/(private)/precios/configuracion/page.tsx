import { redirect } from 'next/navigation'

/**
 * This screen no longer exists, and its absence is a business rule.
 *
 * 001 put the two parameters of the price update here, next to the feature that
 * reads them. The spec signed for 003 says the opposite in as many words: every
 * configurable parameter lives on one screen, and there are none hidden inside
 * the screen of the functionality that uses them. So the two moved to
 * `/configuracion` along with the other five.
 *
 * A redirect rather than a deletion because the address was handed out — it is
 * in the menu somebody bookmarked and in the docs of 001. Whoever follows it
 * lands on the panel instead of on a 404 they would have to ask about.
 */
export default function MovedToTheParametersPanel() {
  redirect('/configuracion')
}
