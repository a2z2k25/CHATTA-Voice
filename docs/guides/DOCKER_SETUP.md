# CHATTA Docker Voice Services Setup

## Overview
CHATTA provides containerized voice services for speech-to-text (STT), text-to-speech (TTS), and real-time WebRTC communication through Docker containers. This setup enables local, privacy-focused voice AI capabilities without cloud dependencies.

## Services

### 1. Whisper STT (Speech-to-Text)
- **Container**: chatta-whisper
- **Port**: 8880
- **Model**: OpenAI Whisper base model
- **API**: OpenAI-compatible transcription endpoint

### 2. Kokoro TTS (Text-to-Speech)
- **Container**: chatta-kokoro
- **Port**: 7888
- **Model**: Kokoro ONNX v0.87
- **API**: OpenAI-compatible speech synthesis endpoint
- **Voices**: af_alloy, af_aoede, af_bella, and more

### 3. LiveKit (WebRTC)
- **Container**: chatta-livekit
- **Ports**: 
  - 7880-7881 (TCP)
  - 50000-50100 (UDP)
- **Purpose**: Real-time voice communication

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- 4GB+ free disk space for models
- Ports 7880-7881, 7888, 8880, and 50000-50100 available

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d whisper
docker-compose up -d kokoro
docker-compose up -d livekit

# View logs
docker-compose logs -f whisper
docker-compose logs -f kokoro
docker-compose logs -f livekit

# Stop services
docker-compose down
```

### Health Checks

```bash
# Check Whisper STT
curl http://localhost:8880/health

# Check Kokoro TTS
curl http://localhost:7888/health

# Check LiveKit (no HTTP endpoint, check process)
docker ps | grep chatta-livekit
```

## API Usage

### Whisper STT - Transcribe Audio

```bash
# Transcribe audio file
curl -X POST http://localhost:8880/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "model=whisper-1"
```

**Python Example:**
```python
import requests

with open("audio.wav", "rb") as f:
    files = {"file": ("audio.wav", f, "audio/wav")}
    data = {"model": "whisper-1"}
    response = requests.post(
        "http://localhost:8880/v1/audio/transcriptions",
        files=files,
        data=data
    )
    print(response.json()["text"])
```

### Kokoro TTS - Generate Speech

```bash
# Generate speech from text
curl -X POST http://localhost:7888/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Hello CHATTA voice services",
    "voice": "af_alloy",
    "model": "tts-1"
  }' \
  --output speech.wav
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:7888/v1/audio/speech",
    json={
        "input": "Hello from CHATTA",
        "voice": "af_alloy",
        "model": "tts-1"
    }
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

### Available Kokoro Voices
- `af_alloy` - Default voice
- `af_aoede` - Alternative female voice
- `af_bella` - Warm female voice
- `am_adam` - Male voice
- `am_benjamin` - Deep male voice
- `bf_emma` - British female
- `bm_george` - British male

## Testing

### Run Integration Tests
```bash
# Run comprehensive test suite
python test_all_services.py
```

This will test:
1. Individual service health checks
2. Whisper STT transcription
3. Kokoro TTS generation
4. LiveKit connectivity
5. End-to-end voice flow

### Manual Testing

1. **Test TTS Generation:**
```bash
echo "Testing CHATTA voice" | \
  curl -X POST http://localhost:7888/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d @- \
  --data-raw '{"input":"Testing CHATTA voice","voice":"af_alloy","model":"tts-1"}' \
  --output test.wav && afplay test.wav
```

2. **Test STT Transcription:**
```bash
# First generate test audio (macOS)
say -o test.wav --data-format=LEI16@16000 "Testing whisper transcription"

# Then transcribe it
curl -X POST http://localhost:8880/v1/audio/transcriptions \
  -F "file=@test.wav" \
  -F "model=whisper-1"
```

## Configuration

### Docker Compose Environment Variables

**Whisper:**
- `WHISPER_MODEL`: Model size (base, small, medium, large)
- `WHISPER_THREADS`: Number of CPU threads

**Kokoro:**
- `KOKORO_MODEL`: Model version (kokoro-v0.87)
- `KOKORO_VOICE`: Default voice (af, am, bf, bm)

### Volume Mounts
- `./models/whisper:/models` - Whisper model storage
- `./models/kokoro:/models` - Kokoro model storage
- `./docker/livekit/livekit.yaml:/etc/livekit.yaml` - LiveKit config

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs whisper
docker-compose logs kokoro
docker-compose logs livekit

# Rebuild if needed
docker-compose build --no-cache whisper
docker-compose build --no-cache kokoro
```

### Port Already in Use
```bash
# Find process using port
lsof -i :8880  # Whisper
lsof -i :7888  # Kokoro
lsof -i :7880  # LiveKit

# Kill process or change port in docker-compose.yml
```

### Model Download Issues
```bash
# Manually download models
mkdir -p models/whisper models/kokoro

# Whisper models are auto-downloaded on first use
# Kokoro models need to be present in docker/kokoro/
```

### Performance Issues
- Increase `WHISPER_THREADS` for faster transcription
- Use smaller Whisper model (base vs large)
- Allocate more Docker resources in Docker Desktop settings

## Architecture

```
┌─────────────────────────────────────────┐
│           CHATTA Application            │
├─────────────────────────────────────────┤
│          MCP Voice Tools                │
└────────────┬────────────────────────────┘
             │
    ┌────────┴───────────────────┐
    │   Docker Network: chatta    │
    ├────────────────────────────┤
    │                            │
    │  ┌──────────────┐         │
    │  │ Whisper STT  │:8880    │
    │  └──────────────┘         │
    │                            │
    │  ┌──────────────┐         │
    │  │ Kokoro TTS   │:7888    │
    │  └──────────────┘         │
    │                            │
    │  ┌──────────────┐         │
    │  │   LiveKit    │:7880-81 │
    │  └──────────────┘         │
    └────────────────────────────┘
```

## Security Considerations

1. **Local-Only by Default**: Services bind to localhost (0.0.0.0 in containers mapped to host)
2. **No Authentication**: Add reverse proxy with auth for production
3. **Resource Limits**: Consider adding Docker resource limits
4. **Model Security**: Models are stored locally, no cloud dependencies

## Advanced Configuration

### Custom Whisper Model
Edit `docker/whisper/server_simple.py`:
```python
model = whisper.load_model("large")  # Change from "base"
```

### Custom Kokoro Voices
Mount additional voice files in `docker-compose.yml`:
```yaml
volumes:
  - ./custom-voices:/app/custom-voices
```

### LiveKit Configuration
Edit `docker/livekit/livekit.yaml` for WebRTC settings:
```yaml
port: 7880
rtc:
  tcp_port: 7881
  udp_port_range: 50000-50100
```

## Next Steps

1. **Integration with CHATTA MCP**:
   - Services auto-discovered by CHATTA's provider system
   - Available through `voice_converse` MCP tool

2. **Production Deployment**:
   - Add SSL/TLS termination
   - Implement authentication
   - Set resource limits
   - Use Docker Swarm or Kubernetes

3. **Performance Optimization**:
   - GPU acceleration for Whisper
   - Model quantization for faster inference
   - Load balancing for multiple instances

## Support

For issues or questions:
- Check service logs: `docker-compose logs [service]`
- Run test suite: `python test_all_services.py`
- Verify ports are available and not blocked by firewall
- Ensure Docker has sufficient resources allocated