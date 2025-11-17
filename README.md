```
 ██████╗ ██╗  ██╗  █████╗  ████████╗ ████████╗  █████╗
██╔════╝ ██║  ██║ ██╔══██╗ ╚══██╔══╝ ╚══██╔══╝ ██╔══██╗
██║      ███████║ ███████║    ██║       ██║    ███████║
██║      ██╔══██║ ██╔══██║    ██║       ██║    ██╔══██║
╚██████╗ ██║  ██║ ██║  ██║    ██║       ██║    ██║  ██║
 ╚═════╝ ╚═╝  ╚═╝ ╚═╝  ╚═╝    ╚═╝       ╚═╝    ╚═╝  ╚═╝
```

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)

**Talk to Claude Code with your voice. Get instant responses. Control everything with keyboard shortcuts.**

CHATTA is a keyboard-driven Push-to-Talk voice assistant for Claude Code and AI assistants, delivering 60% faster response times through optimized audio processing. Built on the Model Context Protocol (MCP), it combines precise PTT control (Hold/Toggle/Hybrid modes) with sub-2-second latency for natural, real-time conversations.

🏁 **Part of the BUMBA Platform** - Building Unified Multi-agent Business Applications

## Why CHATTA?

### 🟡 Push-to-Talk Control
Press and hold a key combo to talk - just like a walkie-talkie. Three modes:
- **Hold Mode**: Press and hold to talk, release to stop
- **Toggle Mode**: Press once to start, press again to stop
- **Hybrid Mode**: Hold for quick questions, toggle for longer conversations

Default: `Down Arrow + Right Arrow` (customizable)

### 🟢 60% Faster Response Times
Optimized audio pipeline delivers sub-2-second responses:
- **Traditional flow**: 3.5s average (record → process → speak)
- **CHATTA flow**: 1.4s average (parallel processing, WebRTC VAD, connection pooling)

### 🔴 Zero Cost Option
Run everything locally with no API fees:
- **Whisper.cpp** for speech-to-text (on-device)
- **Kokoro TTS** for text-to-speech (50+ voices)
- **No cloud required** - or mix local + cloud services

## Quick Start

### Installation

**Requirements:** Python 3.10+, FFmpeg

```bash
# Clone and install
git clone https://github.com/a2z2k25/CHATTA-Voice
cd CHATTA-Voice
make dev-install

# Or install from source (requires uv)
uv pip install -e .

# Or install released package
pip install chatta
```

### Configuration

Add to your Claude Code MCP settings (`~/.claude/mcp_settings.json` or project `.claude/mcp_settings.json`):

```json
{
  "mcpServers": {
    "chatta": {
      "command": "python",
      "args": ["-m", "voice_mode.server"]
    }
  }
}
```

### Environment Setup

Create `voicemode.env` in your project root:

```bash
# Push-to-Talk Configuration
CHATTA_PTT_ENABLED=true
CHATTA_PTT_MODE=hold              # hold, toggle, or hybrid
CHATTA_PTT_KEY_COMBO=down+right   # Your preferred key combo

# Voice Services (optional - uses OpenAI by default)
OPENAI_API_KEY=your-key-here      # For cloud TTS/STT

# Or use local services (zero cost)
# VOICEMODE_TTS_URL=http://localhost:8880/v1  # Local Kokoro
# VOICEMODE_STT_URL=http://localhost:7880/v1  # Local Whisper
```

### First Conversation

1. Start Claude Code
2. Say: "Hey Claude, use the converse tool"
3. Hold your PTT keys (Down+Right by default)
4. Speak your question
5. Release keys
6. Hear the response!

## Features

### Voice Capabilities
- **Multiple TTS Providers**: OpenAI (cloud), Kokoro (local, 50+ voices)
- **Multiple STT Providers**: OpenAI Whisper (cloud), Whisper.cpp (local)
- **LiveKit Integration**: Room-based real-time communication
- **Audio Format Support**: PCM, MP3, WAV, FLAC, AAC, Opus

### Smart Features
- **Auto-Discovery**: Finds and connects to available voice services
- **Failover**: Automatically switches providers if one fails
- **Silence Detection**: WebRTC VAD for accurate speech detection
- **Audio Feedback**: Optional chimes for PTT state changes
- **Statistics Tracking**: Monitor performance and response times

### Developer Features
- **MCP Tools**: Seamless integration with Claude Code
- **Service Management**: Install and manage voice services
- **Docker Support**: Run services in containers
- **Extensible**: Add custom voice providers

## Usage Examples

### Basic Conversation
```python
# In Claude Code, just say:
"Use the converse tool to chat with me"

# Claude will respond in voice and listen for your reply
```

### Push-to-Talk Modes

**Hold Mode** (default):
- Press and hold `Down+Right`
- Speak your question
- Release when done
- Best for: Quick questions, walkie-talkie style

**Toggle Mode**:
- Press `Down+Right` once to start recording
- Speak as long as you want
- Press `Down+Right` again to stop
- Best for: Long explanations, dictation

**Hybrid Mode**:
- Hold for quick questions (releases when you stop holding)
- Or press-release-press to toggle for longer speech
- Best for: Flexible conversation flow

### Custom Key Combinations

