# VoiceMode Local Setup Guide: Whisper & Kokoro Integration

## Executive Summary

**Repository:** https://github.com/mbailey/voicemode  
**Feasibility:** ✅ Highly Feasible  
**Purpose:** Run a fully local voice assistant system with Whisper (STT) and Kokoro (TTS) models

---

## Table of Contents
1. [Feasibility Assessment](#feasibility-assessment)
2. [Architecture Overview](#architecture-overview)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [OpenAI Compatibility Deep Dive](#openai-compatibility-deep-dive)
5. [Performance Optimization](#performance-optimization)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Production Deployment](#production-deployment)

---

## Feasibility Assessment

The voicemode system is well-designed for local deployment with both Whisper (STT) and Kokoro (TTS) models. The repository provides:
- Automated installation tools
- OpenAI-compatible API endpoints
- Active maintenance and community support
- Docker support for containerized deployment
- Cross-platform compatibility (macOS, Linux, Windows WSL)

## Architecture Overview

```
┌─────────────────────┐
│  Claude/LLM Client  │
│    (MCP Client)     │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Voice MCP Server   │
│    (voicemode)      │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌─────────┐ ┌─────────┐
│ Whisper │ │ Kokoro  │
│  (STT)  │ │  (TTS)  │
│Port:2022│ │Port:8880│
└─────────┘ └─────────┘
```

---

## Step-by-Step Implementation

### Phase 1: System Prerequisites

#### macOS Installation
```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install core dependencies
brew install portaudio ffmpeg cmake python@3.10 espeak-ng
```

#### Linux (Ubuntu/Debian) Installation
```bash
sudo apt update
sudo apt install -y \
  python3-dev \
  libasound2-dev \
  libasound2-plugins \
  libportaudio2 \
  portaudio19-dev \
  ffmpeg \
  pulseaudio \
  pulseaudio-utils \
  espeak-ng \
  cmake \
  build-essential
```

#### Windows (WSL2) Installation
```bash
# Use Ubuntu/Debian instructions above within WSL
# Additional audio setup for WSL2 microphone access
sudo apt install -y pulseaudio libasound2-plugins
```

### Phase 2: VoiceMode Installation

```bash
# Using UV (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx voice-mode

# Alternative: Using pip
pip install voice-mode

# Alternative: Using Docker
docker run -it --rm \
  -e STT_BASE_URL="http://127.0.0.1:2022/v1" \
  -e TTS_BASE_URL="http://127.0.0.1:8880/v1" \
  --device /dev/snd \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e DISPLAY=$DISPLAY \
  ghcr.io/mbailey/voicemode:latest
```

### Phase 3: Whisper.cpp Setup (Local STT)

#### Automated Installation (Recommended)
```bash
# Using Claude Code (if integrated)
claude run install_whisper_cpp

# This will:
# - Download and compile whisper.cpp
# - Install the large-v2 model by default
# - Set up OpenAI-compatible API on port 2022
# - Configure systemd/launchd service for auto-start
```

#### Manual Installation (Alternative)
```bash
# Clone whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Build with appropriate acceleration
# macOS (Apple Silicon)
make clean && make -j WHISPER_METAL=1

# Linux with CUDA
make clean && make -j WHISPER_CUDA=1

# CPU only
make clean && make -j

# Download model
bash ./models/download-ggml-model.sh large-v2

# Run server with OpenAI-compatible endpoint
./server \
  --model models/ggml-large-v2.bin \
  --host 127.0.0.1 \
  --port 2022 \
  --inference-path "/v1/audio/transcriptions" \
  --threads 4 \
  --processors 1 \
  --convert \
  --print-progress
```

### Phase 4: Kokoro TTS Setup (Local TTS)

#### Automated Installation (Recommended)
```bash
# Using voicemode's installation tool
claude run install_kokoro_fastapi

# This will:
# - Clone kokoro-fastapi to ~/.voicemode/kokoro-fastapi
# - Install UV package manager if needed
# - Set up systemd/launchd service for auto-start
# - Start service on port 8880
```

#### Docker Installation (Alternative)
```bash
# CPU version (surprisingly fast!)
docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest

# GPU version (NVIDIA only)
docker run --gpus all -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu:latest
```

#### Manual Installation (Alternative)
```bash
# Clone Kokoro FastAPI wrapper
git clone https://github.com/remsky/Kokoro-FastAPI.git
cd Kokoro-FastAPI

# For CPU setup
cd docker/cpu
docker compose up --build

# Or direct Python installation
pip install kokoro>=0.9.2 soundfile
# Models will auto-download on first run
```

### Phase 5: Configuration

#### Environment Variables Setup
```bash
# Local Services Configuration
export STT_BASE_URL="http://127.0.0.1:2022/v1"  # Local Whisper
export TTS_BASE_URL="http://127.0.0.1:8880/v1"  # Local Kokoro
export TTS_VOICE="af_bella"  # Choose from available voices

# Optional: Model Selection
export VOICEMODE_WHISPER_MODEL="large-v2"  # or base.en for faster

# Debug & Logging
export VOICEMODE_DEBUG="true"
export VOICEMODE_SAVE_AUDIO="true"  # Saves audio to ~/voicemode_audio/
```

#### Claude Desktop Configuration
Edit config file based on your OS:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "voicemode": {
      "command": "uvx",
      "args": ["voice-mode"],
      "env": {
        "STT_BASE_URL": "http://127.0.0.1:2022/v1",
        "TTS_BASE_URL": "http://127.0.0.1:8880/v1",
        "TTS_VOICE": "af_bella"
      }
    }
  }
}
```

### Phase 6: Service Management

#### Linux (systemd)
```bash
# Check status
systemctl --user status whisper-cpp-2022
systemctl --user status kokoro-fastapi-8880

# Start/stop/restart services
systemctl --user start whisper-cpp-2022
systemctl --user start kokoro-fastapi-8880

# View logs
journalctl --user -u whisper-cpp-2022 -f
journalctl --user -u kokoro-fastapi-8880 -f
```

#### macOS (launchd)
```bash
# Check if running
launchctl list | grep whisper
launchctl list | grep kokoro

# Start/stop services
launchctl load ~/Library/LaunchAgents/com.voicemode.whisper-2022.plist
launchctl load ~/Library/LaunchAgents/com.voicemode.kokoro-8880.plist
```

### Phase 7: Testing & Validation

#### Test Whisper STT
```bash
# Test API endpoint
curl http://127.0.0.1:2022/v1/audio/transcriptions \
  -H "Content-Type: multipart/form-data" \
  -F file="@test.wav" \
  -F model="whisper-1"
```

#### Test Kokoro TTS
```bash
# Test via curl
curl -X POST http://127.0.0.1:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "Hello, this is a test of the local TTS system.",
    "voice": "af_bella"
  }' \
  --output test_output.mp3

