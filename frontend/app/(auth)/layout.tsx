/**
 * Shared layout for the authentication pages (login, reset-password).
 *
 * It exists so that anything wrapping both pages survives navigation between
 * them without a reload.
 */
export default function AuthLayoutWrapper({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
