# Fix Whisper Status Model Detection

## Problem

The service status tool incorrectly reports which whisper model is running. It shows `ggml-base.en.bin` when the actual model is `ggml-base.bin`.

## Investigation

1. The startup script correctly reads `VOICEMODE_WHISPER_MODEL=base` from config
2. The startup log confirms: `Model path: /Users/admin/.voicemode/services/whisper/models/ggml-base.bin`
3. The process command line shows: `--model /Users/admin/.voicemode/services/whisper/models/ggml-base.bin`
4. But status reports: `Model: ggml-base.en.bin`

## Root Cause

The service status detection code likely has a bug in how it parses the model from either:
- The running process arguments
- The filesystem (maybe looking for first matching model?)
- Some cached/stale information

## Solution

Need to fix the model detection in the service status tool to:
1. Parse the `--model` argument from the process command line correctly
2. Extract just the filename from the full path
3. Report the actual model being used

## Files to Check

- `voice_mode/tools/service.py` - Service management tool
- Any helper functions that detect running model

## Testing

After fix:
1. Start whisper with `base` model
2. Check status shows `ggml-base.bin`
3. Switch to `base.en` model
4. Check status shows `ggml-base.en.bin`