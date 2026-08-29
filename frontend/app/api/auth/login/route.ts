import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email, password } = body

    if (!email || !password) {
      return NextResponse.json({ detail: 'Email y contraseña son requeridos' }, { status: 400 })
    }

    // Llamar a FastAPI
    const response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || 'Error al iniciar sesión' },
        { status: response.status }
      )
    }

    // Guardar token en httpOnly cookie
    const cookieStore = await cookies()
    cookieStore.set('access_token', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 30 * 60, // 30 minutos
      path: '/',
    })

    // Retornar usuario (sin token)
    return NextResponse.json({
      user: data.user,
    })
  } catch (error) {
    console.error('Login error:', error)
    return NextResponse.json({ detail: 'Error interno del servidor' }, { status: 500 })
  }
}
