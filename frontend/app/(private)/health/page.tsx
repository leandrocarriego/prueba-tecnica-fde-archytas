import type { Metadata } from 'next'

import { readQuality } from '@/app/actions/quality'
import { ApiStatusCard } from '@/components/status/ApiStatusCard'
import { probeHealth } from '@/lib/health'

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Salud del sistema · Plataforma Cordillera',
}

const PERCENT = new Intl.NumberFormat('es-AR', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

/**
 * The one page about the system itself: whether it is answering, and how well
 * the code answering is tested.
 *
 * It needs a session. That is a real trade and worth naming: this page can no
 * longer be opened by somebody who cannot log in, which is exactly when a
 * public status page earns its keep. What answers that question now is the
 * container's own healthcheck against the API's public `/health`, which is
 * where an orchestrator was always going to look anyway.
 *
 * The numbers are measured, never typed — `scripts/quality_snapshot.py` writes
 * them from the artefacts of a real run, and CI fails the build when the
 * committed snapshot disagrees with what the suite just did.
 */
export default async function HealthPage() {
  const [probe, quality] = await Promise.all([probeHealth(), readQuality()])

  return (
    <main className="mx-auto max-w-2xl space-y-8 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Salud del sistema</h1>
        <p className="text-muted-foreground">
          Si la plataforma está respondiendo, y qué tan probado está el código que la corre.
        </p>
      </div>

      <ApiStatusCard initial={probe} />

      <section className="space-y-4">
        <h2 className="font-medium">Cómo está probado</h2>

        {quality ? (
          <dl className="grid grid-cols-2 gap-4">
            <div className="rounded border p-4">
              <dt className="text-sm text-muted-foreground">Tests en verde</dt>
              <dd className="text-3xl font-semibold">{quality.tests}</dd>
            </div>
            <div className="rounded border p-4">
              <dt className="text-sm text-muted-foreground">Cobertura</dt>
              <dd className="text-3xl font-semibold">{PERCENT.format(quality.coverage / 100)}</dd>
            </div>
          </dl>
        ) : (
          <p className="rounded border border-dashed p-4 text-sm text-muted-foreground">
            Esta versión no trae la medición. Se genera con <code>make quality</code> a partir de
            una corrida real de la suite, así que preferimos no decir nada antes que mostrar un
            número que nadie midió.
          </p>
        )}

        <div className="space-y-3 text-sm text-muted-foreground">
          <p>
            Los números no se escriben a mano: salen de los artefactos que dejó la suite, y una
            corrida con fallas no genera ninguno. CI vuelve a medir en cada cambio y{' '}
            <strong>falla si lo guardado no coincide</strong> con lo que la suite acaba de hacer,
            así que una medición vieja se frena en el pull request y no llega hasta acá.
          </p>
          <p>
            Los tests salteados no cuentan como verdes: no corrieron, y contarlos inflaría el número
            justo cuando alguien deshabilita un test para pasar un gate.
          </p>
        </div>
      </section>
    </main>
  )
}
