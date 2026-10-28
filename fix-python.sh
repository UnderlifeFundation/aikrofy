#!/bin/bash
# fix-python.sh - Solución de PymAI para Mac con Python 3.14

echo "🔧 Solucionando incompatibilidad de Python 3.14..."

# 1. Instalar Python 3.12 si no existe
if ! command -v python3.12 &> /dev/null; then
    echo "📦 Instalando Python 3.12 vía Homebrew (estable)..."
    brew install python@3.12
else
    echo "✅ Python 3.12 ya está instalado."
fi

# 2. Recrear el venv con Python 3.12
echo "🐍 Recreando Entorno Virtual con Python 3.12..."
cd backend
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip

echo "🚀 Todo listo. Ahora puedes ejecutar ./start-local.sh y volará."
