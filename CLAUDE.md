# CLAUDE.md

Instructions for Claude Code when working with the CHATTA codebase.

## Project Overview

**CHATTA** is a Python MCP server providing voice conversation capabilities for AI assistants. It features Push-to-Talk (PTT) keyboard control, optimized latency (60% faster than traditional voice), and support for both cloud and local voice services.

**Key Innovation:** PTT system with 3 modes (Hold/Toggle/Hybrid) + latency optimizations achieving sub-2-second response times.

## Quick Commands

```bash
# Development
make dev-install          # Install with dependencies
make test                 # Run all tests
pytest tests/unit/ptt/ -v  # Run PTT tests specifically

# Building
make build-package        # Build distributable package
make clean                # Clean build artifacts

# Package is `voice_mode`, server runs as: python -m voice_mode.server
```

## Architecture

### Core Components

**1. MCP Server** (`src/voice_mode/server.py`)
- FastMCP-based stdio transport
- Auto-imports tools, prompts, resources

**2. PTT System** (`src/voice_mode/ptt/`)
- **State Machine**: 7 states (IDLE → ARMED → RECORDING → PROCESSING → etc.)
- **3 Modes**: Hold (walkie-talkie), Toggle (press-to-start/stop), Hybrid (best of both)
- **Transport Adapter**: Abstracts LiveKit vs Local microphone
- **Keyboard Monitor**: Cross-platform key combo detection (pynput)

**3. Tool System** (`src/voice_mode/tools/`)
- **converse.py**: Main voice conversation tool with PTT integration
- **service.py**: Manage Whisper/Kokoro/LiveKit services
- **providers.py**: Auto-discover OpenAI-compatible voice endpoints
- **devices.py**: Audio device management

**4. Provider System** (`src/voice_mode/providers.py`)
- Dynamic discovery of TTS/STT endpoints
- Health checking with automatic failover
- Voice-first selection algorithm

**5. Configuration** (`src/voice_mode/config.py`)
- Environment-based with `voicemode.env` support
- PTT settings: `CHATTA_PTT_ENABLED`, `CHATTA_PTT_MODE`, `CHATTA_PTT_KEY_COMBO`
- Voice preferences from `.voices.txt` files

### PTT State Machine

```
IDLE → ARMED (key pressed) → RECORDING (audio detected) →
PROCESSING (key released) → GENERATING (TTS) → PLAYING (audio out) → IDLE

Special states:
- CANCELLED: User interrupt (Escape key)
- ERROR: Recoverable failures
```

### Key Design Patterns

1. **Adapter Pattern**: `TransportAdapter` abstracts LiveKit/Local, enabling zero-breaking-change PTT integration
2. **OpenAI Compatibility**: All services expose OpenAI-compatible endpoints
3. **Failover**: Automatic provider switching on failure
4. **Latency Optimization**: Parallel TTS/STT, WebRTC VAD, connection pooling, zero-copy audio

### Latency Achievements

- **Traditional**: 3.5s average (sequential record → STT → LLM → TTS → play)
- **CHATTA**: 1.4s average (60% faster via parallel processing, VAD, pooling)

## Development Notes

- **Package Manager**: `uv` (not pip)
- **Python**: 3.10+
- **Dependencies**: FFmpeg (required), pynput (PTT), webrtcvad (VAD)
- **Testing**: pytest with fixtures for mocking services
- **Architecture**: src/ layout, tests/ mirrors structure

## Voice Conversation Best Practices

### Hybrid Voice-Text Pattern

For lengthy responses (>500 chars, code blocks, 3+ paragraphs):
1. Output detailed text first
2. Follow with concise voice summary using `wait_for_response=True`
3. Example: "I've provided the details above. Review and let me know your thoughts."

Prevents awkward silences, maintains conversation flow. See [docs/ptt/HYBRID_VOICE_TEXT_PATTERN.md](docs/ptt/HYBRID_VOICE_TEXT_PATTERN.md).

### Voice Identity: "Chatta"

When using `mcp__chatta__converse`: respond naturally to "Chatta" as conversational name. Context-specific (voice only). Don't introduce unprompted or use in text/code/tools. Casual acknowledgment, no emphasis.

**Note:** Identity instruction embedded in `src/voice_mode/prompts/converse.py`, loads automatically.

See [docs/voice/CONVERSATIONAL_IDENTITY.md](docs/voice/CONVERSATIONAL_IDENTITY.md) for details.

## File Locations

### Source Code
- **Server**: `src/voice_mode/server.py`
- **PTT Core**: `src/voice_mode/ptt/core.py` (state machine, recorder)
- **PTT Adapter**: `src/voice_mode/ptt/transport_adapter.py`
- **Config**: `src/voice_mode/config.py`
- **Providers**: `src/voice_mode/providers.py`

### Configuration
- **Build**: `pyproject.toml` (root), `Makefile` (root)
- **Environment**: `voicemode.env` (project root, gitignored if tracked)
- **Voice Prefs**: `.voices.txt` (project or home directory)
- **MCP Settings**: `~/.claude/mcp_settings.json` or `.claude/mcp_settings.json`

### Documentation
- **PTT Guide**: `docs/ptt/README.md`
- **API Ref**: `docs/ptt/API_REFERENCE.md`
- **Architecture**: `docs/ARCHITECTURE_DIAGRAMS.md`
- **Case Study**: `docs/CASE_STUDY.md` (comprehensive development history)

### Tests
- **Unit**: `tests/unit/` (config, providers, tools)
- **PTT Tests**: `tests/unit/ptt/` (state machine, adapter)
- **Integration**: `tests/integration/` (end-to-end flows)
- **Manual**: `tests/manual/` (user interaction required)

## Common Tasks

### Adding PTT Feature
1. Update state machine in `src/voice_mode/ptt/core.py`
2. Add tests in `tests/unit/ptt/`
3. Update docs in `docs/ptt/`

### Adding Voice Provider
1. Ensure OpenAI-compatible endpoint
2. Provider auto-discovered if health check passes
3. Add to provider registry in `src/voice_mode/providers.py`

### Debugging Voice Issues
- Check: `voicemode.env` for PTT config
- Run: `python -m voice_mode.tools.devices` for audio devices
- Use: MCP tool `voice_status` for service health
- Enable: Event logging with `VOICEMODE_EVENT_LOG_ENABLED=true`

## Testing

```bash
# All tests
pytest tests/ -v

# PTT tests only
pytest tests/unit/ptt/ -v

# Integration tests
pytest tests/integration/ -v

# Specific test
pytest tests/unit/ptt/test_state_machine.py::test_hold_mode -v
```

## Important Constraints

- PTT requires foreground app (keyboard monitoring limitation)
- WebRTC VAD requires audio input (won't work with file playback)
- Service auto-discovery runs on startup (may take 2-3s)
- Transport adapter pattern maintains backward compatibility

## References

- **MCP**: Model Context Protocol by Anthropic
- **FastMCP**: Python MCP framework
- **Whisper**: OpenAI speech-to-text model
- **Kokoro**: Open-source TTS by remsky
- **LiveKit**: Real-time communication platform
