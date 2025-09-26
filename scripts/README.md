# Scripts Directory 🔧

This directory contains utility scripts and test files for CHATTA.

## Shell Scripts

- **chatta_mcp_server.sh** - MCP server launcher script
- **safe_cleanup.sh** - Safe cleanup utility
- **security_cleanup.sh** - Security-focused cleanup tool
- **docker_setup.py** - Docker configuration setup

## Test Scripts

### Core Tests
- **test_*.py** - Various test scripts for different components
- **demo_*.py** - Demonstration scripts
- **verify_*.py** - Verification utilities

### Categories
- Audio testing (test_audio_*.py)
- MCP integration (test_mcp_*.py)
- Voice functionality (test_voice_*.py, test_vad*.py)
- Service testing (test_services.py)
- Interactive testing (test_interactive.py)

## Usage

Most Python scripts can be run directly:
```bash
python scripts/test_audio_simple.py
```

Shell scripts should be made executable first:
```bash
chmod +x scripts/chatta_mcp_server.sh
./scripts/chatta_mcp_server.sh
```