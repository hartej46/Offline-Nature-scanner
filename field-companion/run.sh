#!/usr/bin/env bash
# Field Companion — Single command runner
# Starts:
# 1. Ollama local LLM runtime (port 11434)
# 2. FastAPI Python backend (port 8000)
# 3. React webapp (port 5173)

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "============================================================"
echo "🌱 Starting Field Companion (Touch Grass Edition)"
echo "============================================================"

# 1. Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama server..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
else
    echo "✓ Ollama is already running on port 11434"
fi

# 2. Start FastAPI Backend
echo "Starting FastAPI backend on http://0.0.0.0:8000..."
cd "$DIR/backend"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 3. Start React Webapp
echo "Starting React webapp on http://localhost:5173..."
cd "$DIR/webapp"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

# Cleanup on exit
trap "echo 'Shutting down Field Companion...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true; exit 0" INT TERM

echo ""
echo "============================================================"
echo "✅ Field Companion is running!"
echo "   Web App:  http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   LAN URL:  http://$(ipconfig getifaddr en0 2>/dev/null || echo '<mac-ip>'):8000"
echo "============================================================"
echo "Press Ctrl+C to stop all services."

wait
