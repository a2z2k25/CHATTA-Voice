#!/bin/bash
# Start Kokoro service and wait for it to be ready

# Start the service in the background
exec "{START_SCRIPT}" &
SERVICE_PID=$!

# Wait for the health endpoint to respond
echo "Starting Kokoro service (PID: $SERVICE_PID)..."
while ! curl -sf http://127.0.0.1:{KOKORO_PORT}/health >/dev/null 2>&1; do
    # Check if process is still running
    if ! kill -0 $SERVICE_PID 2>/dev/null; then
        echo "Kokoro service failed to start"
        exit 1
    fi
    echo "Waiting for Kokoro to be ready..."
    sleep 1
done

echo "Kokoro is ready and listening on port {KOKORO_PORT}!"

# Wait for the service process
wait $SERVICE_PID