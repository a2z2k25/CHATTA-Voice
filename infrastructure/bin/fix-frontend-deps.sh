#!/bin/bash
# Fix LiveKit Voice Assistant Frontend dependencies

set -e

FRONTEND_DIR="/home/m/Code/github.com/mbailey/voicemode/vendor/livekit-voice-assistant/voice-assistant-frontend"

echo "🔧 Fixing LiveKit Voice Assistant Frontend dependencies..."

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

cd "$FRONTEND_DIR"

echo "📁 Working directory: $(pwd)"

# Remove existing node_modules if corrupted
if [ -d "node_modules" ]; then
    echo "🗑️  Removing existing node_modules..."
    rm -rf node_modules
fi

# Remove package-lock files if they exist
if [ -f "package-lock.json" ]; then
    echo "🗑️  Removing package-lock.json..."
    rm -f package-lock.json
fi

# Install with pnpm
echo "📦 Installing dependencies with pnpm..."
if command -v pnpm >/dev/null 2>&1; then
    pnpm install
else
    echo "⚠️  pnpm not found, trying with npm..."
    npm install
fi

# Verify installation
if [ -f "node_modules/.bin/next" ]; then
    echo "✅ Dependencies installed successfully!"
    echo "📍 Next.js binary found at: node_modules/.bin/next"
else
    echo "❌ Installation failed - next binary not found"
    exit 1
fi

echo ""
echo "🎉 Frontend dependencies are now fixed!"
echo "You can now run: voice-mode livekit frontend start"