import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('access_token')?.value

    if (!token) {
      return NextResponse.json({ detail: 'No autenticado' }, { status: 401 })
    }

    const body = await request.json()
    const { current_password, new_password } = body

    if (!current_password || !new_password) {
      return NextResponse.json(
        { detail: 'Contraseña actual y nueva contraseña son requeridas' },
        { status: 400 }
      )
    }

    // Llamar a FastAPI
    const response = await fetch(`${API_URL}/api/v1/auth/password/change`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        current_password,
        new_password,
      }),
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || 'Error al cambiar la contraseña' },
        { status: response.status }
      )
    }

    return NextResponse.json({ message: 'Contraseña cambiada exitosamente' })
  } catch (error) {
    console.error('Change password error:', error)
    return NextResponse.json({ detail: 'Error interno del servidor' }, { status: 500 })
  }
}
