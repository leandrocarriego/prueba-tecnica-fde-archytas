import Link from 'next/link'

/**
 * What somebody sees when they reach for a section that is not theirs.
 *
 * Deliberately not a redirect to the login: *no entraste* and *no te toca* are
 * different things, and sending the second one to a login form tells a person
 * their session broke when it did not. The refusal is also recorded, so the
 * owner sees it — this screen is only the half the person reads.
 */
export function NoPermission({ what }: { what?: string }) {
  return (
    <main className="mx-auto max-w-2xl px-6 py-24 text-center">
      <h1 className="mb-4 text-2xl font-semibold">No tenés permiso</h1>
      <p className="mb-8 text-muted-foreground">
        {what ? `Tu acceso no llega a ${what}.` : 'Tu acceso no llega a esta parte del sistema.'} Si
        creés que debería, pedíselo al dueño.
      </p>
      <Link href="/" className="underline underline-offset-4">
        Volver al inicio
      </Link>
    </main>
  )
}
