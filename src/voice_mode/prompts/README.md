# Voice Mode Prompts

This directory contains all the FastMCP prompt definitions for the Voice Mode server.

## Prompt Files

### conversation.py
- `converse`: Start an interactive voice conversation - provides instructions for conducting natural voice conversations

### kokoro_management.py
- `kokoro-start`: Instructions to start the Kokoro TTS service
- `kokoro-stop`: Instructions to stop the Kokoro TTS service  
- `kokoro-status`: Instructions to check Kokoro TTS service status

### status.py
- `voice-status`: Instructions to check comprehensive status of all voice services

### voice_commands.py
- `voice_setup`: Guide for setting up voice services
- `emotional_speech_guide`: Guide for using emotional speech features

## Usage

All prompts are automatically registered with FastMCP through the decorator pattern. They can be invoked by the LLM to get instructions for specific voice-related tasks.

## Adding New Prompts

To add a new prompt:

1. Create a new file or add to an existing file in this directory
2. Import the mcp instance: `from voice_mode.server import mcp`
3. Use the `@mcp.prompt()` decorator with an optional name parameter
4. Define a function that returns a string with instructions

Example:
```python
from voice_mode.server import mcp

@mcp.prompt(name="my-prompt")
def my_prompt() -> str:
    """Brief description of what this prompt does."""
    return "Instructions for the LLM to follow..."
```

The prompts will be automatically imported and registered when the server starts.
