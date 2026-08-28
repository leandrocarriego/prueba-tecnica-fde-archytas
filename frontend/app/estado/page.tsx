import type { Metadata } from 'next'
import Link from 'next/link'

import { ApiStatusCard } from '@/components/status/ApiStatusCard'
import { Button } from '@/components/ui/button'
import { probeHealth } from '@/lib/health'

/**
 * Public status page. It is the only page anyone can open without a session,
 * and the one to open when the platform seems down: it says whether the API is
 * answering before anybody tries to log in.
 *
 * A Server Component on purpose. The first reading is rendered on the server,
 * so the page arrives already answering the question instead of flashing a
 * spinner, and it still says something useful with JavaScript disabled. The
 * card takes over from there and keeps re-checking.
 */

// Nothing about a health check may be cached, at any layer.
export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Estado del servicio · Plataforma Cordillera',
  description: 'Estado en vivo de la API de la Plataforma Cordillera.',
}

export default async function StatusPage() {
  const initial = await probeHealth()

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-6">
      <header className="space-y-2 text-center">
        <h1 className="text-3xl font-bold tracking-tight">Plataforma Cordillera</h1>
        <p className="text-sm text-muted-foreground">Ferretería Industrial Cordillera SRL</p>
      </header>

      <ApiStatusCard initial={initial} />

      <Button asChild variant="ghost" size="sm">
        <Link href="/login">Ingresar a la plataforma</Link>
      </Button>
    </main>
  )
}
