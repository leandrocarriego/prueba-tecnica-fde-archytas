import type { Config } from 'tailwindcss'

/**
 * Tailwind v4 + Mendri design system.
 *
 * Design tokens (colors, radii, shadows, fonts) and the dark-mode variant are
 * authoritative in `@mendrisoftware/ui/theme.css` (a v4 `@theme` block), imported
 * from `app/globals.css`. This config only declares the content globs to scan;
 * do NOT re-map colors here (it would shadow the package's `@theme` tokens).
 */
const config: Config = {
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
}

export default config
