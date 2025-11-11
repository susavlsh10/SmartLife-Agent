#!/bin/bash

set -e

# Handle Ctrl+C (SIGINT)
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "Servers stopped."
    exit 0
}
trap cleanup INT

echo "================================================"
echo "SmartLife Agent - Starting with MCP Integration"
echo "================================================"

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Installing..."
    echo "   Using backend startup script instead..."
fi

# --- START BACKEND ---
echo ""
echo "🔧 Starting backend with MCP servers..."
cd backend
uv run uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
echo "✅ Backend running (PID: $BACKEND_PID)"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
cd ..

# --- START FRONTEND ---
echo ""
echo "🎨 Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend running (PID: $FRONTEND_PID)"
echo "   App: http://localhost:5173"
cd ..

echo "Both servers are running."
echo "Press Ctrl+C to stop everything."

# Keep the script alive indefinitely while processes run
while true; do
    sleep 1
done