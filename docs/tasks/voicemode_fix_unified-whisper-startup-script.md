# Unified Whisper Service Startup Script

## Problem
- Mac and Linux use different approaches for starting whisper service
- Mac has a wrapper script that sources voicemode.env
- Linux systemd directly calls binary with baked-in model path
- Changes to VOICEMODE_WHISPER_MODEL don't take effect without reinstalling service

## Solution
Create a unified wrapper script that both platforms use:
1. Script sources ~/.voicemode/voicemode.env
2. Reads VOICEMODE_WHISPER_MODEL environment variable
3. Starts whisper with the appropriate model
4. Both launchd and systemd call this same script

## Implementation
1. Create template at `voice_mode/templates/scripts/start-whisper-server.sh`
2. Update install.py to copy template to `~/.voicemode/services/whisper/bin/`
3. Update systemd service to call wrapper script instead of binary
4. Ensure template is included in Python package

## Benefits
- Consistent behavior across platforms
- Dynamic model selection from environment
- Single script to maintain
- Changes to voicemode.env take effect on service restart

## Testing
- [ ] Test on macOS with launchd
- [ ] Test on Linux with systemd
- [ ] Verify model changes in voicemode.env are respected
- [ ] Test with uv tool install
- [ ] Test with uvx