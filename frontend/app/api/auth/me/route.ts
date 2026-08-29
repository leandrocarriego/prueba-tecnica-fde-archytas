import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('access_token')?.value

    if (!token) {
      return NextResponse.json({ detail: 'No autenticado' }, { status: 401 })
    }

    // Verificar token y obtener usuario de FastAPI
    const response = await fetch(`${API_URL}/api/v1/auth/me`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      return NextResponse.json({ detail: 'Token inválido' }, { status: 401 })
    }

    const user = await response.json()
    // El endpoint /api/v1/auth/me retorna directamente el usuario (id, email, name, is_active)
    return NextResponse.json({ user, authenticated: true })
  } catch (error) {
    console.error('Auth check error:', error)
    return NextResponse.json({ detail: 'Error al verificar autenticación' }, { status: 500 })
  }
}