# Web interface available at
# http://127.0.0.1:8880/web
```

#### Test Complete Integration
```bash
# In Claude with voicemode configured
/converse

# Or test individual components
/listen_for_speech
/check_audio_devices
```

---

## OpenAI Compatibility Deep Dive

### What "OpenAI Compatible" Means

**"OpenAI Compatible"** means that both Whisper.cpp and Kokoro FastAPI implement the exact same API endpoints, request/response formats, and authentication patterns as OpenAI's official APIs. This allows any application written for OpenAI's services to work with these local alternatives without code changes.

### The API Compatibility Layer

#### 1. Identical Endpoint Structure
```bash
# OpenAI's Official Endpoints
https://api.openai.com/v1/audio/transcriptions  # STT
https://api.openai.com/v1/audio/speech          # TTS

# Local Whisper.cpp (STT)
http://127.0.0.1:2022/v1/audio/transcriptions   # Same path structure

# Local Kokoro (TTS)  
http://127.0.0.1:8880/v1/audio/speech           # Same path structure
```

#### 2. Request/Response Format Parity

**Speech-to-Text (Whisper) Example:**
```python
from openai import OpenAI

# This code works with BOTH OpenAI and local Whisper
# Just change the base_url!

# Option A: OpenAI Cloud
client = OpenAI(api_key="sk-...")

