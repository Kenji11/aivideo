#!/bin/bash

echo "🎬 Setting up VideoAI Studio Frontend..."
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the development server, run:"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "The app will open at http://localhost:5173"

