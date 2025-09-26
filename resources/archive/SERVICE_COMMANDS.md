# Service Management Commands

Voice Mode now includes built-in service management commands for Kokoro and Whisper services.

## Usage

### Backward Compatibility

The default behavior is preserved:
```bash
voice-mode              # Starts MCP server (existing behavior)
```

### Service Management

New subcommands allow direct service control without starting the MCP server:

#### Kokoro TTS Service
```bash
voice-mode kokoro status           # Show service status and resource usage
voice-mode kokoro start            # Start Kokoro service
voice-mode kokoro stop             # Stop Kokoro service  
voice-mode kokoro restart          # Restart Kokoro service
voice-mode kokoro enable           # Enable service at boot/login
voice-mode kokoro disable          # Disable service from boot/login
voice-mode kokoro logs             # View service logs (default: 50 lines)
voice-mode kokoro logs --lines 100 # View last 100 log lines
voice-mode kokoro health           # Check health endpoint
voice-mode kokoro update-service-files # Update service files to latest
```

#### Whisper STT Service
```bash
voice-mode whisper status          # Show service status and resource usage
voice-mode whisper start           # Start Whisper service
voice-mode whisper stop            # Stop Whisper service
voice-mode whisper restart         # Restart Whisper service  
voice-mode whisper enable          # Enable service at boot/login
voice-mode whisper disable         # Disable service from boot/login
voice-mode whisper logs            # View service logs (default: 50 lines)
voice-mode whisper logs --lines 100 # View last 100 log lines
voice-mode whisper health          # Check health endpoint
voice-mode whisper update-service-files # Update service files to latest
```

## Examples

### Quick Status Check
```bash
$ voice-mode kokoro status
✅ Kokoro is running
   PID: 12345
   Port: 8880
   CPU: 0.1%
   Memory: 8.9 MB
   Uptime: 2h 15m 30s
   Service files: v1.1.1 (latest)
```

### Starting Services
```bash
$ voice-mode whisper start
✅ Whisper started successfully (PID: 54321)

$ voice-mode kokoro start  
✅ Kokoro started
```

### Health Checks
```bash
$ voice-mode kokoro health
✅ Kokoro is responding
   Status: healthy
   Uptime: 2h 15m 30s

$ voice-mode whisper health
❌ Whisper not responding on port 2022
```

### Service Management
```bash
$ voice-mode kokoro enable
✅ Kokoro service enabled. It will start automatically at login.
Plist: /Users/user/Library/LaunchAgents/com.voicemode.kokoro.plist

$ voice-mode whisper disable
✅ Whisper service disabled and removed
```

### Viewing Logs
```bash
$ voice-mode kokoro logs --lines 20
=== Last 20 log entries for kokoro ===
[2025-08-11 15:30:42] Starting Kokoro FastAPI server...
[2025-08-11 15:30:43] Server listening on 0.0.0.0:8880
...
```

## Cross-Platform Support

Commands work on both macOS and Linux:
- **macOS**: Uses launchctl for service management
- **Linux**: Uses systemctl for service management  
- **Fallback**: Direct process control when service managers not available


## Benefits

1. **No shell setup required** - Commands work immediately after installing voice-mode
2. **Consistent interface** - Same commands on all platforms
3. **Better help text** - Built-in help with `--help`
4. **Standardized options** - Consistent flags like `--lines`
5. **No MCP overhead** - Service commands don't start the MCP server
6. **Future-proof** - Easy to add new service management features