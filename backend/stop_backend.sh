#!/bin/bash
# Stop SmartLife Agent backend server

echo "🛑 Stopping SmartLife Agent Backend..."

# Find processes on port 8000
PIDS=$(lsof -ti:8000 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "✓ No server running on port 8000"
    exit 0
fi

echo "Found process(es) on port 8000: $PIDS"

# Try graceful shutdown first
echo "Attempting graceful shutdown..."
kill $PIDS 2>/dev/null

# Wait a moment
sleep 2

# Check if still running
STILL_RUNNING=$(lsof -ti:8000 2>/dev/null)

if [ -n "$STILL_RUNNING" ]; then
    echo "⚠ Graceful shutdown failed, forcing..."
    kill -9 $STILL_RUNNING
    sleep 1
fi

# Verify
FINAL_CHECK=$(lsof -ti:8000 2>/dev/null)

if [ -z "$FINAL_CHECK" ]; then
    echo "✅ Server stopped successfully"
else
    echo "❌ Failed to stop server. Try manually:"
    echo "   sudo kill -9 $FINAL_CHECK"
fi
