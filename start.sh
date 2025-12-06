#!/bin/bash

echo "🚀 Starting Personal Finance Tracker..."
echo ""

# Check if Python virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "📦 Setting up Python backend..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# Check if Node modules exist
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Setting up Node.js frontend..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "1. Terminal 1 - Start backend:"
echo "   cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "2. Terminal 2 - Start frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "Then open http://localhost:3000 in your browser"

