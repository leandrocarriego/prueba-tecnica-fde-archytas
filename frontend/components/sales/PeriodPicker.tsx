import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

/**
 * El período de **un** corte, sin tocar el de los demás (RF-05 de 009).
 *
 * Es un `form` con `method="get"` y nada de JavaScript: navegar cambia la URL,
 * y la pantalla se rearma en el servidor. Lo que hace que el corte de al lado no
 * se mueva son los campos ocultos: un `GET` reemplaza **toda** la query, así que
 * el período del otro corte tiene que viajar con éste para sobrevivir.
 *
 * Sin eso, cambiar el período de los precios reseteaba el de la facturación —
 * que es exactamente lo que RF-05 dice que no puede pasar.
 *
 * La forma es la del control de período de la guía visual (`3b`): un bloque
 * compacto, arriba a la derecha del corte que gobierna, con los rótulos en
 * versalita y el botón en contorno. El naranja no está acá: elegir un período
 * no es la decisión de esta pantalla.
 */
export function PeriodPicker({
  fromName,
  toName,
  from,
  to,
  keep,
  /** Qué corte gobierna, para quien lo lee con un lector de pantalla. */
  label,
}: {
  fromName: string
  toName: string
  from?: string
  to?: string
  keep: Record<string, string | undefined>
  label: string
}) {
  return (
    <form method="get" aria-label={label} className="flex flex-wrap items-end gap-2">
      {Object.entries(keep).map(([name, value]) =>
        value ? <input key={name} type="hidden" name={name} value={value} /> : null
      )}
      <label className="flex flex-col gap-1.5">
        <span className="section-label">Desde</span>
        <Input
          type="date"
          name={fromName}
          defaultValue={from ?? ''}
          className="h-9 w-auto text-[13px]"
        />
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="section-label">Hasta</span>
        <Input
          type="date"
          name={toName}
          defaultValue={to ?? ''}
          className="h-9 w-auto text-[13px]"
        />
      </label>
      <Button type="submit" variant="outline" size="sm" className="h-9">
        Ver período
      </Button>
    </form>
  )
}