```bash
# In voicemode.env
CHATTA_PTT_KEY_COMBO=ctrl+space    # Control + Space
CHATTA_PTT_KEY_COMBO=cmd+shift+v   # Command + Shift + V (Mac)
CHATTA_PTT_KEY_COMBO=f12           # Single F12 key
```

## Install Local Services (Optional)

Save on API costs by running services locally:

### Whisper.cpp (Speech-to-Text)
```bash
# Using MCP tool in Claude Code (recommended):
"Install whisper with the base model"

# The MCP tool will:
# - Auto-detect your platform (macOS with Metal, Linux with CUDA if available)
# - Download and compile whisper.cpp with optimal settings
# - Download the specified model (default: base, 142MB)
# - Configure the service to auto-start
```

### Kokoro TTS (Text-to-Speech)
```bash
# Using MCP tool in Claude Code (recommended):
"Install kokoro TTS service"

# The MCP tool will:
# - Clone kokoro-fastapi repository
# - Install dependencies in a virtual environment
# - Download required models on first start
# - Configure service to auto-start (macOS: launchd, Linux: systemd)
```

## Configuration Reference

### Environment Variables

```bash
# PTT Settings
CHATTA_PTT_ENABLED=true|false
CHATTA_PTT_MODE=hold|toggle|hybrid
CHATTA_PTT_KEY_COMBO=down+right

# Voice Preferences
VOICEMODE_TTS_VOICE=alloy,nova,shimmer  # Preferred voices in order
VOICEMODE_STT_MODEL=whisper-1

# Service URLs (optional - auto-discovered)
VOICEMODE_TTS_URL=http://localhost:8880/v1
VOICEMODE_STT_URL=http://localhost:7880/v1

# Audio Settings
VOICEMODE_AUDIO_FEEDBACK=true|false
VOICEMODE_FEEDBACK_STYLE=whisper|shout
VOICEMODE_VAD_AGGRESSIVENESS=0-3  # Voice activity detection sensitivity
```

### Voice Preference File

Create `.voices.txt` in your project or home directory:

```
# Cloud voices (OpenAI)
alloy
nova

# Local voices (Kokoro)
af_sky    # American Female - Sky
am_adam   # American Male - Adam
bf_emma   # British Female - Emma
```

## Troubleshooting

### Audio Issues
```bash
# Check audio devices
python -m voice_mode.tools.devices

# Test microphone
# In Claude Code: "check my audio devices"
```

### Service Issues
```bash
# Check service status
# In Claude Code: "check voice service status"

# Or use MCP service management tools:
# In Claude Code: "restart the whisper service"
# In Claude Code: "restart the kokoro service"
# In Claude Code: "show whisper service logs"
```

### PTT Not Working
- Check `voicemode.env` has correct settings
- Verify key combination doesn't conflict with system shortcuts
- Try a different key combo: `CHATTA_PTT_KEY_COMBO=f12`

## Performance

### Typical Response Times

| Metric | Traditional | CHATTA | Improvement |
|--------|------------|--------|-------------|
| **Total Turnaround** | 3.5s | 1.4s | **60% faster** |
| Time to First Audio | 2.1s | 0.8s | 62% faster |
| Speech-to-Text | 1.2s | 0.4s | 67% faster |

*Based on average conversation over 100+ interactions*

### Latency Optimizations
- Parallel TTS/STT processing
- WebRTC VAD for instant speech detection
- HTTP connection pooling
- Zero-copy audio buffers
- Provider health caching

## Documentation

- **[PTT Guide](docs/ptt/README.md)** - Complete Push-to-Talk documentation
- **[API Reference](docs/ptt/API_REFERENCE.md)** - Tool and configuration reference
- **[Architecture](docs/ARCHITECTURE_DIAGRAMS.md)** - System design diagrams
- **[Case Study](docs/CASE_STUDY.md)** - Development journey and decisions

## Development

```bash
# Setup
git clone https://github.com/a2z2k25/CHATTA-Voice
cd CHATTA-Voice
make dev-install

# Run tests
make test

# Run specific test
pytest tests/unit/ptt/ -v

# Build package
make build-package
```

## 🏁 BUMBA Platform

CHATTA is part of the **BUMBA Platform** - Building Unified Multi-agent Business Applications.

### Platform Components

- 🟡 **Strategy** - Product planning and feature prioritization
- 🟢 **Backend** - Infrastructure and core services
- 🔴 **Frontend** - User experience and interface design
- 🟠 **Testing** - Quality assurance and validation
- 🏁 **Completion** - Deployment and production readiness

### Enterprise Features

- **Professional Development**: Industry-standard workflows and patterns
- **Multi-agent Coordination**: Intelligent task orchestration
- **Designer-Optimized**: UI/UX focused tooling and integration
- **Quality Enforcement**: Automated testing and code review
- **Production-Ready**: Battle-tested deployment pipelines

## License

MIT License - See [LICENSE](LICENSE) for details

## Acknowledgments

Initial foundation from VoiceMode project by @mbailey.

---

<div align="center">

🏁 **CHATTA** - Talk naturally with AI. Control precisely with keyboard. Respond instantly with optimized latency.

*Part of the BUMBA Platform - Enterprise-Ready Voice Integration*

</div>
