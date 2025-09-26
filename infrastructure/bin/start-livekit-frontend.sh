#!/bin/bash
# Start the LiveKit Voice Assistant Frontend

FRONTEND_DIR="/home/m/Code/github.com/mbailey/voicemode/vendor/livekit-voice-assistant/voice-assistant-frontend"

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "Error: Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    pnpm install
fi

# Start the frontend
echo "Starting LiveKit Voice Assistant Frontend..."
echo "Access at: http://localhost:3000"
echo "Password: Check .env.local for LIVEKIT_ACCESS_PASSWORD"
echo ""
pnpm dev