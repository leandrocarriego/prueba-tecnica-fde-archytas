#!/bin/bash
# Bootstrap the Plataforma Cordillera development environment.
set -e

echo "🔩 Configurando la Plataforma Cordillera..."

faltante=0
for cmd in docker uv npm; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "❌ Falta $cmd. Instalalo antes de continuar."
        faltante=1
    fi
done
if ! docker compose version &> /dev/null; then
    echo "❌ Falta el plugin 'docker compose'."
    faltante=1
fi
[ "$faltante" -eq 1 ] && exit 1

if [ ! -f .env ]; then
    if [ ! -f .env.example ]; then
        echo "❌ No existe .env.example. No puedo generar el .env."
        exit 1
    fi
    cp .env.example .env
    echo "📝 .env creado a partir de .env.example."
    echo "   Completá las credenciales del portal (PORTAL_USER, PORTAL_PASSWORD) antes de extraer."
else
    echo "✅ .env ya existe, no lo toco."
fi

echo ""
echo "✅ Prerrequisitos verificados."
echo ""
echo "Siguientes pasos:"
echo "  1. make dev                              # Postgres + RabbitMQ"
echo "  2. cd backend && uv sync"
echo "  3. uv run playwright install chromium    # una sola vez"
echo "  4. uv run alembic upgrade head"
echo "  5. uv run uvicorn app.main:app --reload"
echo "  6. cd frontend && npm install && npm run dev"
