# MCP Configuration (.mcp.json) Environment Variables

## Overview

This document explains how environment variables work in MCP (Model Context Protocol) configuration files, based on research and testing with Claude Code and other MCP clients.

## Current Limitations

**Environment variable substitution is NOT supported** in .mcp.json files. Despite being a commonly requested feature, the `${VARIABLE}` syntax does not work.

### ❌ What DOESN'T Work

```json
{
  "mcpServers": {
    "my-server": {
      "command": "./my-server",
      "env": {
        "API_KEY": "${OPENAI_API_KEY}",           // Does NOT expand
        "BASE_URL": "${MY_SERVICE_URL:-default}", // Does NOT expand
        "TOKEN": "${env:MY_TOKEN}"                // Does NOT expand
      }
    }
  }
}
```

### ✅ What DOES Work

```json
{
  "mcpServers": {
    "my-server": {
      "command": "./my-server", 
      "env": {
        "API_KEY": "sk-your-actual-key-here",  // Only literal values
        "DEBUG": "true",                          // Literal strings
        "PORT": "3000"                            // Literal values only
      }
    }
  }
}
```

## How Environment Variables Are Handled

1. **Explicit Declaration Required**: Only variables explicitly listed in the `env` section are passed to the MCP server
2. **No Automatic Passthrough**: Global environment variables are NOT automatically available unless explicitly declared
3. **Literal Values Only**: The `env` section only accepts literal string values
4. **No Variable Expansion**: The MCP client does not process `${VAR}` syntax

## Workarounds

### Option 1: Remove env Block (Recommended for shared vars)

Let the MCP server read from the global environment:

```json
{
  "mcpServers": {
    "voice-mode": {
      "command": "./mcp-servers/voice-mode",
      "env": {
        "VOICE_MODE_DEBUG": "true"  // Only MCP-specific vars
      }
      // OPENAI_API_KEY will be read from global environment
    }
  }
}
```

**Pros**: 
- Uses existing environment variables
- No hardcoded secrets in config
- Works with different environments

**Cons**: 
- Requires global environment setup
- Less explicit about dependencies

### Option 2: Literal Values (Current working solution)

```json
{
  "mcpServers": {
    "voice-mode": {
      "type": "stdio",
      "command": "uvx",
      "args": ["voice-mode"],
      "env": {
        "OPENAI_API_KEY": "sk-proj-your-key-here",
        "VOICE_MODE_DEBUG": "true",
        "STT_BASE_URL": "https://api.openai.com/v1",
        "TTS_BASE_URL": "https://api.openai.com/v1"
      }
    }
  }
}
```

**Pros**: 
- Explicit and clear
- Works immediately
- Self-contained configuration

**Cons**: 
- Hardcoded secrets in config file
- Needs manual updates for different environments

### Option 3: envmcp Wrapper (Community Solution)

Install the community `envmcp` package:

```bash
npm install -g envmcp
```

```json
{
  "mcpServers": {
    "my-server": {
      "command": "npx",
      "args": [
        "envmcp",
        "./my-server"
      ]
    }
  }
}
```

**Pros**: 
- Enables environment variable usage
- No hardcoded secrets

**Cons**: 
- Requires additional dependency
- Community maintained (not official)

## Security Considerations

### Avoid Hardcoding Secrets

- **Don't commit** .mcp.json files with literal API keys to version control
- **Use .gitignore** to exclude configuration files with secrets
- **Consider environment-specific** config files

### Best Practices

1. **Use Option 1** for widely available environment variables (like OPENAI_API_KEY)
2. **Use Option 2** for deployment-specific configurations 
3. **Document required environment variables** in your README
4. **Create example config files** without secrets

## Feature Requests

The MCP community has active requests for environment variable substitution:

- [VS Code Issue #245237](https://github.com/microsoft/vscode/issues/245237) - Support `${env:VARIABLE_NAME}` syntax
- [Cursor Forum Discussion](https://forum.cursor.com/t/how-to-use-environment-variables-in-mcp-json/79296) - Community workarounds

## Example: Voice MCP Configuration

Our working voice-mode configuration uses Option 2 (literal values):

```json
{
  "mcpServers": {
    "voice-mode": {
      "type": "stdio",
      "command": "./mcp-servers/voice-mode",
      "args": [],
      "env": {
        "STT_BASE_URL": "https://api.openai.com/v1",
        "TTS_BASE_URL": "https://api.openai.com/v1", 
        "TTS_VOICE": "alloy",
        "TTS_MODEL": "tts-1",
        "STT_MODEL": "whisper-1",
        "LIVEKIT_URL": "ws://127.0.0.1:7880",
        "LIVEKIT_API_KEY": "devkey",
        "LIVEKIT_API_SECRET": "secret",
        "VOICE_MODE_DEBUG": "true",
        "OPENAI_API_KEY": "sk-proj-actual-key-here"
      }
    }
  }
}
```

## Testing Environment Variable Behavior

To test whether variables are being passed correctly:

1. **Add debug logging** to your MCP server startup
2. **Check process.env** in your server code
3. **Use VOICE_MODE_DEBUG=true** to see detailed logs
4. **Verify API calls** work with the provided credentials

## Summary

- Environment variable substitution **does not work** in .mcp.json
- Only **literal values** are supported in the `env` section
- **Global environment variables** must be explicitly declared to be passed through
- **Remove the env block** if you want the server to read from global environment
- This is a **known limitation** with active feature requests for improvement