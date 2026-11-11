#!/bin/bash
set -e

# Determinar el directorio raíz del proyecto dinámicamente
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Iniciando despliegue de Uyuni Backend..."
cd "$PROJECT_ROOT"

echo "📥 Descargando últimos cambios de Git..."
git pull origin main

echo "📦 Actualizando dependencias de Python..."
venv/bin/pip install -r requirements.txt

echo "🔄 Ejecutando migraciones de base de datos (Alembic)..."
venv/bin/alembic upgrade head

echo "♻️ Reiniciando servicio FastAPI en Systemd..."
sudo systemctl restart uyuni-backend

echo "✅ Despliegue completado con éxito!"
sudo systemctl status uyuni-backend --no-pager

