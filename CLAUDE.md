# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VoiceMode is a Python package that provides voice interaction capabilities for AI assistants through the Model Context Protocol (MCP). It enables natural voice conversations with Claude Code and other AI coding assistants by integrating speech-to-text (STT) and text-to-speech (TTS) services.

## Key Commands

### Development & Testing
```bash
# Install in development mode with dependencies
make dev-install

# Run all unit tests
make test
# Or directly: uv run pytest tests/ -v --tb=short

# Run specific test
uv run pytest tests/test_voice_mode.py -v

# Clean build artifacts
make clean
```

### Building & Publishing
```bash
# Build Python package
make build-package

# Build development version (auto-versioned)
make build-dev  

# Test package installation
make test-package

# Release workflow (bumps version, tags, pushes)
make release
```

### Documentation
```bash
# Serve docs locally at http://localhost:8000
make docs-serve

# Build documentation site
make docs-build

# Check docs for errors (strict mode)
make docs-check
```

## Architecture Overview

### Core Components

1. **MCP Server (`voice_mode/server.py`)**
   - FastMCP-based server providing voice tools via stdio transport
   - Auto-imports all tools, prompts, and resources
   - Handles FFmpeg availability checks and logging setup

2. **Tool System (`voice_mode/tools/`)**
   - **converse.py**: Primary voice conversation tool with TTS/STT integration
   - **service.py**: Unified service management for Whisper/Kokoro/LiveKit
   - **providers.py**: Provider discovery and registry management
   - **devices.py**: Audio device detection and management
   - Services subdirectory contains install/uninstall tools for Whisper, Kokoro, and LiveKit

3. **Provider System (`voice_mode/providers.py`)**
   - Dynamic discovery of OpenAI-compatible TTS/STT endpoints
   - Health checking and failover support
   - Maintains registry of available voice services

4. **Configuration (`voice_mode/config.py`)**
   - Environment-based configuration with sensible defaults
   - Support for voice preference files (project/user level)
   - Audio format configuration (PCM, MP3, WAV, FLAC, AAC, Opus)

5. **Resources (`voice_mode/resources/`)**
   - MCP resources exposed for client access
   - Statistics, configuration, changelog, and version information
   - Whisper model management

6. **Frontend (`voice_mode/frontend/`)**
   - Next.js-based web interface for LiveKit integration
   - Real-time voice conversation UI
   - Built and bundled with the Python package

### Service Architecture

The project supports multiple voice service backends:
- **OpenAI API**: Cloud-based TTS/STT (requires API key)
- **Whisper.cpp**: Local speech-to-text service
- **Kokoro**: Local text-to-speech with multiple voices
- **LiveKit**: Room-based real-time communication

Services can be installed and managed through MCP tools, with automatic service discovery and health checking.

### Key Design Patterns

1. **OpenAI API Compatibility**: All voice services expose OpenAI-compatible endpoints, enabling transparent switching between providers
2. **Dynamic Tool Discovery**: Tools are auto-imported from the tools directory structure
3. **Failover Support**: Automatic fallback between services based on availability
4. **Transport Flexibility**: Supports both local microphone and LiveKit room-based communication
5. **Audio Format Negotiation**: Automatic format validation against provider capabilities

## Development Notes

- The project uses `uv` for package management (not pip directly)
- Python 3.10+ is required
- FFmpeg is required for audio processing
- The project follows a modular architecture with FastMCP patterns
- Service installation tools handle platform-specific setup (launchd on macOS, systemd on Linux)
- Event logging and conversation logging are available for debugging
- WebRTC VAD is used for silence detection when available

## Testing Approach

- Unit tests are in the `tests/` directory
- Manual tests requiring user interaction are in `tests/manual/`
- Use `pytest` for running tests, with fixtures for mocking external services
- Integration tests verify service discovery and provider selection
- The project includes comprehensive test coverage for configuration, providers, and tools

## Voice Conversation Best Practices

### Hybrid Voice-Text Response Pattern

For lengthy responses (>500 chars, code blocks, 3+ paragraphs): output detailed text, then follow with concise voice message using `wait_for_response=True` to keep conversation active. Example: "I've provided details above. Review and let me know your thoughts." Prevents awkward silences, maintains flow. See [docs/ptt/HYBRID_VOICE_TEXT_PATTERN.md](docs/ptt/HYBRID_VOICE_TEXT_PATTERN.md).

### Voice Conversation Identity: "Chatta"

When using `mcp__chatta__converse`: respond naturally to "Chatta" as a conversational name. Context-specific (voice only). Don't introduce unprompted or use in text/code/other tools. Casual acknowledgment, no emphasis.

**Note:** As of 2025-11-11, this identity instruction is embedded directly in the `converse` prompt (`src/voice_mode/prompts/converse.py`) and automatically loads with the tool. No manual CLAUDE.md reading required.

See [docs/voice/CONVERSATIONAL_IDENTITY.md](docs/voice/CONVERSATIONAL_IDENTITY.md) for comprehensive guidelines.