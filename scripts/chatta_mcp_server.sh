#!/bin/bash
# CHATTA MCP Server Launcher
cd "."
export STT_BASE_URL="http://localhost:8880/v1"
export TTS_BASE_URL="http://localhost:7888/v1"
export PREFER_LOCAL="true"
export OPENAI_API_KEY="dummy-key-for-local"
export PYTHONPATH="."
export PYTHONUNBUFFERED=1
# Suppress Python warnings that would break JSON-RPC
export PYTHONWARNINGS="ignore"

# Use the venv Python
exec ./.venv/bin/python -m voice_mode.server