# Option B: Local Whisper - NO CODE CHANGES NEEDED
client = OpenAI(
    base_url="http://127.0.0.1:2022/v1",
    api_key="not-needed"  # Local doesn't require auth
)

# Identical usage for both
audio_file = open("recording.mp3", "rb")
transcript = client.audio.transcriptions.create(
    model="whisper-1",  # Model param is accepted but ignored locally
    file=audio_file,
    response_format="json"
)
print(transcript.text)
```

**Text-to-Speech (Kokoro) Example:**
```python
# Option A: OpenAI Cloud
client = OpenAI(api_key="sk-...")

# Option B: Local Kokoro - NO CODE CHANGES NEEDED
client = OpenAI(
    base_url="http://127.0.0.1:8880/v1",
    api_key="not-needed"
)

# Identical usage for both
response = client.audio.speech.create(
    model="tts-1",  # Kokoro accepts this for compatibility
    voice="alloy",  # Maps to Kokoro voices internally
    input="Hello world!"
)
response.stream_to_file("output.mp3")
```

#### 3. Parameter Mapping & Translation

```python
# OpenAI voice names → Kokoro voice mappings
{
    "alloy": "af_alloy",      # Direct mapping
    "echo": "am_echo",         # Male voice
    "fable": "bf_fable",       # British female
    "onyx": "am_onyx",         # Deep male
    "nova": "af_nova",         # American female
    "shimmer": "af_shimmer"    # Soft female
}

# Whisper model names → Local model files
{
    "whisper-1": "ggml-large-v2.bin",
    "whisper-large": "ggml-large-v2.bin",
    "whisper-base": "ggml-base.bin"
}
```

### Why This Matters for Your Workflow

#### 1. Zero-Friction Migration
```javascript
// Your existing N8N workflow using OpenAI
const transcription = await openai.audio.transcriptions.create({
    file: audioBuffer,
    model: "whisper-1"
});

// Switch to local with ONE environment variable
// No code changes needed!
process.env.OPENAI_BASE_URL = "http://127.0.0.1:2022/v1";
```

#### 2. Intelligent Routing Capabilities
```python
# Smart router example
class IntelligentVoiceRouter:
    def route_stt_request(self, audio_size, priority):
        if audio_size < 1_000_000:  # Under 1MB
            return "http://127.0.0.1:2022/v1"  # Local for small files
        elif priority == "fast":
            return "https://api.openai.com/v1"  # Cloud for speed
        else:
            return "http://127.0.0.1:2022/v1"  # Default to local
    
    def route_tts_request(self, text_length, voice_quality):
        if voice_quality == "premium":
            return "https://api.elevenlabs.io/v1"  # Premium service
        elif text_length < 500:
            return "http://127.0.0.1:8880/v1"  # Local for short text
        else:
            return "https://api.openai.com/v1"  # Cloud for long text
```

#### 3. Fallback & Redundancy
```python
class ResilientVoiceService:
    def __init__(self):
        self.endpoints = [
            "http://127.0.0.1:2022/v1",     # Primary: Local
            "http://backup-server:2022/v1",  # Secondary: Another local
            "https://api.openai.com/v1"      # Fallback: Cloud
        ]
    
    async def transcribe_with_fallback(self, audio):
        for endpoint in self.endpoints:
            try:
                client = OpenAI(base_url=endpoint)
                return await client.audio.transcriptions.create(
                    file=audio,
                    model="whisper-1"
                )
            except Exception as e:
                continue  # Try next endpoint
        raise Exception("All endpoints failed")
