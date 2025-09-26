"""
voice-mode - Voice interaction capabilities for Model Context Protocol (MCP) servers

This package provides MCP servers for voice interactions through multiple transports:
- Local microphone recording and playback
- LiveKit room-based voice communication
- Configurable OpenAI-compatible STT/TTS services
"""

from .version import __version__

# Create the MCP instance here so tools can import it
from fastmcp import FastMCP
mcp = FastMCP("chatta")

# Import tools to register them with the mcp instance
# We need to do this here so they're registered before server.py runs
try:
    from . import tools
    from . import prompts
    from . import resources
except ImportError:
    # If imports fail, server.py will handle them
    pass