# Config Directory ⚙️

This directory contains configuration files and examples for CHATTA.

## Files

### Active Configuration
- **.mcp.json** - MCP server configuration (user-specific)
- **.voices.txt** - Voice preferences (user-specific)

### Examples
- **mcp.example.json** - Template MCP configuration
- **voices.example.txt** - Template voice preferences

## Setup

1. Copy example files to create your configuration:
```bash
cp config/mcp.example.json config/.mcp.json
cp config/voices.example.txt config/.voices.txt
```

2. Edit `.mcp.json` to configure MCP server:
```json
{
  "mcpServers": {
    "chatta": {
      "command": "chatta",
      "args": ["mcp"],
      "env": {
        "CHATTA_MODE": "local"
      }
    }
  }
}
```

3. Edit `.voices.txt` to set voice preferences:
```
nova        # OpenAI voice
kokoro:af   # Kokoro voice
en-US       # Language preference
```

## Note

Files starting with `.` are ignored by git to protect user-specific settings.