```

#### 4. Cost Optimization Strategy
```python
# Automatic cost-optimized routing
class CostOptimizedRouter:
    def __init__(self):
        self.daily_openai_budget = 10.00  # $10/day
        self.openai_spent_today = 0.0
    
    def get_stt_endpoint(self, request_size):
        # Estimate cost
        estimated_cost = request_size * 0.006 / 1_000_000  # $0.006/minute
        
        if self.openai_spent_today + estimated_cost > self.daily_openai_budget:
            return "http://127.0.0.1:2022/v1"  # Use local when budget exceeded
        else:
            self.openai_spent_today += estimated_cost
            return "https://api.openai.com/v1"  # Use cloud within budget
```

### Practical Implementation Patterns

#### Pattern 1: Environment-Based Switching
```bash
# Development: Use local services
export OPENAI_BASE_URL="http://127.0.0.1:2022/v1"
export OPENAI_API_KEY="dummy"

# Staging: Use mixed mode
export OPENAI_BASE_URL="http://router.staging.internal/v1"

# Production: Use cloud with fallback
export OPENAI_BASE_URL="https://api.openai.com/v1"
export FALLBACK_BASE_URL="http://127.0.0.1:2022/v1"
```

#### Pattern 2: Load Balancing
```nginx
# nginx.conf for load balancing between multiple local instances
upstream whisper_backends {
    least_conn;
    server 127.0.0.1:2022 weight=3;
    server 127.0.0.1:2023 weight=2;
    server 127.0.0.1:2024 weight=1;
}

server {
    listen 2022;
    location /v1/audio/transcriptions {
        proxy_pass http://whisper_backends;
    }
}
```

#### Pattern 3: A/B Testing
```python
class ABTestingVoiceService:
    def __init__(self):
        self.endpoints = {
            "control": "https://api.openai.com/v1",
            "experiment": "http://127.0.0.1:2022/v1"
        }
    
    def get_endpoint(self, user_id):
        # 50/50 split based on user ID
        if hash(user_id) % 2 == 0:
            return self.endpoints["control"]
        return self.endpoints["experiment"]
```

### Integration with Your Stack

#### NextJS Application
```typescript
// lib/voice-service.ts
class VoiceService {
  private baseUrl: string;
  
  constructor() {
    // Automatically use local in development
    this.baseUrl = process.env.NODE_ENV === 'development' 
      ? 'http://127.0.0.1:2022/v1'
      : process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1';
  }
  
  async transcribe(audioBlob: Blob): Promise<string> {
    const formData = new FormData();
    formData.append('file', audioBlob);
    formData.append('model', 'whisper-1');
    
    const response = await fetch(`${this.baseUrl}/audio/transcriptions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`
      },
      body: formData
    });
    
    const data = await response.json();
    return data.text;
  }
}
```

#### N8N Workflow Node
```json
{
  "name": "Transcribe Audio",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "={{$env.STT_BASE_URL}}/audio/transcriptions",
    "authentication": "predefinedCredentialType",
    "nodeCredentialType": "openAiApi",
    "sendBody": true,
    "contentType": "multipart-form-data",
    "bodyParameters": {
      "parameters": [
        {
          "name": "file",
          "parameterType": "formBinaryData",
          "inputDataFieldName": "audio"
        },
        {
          "name": "model",
          "value": "whisper-1"
        }
      ]
    }
  }
}
```

### Key Benefits for Agentic Workflows

1. **Vendor Independence**: Your agents aren't locked to OpenAI's pricing or availability
2. **Hybrid Flexibility**: Use local for development/testing, cloud for production
3. **Cost Control**: Route expensive operations to local, premium features to cloud
4. **Privacy Options**: Sensitive audio never leaves your infrastructure
5. **Performance Tuning**: Optimize local models for your specific use case
6. **Compliance Ready**: Meet data residency requirements by keeping processing local

---

## Performance Optimization

### Hardware Recommendations

**Minimum Requirements:**
- CPU: 4 cores, AVX2 support
- RAM: 8GB
- Storage: 10GB for models

**Optimal Setup:**
- Apple Silicon Mac (M1/M2/M3) - Metal acceleration
- NVIDIA GPU (RTX 3060+) - CUDA acceleration
- 16GB+ RAM
- NVMe SSD for model storage

### Model Selection Strategy

**Whisper Models (Speed vs Accuracy):**
- `tiny.en` - 1s latency, good for commands
- `base.en` - 2s latency, balanced
- `small.en` - 3s latency, better accuracy
- `large-v2` - 5s latency, best accuracy

**Kokoro Voice Selection:**
```python
# Single voice
voice="af_bella"

