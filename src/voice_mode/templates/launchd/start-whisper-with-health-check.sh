#!/bin/bash
# Start Whisper service and wait for it to be ready

# Start the service in the background
"{WHISPER_BIN}" --host 0.0.0.0 --port {WHISPER_PORT} --model "{MODEL_FILE}" &
SERVICE_PID=$!

# Wait for the health endpoint to respond
echo "Starting Whisper service (PID: $SERVICE_PID)..."
while ! curl -sf http://127.0.0.1:{WHISPER_PORT}/health >/dev/null 2>&1; do
    # Check if process is still running
    if ! kill -0 $SERVICE_PID 2>/dev/null; then
        echo "Whisper service failed to start"
        exit 1
    fi
    echo "Waiting for Whisper to be ready..."
    sleep 1
done

echo "Whisper is ready and listening on port {WHISPER_PORT}!"

# Wait for the service process
wait $SERVICE_PID