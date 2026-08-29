import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export async function POST() {
  const cookieStore = await cookies()

  // Eliminar cookie de token
  cookieStore.delete('access_token')

  return NextResponse.json({ message: 'Sesión cerrada' })
}
