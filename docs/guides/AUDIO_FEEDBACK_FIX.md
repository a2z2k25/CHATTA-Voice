# Audio Feedback Fix for Claude Code

## Problem Summary
Audio feedback chimes are implemented but not working when called through Claude Code's MCP interface.
Additionally, simpleaudio library causes Python crashes on macOS with Python 3.13.

## Root Cause Analysis

### What Works ✅
1. **Direct Python execution** - Chimes play correctly when called directly
   - `play_chime_start()` and `play_chime_end()` functions work
   - Returns `True` indicating successful playback
   - Uses `sounddevice` library for audio output

2. **Configuration** - Audio feedback is enabled by default
   - `AUDIO_FEEDBACK_ENABLED = True` in config
   - Environment variables properly set in `.mcp.json`

### What Doesn't Work ❌
1. **MCP Server Context** - Audio doesn't play when called via MCP
   - The MCP server runs in a subprocess via `stdio` transport
   - Audio context may not be properly initialized in subprocess
   - No error messages but audio is silent

## The Fix

### Option 1: Force Audio Context Initialization
Add audio device initialization when MCP server starts:

```python
# In voice_mode/server.py, add after imports:
import sounddevice as sd

# Force audio device initialization on server start
try:
    sd.default.device  # This triggers device initialization
    logger.info(f"Audio device initialized: {sd.query_devices()[sd.default.device[1]]['name']}")
except Exception as e:
    logger.warning(f"Could not initialize audio device: {e}")
```

### Option 2: Use External Audio Player
Instead of `sounddevice`, use system audio player:

```python
# In voice_mode/core.py, modify play_chime_start/end:
import subprocess
import tempfile
from scipy.io.wavfile import write

async def play_chime_start(...):
    try:
        chime = generate_chime(...)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            write(f.name, sample_rate, chime)
            
            # Play using system command
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['afplay', f.name], check=True)
            elif sys.platform.startswith('linux'):
                subprocess.run(['aplay', f.name], check=True)
            else:  # Windows
                subprocess.run(['powershell', '-c', f'(New-Object Media.SoundPlayer "{f.name}").PlaySync()'], check=True)
        
        return True
    except Exception as e:
        logger.debug(f"Could not play chime: {e}")
        return False
```

### Option 3: Pre-generate Audio Files
Create actual audio files instead of generating programmatically:

1. Generate and save chime files:
```python
# generate_chimes.py
from voice_mode.core import generate_chime
from scipy.io.wavfile import write
import os

# Create audio directory
audio_dir = "voice_mode/audio"
os.makedirs(audio_dir, exist_ok=True)

# Generate start chime
start_chime = generate_chime([800, 1000])
write(f"{audio_dir}/start_chime.wav", 16000, start_chime)

# Generate end chime  
end_chime = generate_chime([1000, 800])
write(f"{audio_dir}/end_chime.wav", 16000, end_chime)
```

2. Use simpleaudio to play files:
```python
# In voice_mode/core.py
import simpleaudio as sa
from pathlib import Path

AUDIO_DIR = Path(__file__).parent / "audio"

async def play_chime_start(...):
    try:
        wave_obj = sa.WaveObject.from_wave_file(str(AUDIO_DIR / "start_chime.wav"))
        play_obj = wave_obj.play()
        play_obj.wait_done()
        return True
    except Exception as e:
        logger.debug(f"Could not play chime: {e}")
        return False
```

## Recommended Solution

**Option 3** (Pre-generated files with simpleaudio) is most reliable because:
- Works consistently across all contexts (subprocess, MCP, direct)
- `simpleaudio` is already a dependency
- Reduces computational overhead
- More predictable behavior

## Implementation Steps

1. Generate chime audio files
2. Store in `voice_mode/audio/` directory
3. Modify `play_chime_start()` and `play_chime_end()` to use simpleaudio
4. Test through MCP server
5. Verify in Claude Code

## Final Implementation

The solution uses native system audio players with pre-generated WAV files:
- **macOS**: Uses `afplay` command (built-in, no crashes)
- **Linux**: Uses `aplay` or `paplay`
- **Windows**: Falls back to simpleaudio with error handling

This approach avoids the Python crash issue with simpleaudio on macOS/Python 3.13.

## Testing Checklist

- [x] Direct Python execution plays chimes
- [x] CLI command plays chimes
- [x] MCP server subprocess plays chimes
- [x] Claude Code integration plays chimes
- [x] Bluetooth devices work correctly
- [x] Volume levels are appropriate
- [x] No Python crashes on macOS