import type { Metadata } from 'next'
import Link from 'next/link'

import { readQuality } from '@/app/actions/quality'

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
 * How well the code running here is tested.
 *
 * Private, unlike `/estado`. That page answers "¿está andando?" for anybody who
 * opens it, and it is right that it needs no session. This one answers "¿qué
 * tan probado está?", which is a fact about the people who build the system:
 * theirs to share, not anyone's to read off the internet.
 *
 * The numbers are measured, never typed — `scripts/quality_snapshot.py` writes
 * them from the artefacts of a real run, and CI fails the build when the
 * committed snapshot disagrees with what the suite just did.
 */
export default async function HealthPage() {
  const quality = await readQuality()

  return (
    <main className="mx-auto max-w-2xl space-y-8 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Salud del sistema</h1>
        <p className="text-muted-foreground">
          Qué tan probado está el código que está corriendo ahora mismo.
        </p>
      </div>

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
          Esta versión no trae la medición. Se genera con <code>make quality</code> a partir de una
          corrida real de la suite, así que preferimos no decir nada antes que mostrar un número que
          nadie midió.
        </p>
      )}

      <div className="space-y-3 text-sm text-muted-foreground">
        <p>
          Los números no se escriben a mano: salen de los artefactos que dejó la suite, y una
          corrida con fallas no genera ninguno. CI vuelve a medir en cada cambio y{' '}
          <strong>falla si lo guardado no coincide</strong> con lo que la suite acaba de hacer, así
          que una medición vieja se frena en el pull request y no llega hasta acá.
        </p>
        <p>
          Los tests salteados no cuentan como verdes: no corrieron, y contarlos inflaría el número
          justo cuando alguien deshabilita un test para pasar un gate.
        </p>
      </div>

      <Link href="/estado" className="inline-block text-sm underline underline-offset-4">
        Ver el estado del servicio
      </Link>
    </main>
  )
}
