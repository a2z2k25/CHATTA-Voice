# PTT User Experience Design
Date: November 9, 2025
Sprint: 1.5

## Visual Feedback States

### 1. Waiting for Key Press
```
┌─────────────────────────────────────────────┐
│ 🎤 Push-to-Talk Ready                      │
│                                             │
│ Press and hold [↓ + →] to speak            │
│ Press [ESC] to cancel                      │
│                                             │
│ ⚪ Waiting for input...                    │
└─────────────────────────────────────────────┘
```

### 2. Keys Detected (Preparing)
```
┌─────────────────────────────────────────────┐
│ 🟡 Keys Detected                           │
│                                             │
│ Hold to continue recording...              │
│                                             │
│ ⏱️ Initializing...                         │
└─────────────────────────────────────────────┘
```

### 3. Actively Recording
```
┌─────────────────────────────────────────────┐
│ 🔴 Recording                               │
│                                             │
│ Release [↓ + →] to stop                    │
│                                             │
│ ▓▓▓▓▓▓▓▓░░░░░░░░ 00:03 / 02:00           │
│ ████████████ [Audio Level]                 │
└─────────────────────────────────────────────┘
```

### 4. Processing
```
┌─────────────────────────────────────────────┐
│ 🟢 Processing                              │
│                                             │
│ Transcribing your message...               │
│                                             │
│ ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏ [spinner animation]          │
└─────────────────────────────────────────────┘
```

## CLI Output Formatting

### Minimalist Mode (Default)
```python
# Clean, single-line updates
print("\r🎤 Press and hold [↓+→] to speak...", end="", flush=True)
print("\r🔴 Recording... (00:03)            ", end="", flush=True)
print("\r🟢 Processing...                   ", end="", flush=True)
print("\r✅ Ready                           ", end="", flush=True)
```

### Verbose Mode (Debug/Learning)
```python
# Detailed multi-line output
print("""
╔══════════════════════════════════════════════╗
║ Push-to-Talk Session Started                ║
║──────────────────────────────────────────────║
║ Mode:      Hold-to-Record                   ║
║ Keys:      ↓ + →                           ║
║ Transport: Local Microphone                 ║
║ Timeout:   120 seconds                      ║
╚══════════════════════════════════════════════╝
""")
```

## Audio Level Visualization

```python
def render_audio_level(level: float, width: int = 40) -> str:
    """Render audio level as ASCII bar"""
    filled = int(level * width)
    bar = "█" * filled + "░" * (width - filled)

    # Color coding based on level
    if level < 0.2:
        color = "\033[90m"  # Gray (too quiet)
    elif level < 0.8:
        color = "\033[92m"  # Green (good)
    else:
        color = "\033[91m"  # Red (too loud)

    return f"{color}{bar}\033[0m"

# Example output:
# ████████████████████░░░░░░░░░░░░░░░░░░░░  [Good level]
# ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  [Too quiet]
# ████████████████████████████████████████  [Too loud]
```

## Error Messages

### Permission Denied
```
⚠️ Push-to-Talk Unavailable

Keyboard access permission required.

macOS: System Preferences → Security & Privacy →
       Privacy → Accessibility → Add this terminal

Falling back to standard voice mode.
Press ENTER to continue...
```

### Key Combination Conflict
```
⚠️ Key Combination Conflict

The keys [Ctrl+C] are reserved by the system.

Please choose different keys or use the default [↓+→].

Current alternatives:
- [Ctrl+Space]
- [Alt+Shift]
- [Cmd+Option] (macOS)
```

### Recording Failed
```
❌ Recording Failed

Unable to access microphone.

Possible causes:
1. Microphone in use by another app
2. Audio device disconnected
3. Insufficient permissions

Troubleshooting:
- Check audio device connections
- Close other recording apps
- Restart the voice service

[R]etry | [S]tandard mode | [C]ancel
```

## Success Feedback

### Recording Complete
```
✅ Recording Complete
Duration: 3.5 seconds
Quality: Excellent
Processing...
```

### Transcription Result
```
📝 Transcription:
"This is my transcribed message with push to talk"

Confidence: 98%
PTT Duration: 3.5s
Processing Time: 0.8s
```

## Keyboard Shortcut Display

