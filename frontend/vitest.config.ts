/**
 * Los tests de pantalla del frontend.
 *
 * Existen por lo que ningún test de backend puede demostrar: que el control de
 * mes arma la ventana correcta y que un día cargado recorta e informa cuántos
 * hay (RF-05, RF-08). El backend no sabe nada de ninguna de las dos cosas.
 *
 * `jsdom` y no un navegador: acá se prueba lo que la pantalla decide, no cómo
 * se ve. Lo que sólo se puede ver —la pantalla en un teléfono, RF-41— se
 * verifica a mano, y está dicho en `docs/specs/006-due-date-calendar/`.
 */
import { fileURLToPath } from 'node:url'

import { defineConfig } from 'vitest/config'

export default defineConfig({
  // Sin el plugin de React: vitest transforma el JSX con esbuild y el runtime
  // automático. El plugin trae su propia copia de vite y las dos se pelean por
  // los tipos de rollup, que es un problema de instalación y no del producto.
  esbuild: { jsx: 'automatic' },
  resolve: {
    alias: { '@': fileURLToPath(new URL('.', import.meta.url)) },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}'],
    // El primer render paga el arranque de React y de jsdom, y en una máquina
    // cargada pasa los 5 s por omisión. El límite está para atrapar un test
    // colgado, no para medir el arranque del entorno.
    testTimeout: 20_000,
  },
})
