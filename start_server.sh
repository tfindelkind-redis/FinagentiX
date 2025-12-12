#!/bin/bash
# Start FinagentiX API Server

set -e

echo "🚀 Starting FinagentiX API Server..."
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please create one from .env.template"
    echo "   cp .env.template .env"
    echo "   Then edit .env with your credentials"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Start the server
echo "🌐 Starting server at http://localhost:8000"
echo "📚 API docs at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
