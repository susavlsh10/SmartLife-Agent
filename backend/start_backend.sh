#!/bin/bash

# SmartLife Agent Backend Startup Script with MCP Integration
# This script uses UV for Python environment management

set -e

BACKEND_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$BACKEND_DIR"

echo "================================================"
echo "SmartLife Agent Backend - MCP Enabled"
echo "================================================"

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ UV is installed"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment with Python 3.10..."
    uv venv --python 3.10
    echo "✓ Virtual environment created"
fi

# Sync dependencies
echo "📥 Installing/syncing dependencies..."
uv sync
echo "✓ Dependencies synchronized"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Please create a .env file with your GEMINI_API_KEY"
    echo "   Example: echo 'GEMINI_API_KEY=your-key-here' > .env"
fi

# Check for Gmail OAuth credentials
if [ ! -f "gmail/google_credentials.json" ]; then
    echo "⚠️  Warning: Gmail OAuth credentials not found"
    echo "   To enable Gmail and Calendar features:"
    echo "   1. Go to https://console.cloud.google.com/"
    echo "   2. Create a new project or select existing one"
    echo "   3. Enable Gmail API and Google Calendar API"
    echo "   4. Create OAuth 2.0 credentials (Desktop app)"
    echo "   5. Download credentials and save as: gmail/google_credentials.json"
    echo ""
    echo "   The app will work without these, but Gmail/Calendar features will be disabled."
fi

# Start the server
echo ""
echo "🚀 Starting SmartLife Agent Backend..."
echo "   Server will be available at: http://localhost:8000"
echo "   API docs at: http://localhost:8000/docs"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""

# Run with UV
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