# Voice blending for unique characteristics
voice="af_bella:0.7,af_sarah:0.3"
```

---

## Troubleshooting Guide

### Common Issues & Solutions

**1. No Microphone Access:**
```bash
# Check permissions
# macOS: System Preferences > Security & Privacy > Microphone
# Linux: Check pulseaudio
pactl info
```

**2. Port Conflicts:**
```bash
# Check if ports are in use
lsof -i :2022
lsof -i :8880

# Change ports in environment variables
export STT_BASE_URL="http://127.0.0.1:3022/v1"
export TTS_BASE_URL="http://127.0.0.1:3880/v1"
```

**3. Model Download Issues:**
```bash
# Manual model download for Whisper
cd ~/.whisper
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v2.bin

# Kokoro models auto-download, but can be pre-fetched
python -c "from kokoro import KPipeline; KPipeline(lang_code='a')"
```

---

## Production Deployment

### Docker Compose Stack

```yaml
version: '3.8'

services:
  whisper:
    image: ghcr.io/your-org/whisper-cpp:latest
    ports:
      - "2022:2022"
    volumes:
      - ./models:/models
    command: >
      ./server
      --model /models/ggml-large-v2.bin
      --host 0.0.0.0
      --port 2022
    restart: unless-stopped

  kokoro:
    image: ghcr.io/remsky/kokoro-fastapi-cpu:latest
    ports:
      - "8880:8880"
    environment:
      - KOKORO_VOICES=af_bella,af_sky,am_adam
    restart: unless-stopped

  voicemode:
    image: ghcr.io/mbailey/voicemode:latest
    environment:
      - STT_BASE_URL=http://whisper:2022/v1
      - TTS_BASE_URL=http://kokoro:8880/v1
    depends_on:
      - whisper
      - kokoro
    restart: unless-stopped
```

### Docker Compose with Smart Routing

```yaml
version: '3.8'

services:
  voice-router:
    image: nginx:alpine
    volumes:
      - ./router.conf:/etc/nginx/nginx.conf
    environment:
      - ROUTING_MODE=${ROUTING_MODE:-local_first}
    ports:
      - "8000:8000"
    
  whisper-local:
    image: whisper-cpp:latest
    ports:
      - "2022:2022"
      
  kokoro-local:
    image: kokoro-fastapi:latest
    ports:
      - "8880:8880"
      
  app:
    image: your-app:latest
    environment:
      # Point to router instead of direct services
      - OPENAI_BASE_URL=http://voice-router:8000/v1
```

---

## Key Advantages of This Setup

1. **Complete Privacy** - All processing happens locally
2. **No API Costs** - After initial setup, zero ongoing costs
3. **Low Latency** - Direct local processing, no network delays
4. **Customizable** - Tune models, voices, and processing parameters
5. **Offline Capable** - Works without internet connection
6. **OpenAI Compatible** - Drop-in replacement for OpenAI APIs

This system is production-ready and actively maintained. The voicemode repository shows recent updates and strong community support, making it a reliable choice for your agentic workflow design needs.

---

## Additional Resources

- **VoiceMode Repository**: https://github.com/mbailey/voicemode
- **Whisper.cpp**: https://github.com/ggerganov/whisper.cpp
- **Kokoro FastAPI**: https://github.com/remsky/Kokoro-FastAPI
- **Kokoro Model**: https://huggingface.co/hexgrad/Kokoro-82M
- **VoiceMode Documentation**: https://voice-mode.readthedocs.io/

---

*Document generated: January 2025*
*Author: Andrew Zellinger (via Claude)*