### Platform-Adaptive Display
```python
def format_key_combo(keys: list, platform: str) -> str:
    """Format key combination for platform"""

    symbols = {
        "Darwin": {
            "cmd": "⌘",
            "alt": "⌥",
            "shift": "⇧",
            "ctrl": "⌃",
            "down": "↓",
            "right": "→"
        },
        "Windows": {
            "cmd": "Win",
            "alt": "Alt",
            "shift": "Shift",
            "ctrl": "Ctrl",
            "down": "↓",
            "right": "→"
        },
        "Linux": {
            "cmd": "Super",
            "alt": "Alt",
            "shift": "Shift",
            "ctrl": "Ctrl",
            "down": "↓",
            "right": "→"
        }
    }

    platform_symbols = symbols.get(platform, symbols["Linux"])
    formatted = " + ".join([platform_symbols.get(k, k) for k in keys])

    return f"[{formatted}]"

# Examples:
# macOS:   [⌘ + ⇧]
# Windows: [Ctrl + Space]
# Linux:   [Alt + Shift]
```

## Accessibility Features

### Screen Reader Support
```python
# Announce state changes for screen readers
def announce_for_screen_reader(message: str):
    """Output screen reader friendly messages"""

    # Use aria-live regions in web UI
    # For CLI, output clear text
    print(f"\n[Screen Reader]: {message}\n")

# Usage:
announce_for_screen_reader("Recording started. Release keys to stop.")
announce_for_screen_reader("Recording stopped. Processing audio.")
```

### High Contrast Mode
```python
# High contrast color scheme
HIGH_CONTRAST = {
    "recording": "⬤ RECORDING",     # Solid circle
    "waiting": "○ WAITING",         # Empty circle
    "processing": "◈ PROCESSING",   # Diamond
    "error": "✖ ERROR",            # X mark
    "success": "✓ SUCCESS"         # Check mark
}
```

### Keyboard Navigation
```
Tab Navigation Order:
1. Start/Stop PTT
2. Cancel Recording
3. Switch Mode (Hold/Toggle)
4. Configure Keys
5. Help
```

## Progressive Disclosure

### First Time User
```
🎉 Welcome to Push-to-Talk!

This is your first time using PTT. Here's how it works:

1. Press and hold [↓+→] keys together
2. Speak your message
3. Release the keys when done

Would you like a tutorial? [Y/n]
```

### Experienced User
```
🎤 PTT: [↓+→] | ESC to cancel
```

## Status Bar Integration

```python
def render_status_bar(state: dict) -> str:
    """Render PTT status in terminal status bar"""

    parts = []

    # PTT indicator
    if state["ptt_enabled"]:
        parts.append("🎤 PTT")

    # Key combo
    parts.append(f"[{state['key_combo']}]")

    # Recording status
    if state["is_recording"]:
        parts.append(f"🔴 {state['duration']}s")

    # Audio level
    if state["audio_level"]:
        parts.append(render_audio_level_mini(state["audio_level"]))

    return " │ ".join(parts)

# Output: 🎤 PTT │ [↓+→] │ 🔴 3.2s │ ▓▓▓░
```

## Animation and Timing

### Recording Pulse Animation
```python
import itertools

def pulse_animation():
    """Generate pulsing recording indicator"""
    frames = ["🔴", "🟥", "🔴", "⭕"]
    for frame in itertools.cycle(frames):
        yield frame

# Usage:
animator = pulse_animation()
while recording:
    print(f"\r{next(animator)} Recording...", end="", flush=True)
    time.sleep(0.5)
```

### Smooth Progress Bar
```python
def smooth_progress(current: float, total: float) -> str:
    """Render smooth progress bar with sub-character precision"""

    width = 40
    progress = current / total
    filled = int(progress * width)
    partial = int((progress * width - filled) * 8)

    # Unicode block characters for smooth fill
    blocks = " ▏▎▍▌▋▊▉█"
    bar = "█" * filled

    if filled < width:
        bar += blocks[partial]
        bar += "░" * (width - filled - 1)

    return f"[{bar}] {current:.1f}/{total:.1f}s"
```

## Error Recovery UX

### Graceful Degradation
```
┌─────────────────────────────────────────────┐
│ ⚠️ PTT Temporarily Unavailable             │
│                                             │
│ Using standard voice mode.                 │
│ Speak after the beep...                    │
│                                             │
│ [Press P to retry PTT setup]               │
└─────────────────────────────────────────────┘
```

### Inline Help
```
Need help? Common PTT commands:
• Change keys: /ptt config keys
• Toggle mode: /ptt config mode toggle
• Disable PTT: /ptt disable
• Show stats: /ptt stats
```

## Platform-Specific Adaptations

### macOS
- Use native symbols (⌘⌥⇧)
- Reference System Preferences
- Terminal.app specific instructions

### Windows
- Use Windows terminology (Win key)
- Reference Windows Settings
- PowerShell/CMD specific formatting

### Linux
- Detect terminal emulator
- X11/Wayland specific messages
- Distribution-aware instructions