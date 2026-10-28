#!/bin/bash

# Aikrofy Unified Local Startup Script
# This script handles EVERYTHING: Front-end, Back-end environment, and PM2.

echo "🚀 Starting Aikrofy Unified Environment..."

# 1. Frontend Preparation
echo "⚛️ Preparing Frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
cd ..

# 2. Backend Preparation
echo "🐍 Preparing Backend (Python Venv)..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
# Use python3 -m pip to ensure compatibility with Mac system paths
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
echo "🗄️ Synchronizing Database Schema & RAG Knowledge Base..."
python3 sync_db.py || true
cd ..

# 3. WhatsApp Preparation
echo "📱 Preparing WhatsApp Microservice..."
cd api-whatsapp
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
cd ..

# 3c. Landing Page Generator Microservice (screenshot-to-code)
echo "🤖 Preparing Landing Page Generator (screenshot-to-code)..."
if [ -d "screenshot-to-code/backend" ]; then
    cd screenshot-to-code/backend
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    python3 -m pip install --upgrade pip -q
    python3 -m pip install -r pyproject.toml 2>/dev/null || python3 -m pip install fastapi uvicorn openai anthropic google-generativeai httpx python-dotenv 2>/dev/null || true
    deactivate
    cd ../..
else
    echo "⚠️ Warning: screenshot-to-code/backend directory not found. Skipping."
fi

# 4. Port Cleanup
echo "🧹 Cleaning up old stray processes..."
for PORT in 3010 3011 5010 5015 6380; do
    PID=$(lsof -ti :$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null
    fi
done
pkill -f "celery -A config celery_app" 2>/dev/null
pkill -f "redis-server" 2>/dev/null

# 4. Launch with PM2
echo "🔄 Launching cluster with PM2..."
pm2 restart ecosystem.config.js || pm2 start ecosystem.config.js

echo ""
pm2 status
echo ""
echo "✅ Aikrofy & Landing Gen are running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Frontend (PyME):    http://localhost:3010"
echo "  Backend (API):      http://localhost:5010"
echo "  WhatsApp Micro:     http://localhost:3011"
echo "  Landing Gen AI:     http://localhost:5015"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 Monitor logs with: pm2 logs"
echo "🛑 Stop all with:    pm2 stop all"
