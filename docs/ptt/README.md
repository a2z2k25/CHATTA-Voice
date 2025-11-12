# Push-to-Talk (PTT) Module Documentation

**Version:** 0.2.0
**Status:** Phase 4 Complete (Transport Integration)

## Overview

The PTT module provides keyboard-controlled voice recording for CHATTA, allowing users to control when audio recording starts and stops via configurable key combinations. This gives users better control over conversation cadence compared to automatic microphone triggering.

## Features

### Three Operating Modes

1. **Hold Mode** (Classic Push-to-Talk)
   - Press and hold key combination to record
   - Release to stop recording
   - Enforces minimum duration to prevent accidental quick presses
   - Best for: Quick, controlled recordings

2. **Toggle Mode** (Hands-Free)
   - Press once to start recording
   - Press again to stop recording
   - Hands-free after initial press
   - Best for: Longer recordings, accessibility

3. **Hybrid Mode** (Smart)
   - Hold key to record (like hold mode)
   - Automatically stops on silence detection
   - Combines manual control with smart automation
   - Best for: Natural conversation flow

### Key Features

- **Cross-Platform Keyboard Monitoring** - Works on macOS, Windows, Linux
- **State Machine Architecture** - 7-state lifecycle with validation
- **Error Recovery** - Exponential backoff retry logic
- **Timeout Protection** - Configurable maximum recording duration
- **Resource Cleanup** - Automatic cleanup on cancel, disable, or error
- **Comprehensive Logging** - Detailed event tracking for debugging

## Architecture

### Component Overview

```
PTTController
├── KeyboardHandler      # Cross-platform keyboard monitoring
├── PTTStateMachine      # 7-state lifecycle management
├── AsyncPTTRecorder     # Audio recording with sounddevice
└── PTTLogger           # Event logging and diagnostics
```

### State Machine

```
IDLE
  ↓ (enable)
WAITING_FOR_KEY
  ↓ (key press)
KEY_PRESSED
  ↓ (start recording)
RECORDING
  ↓ (key release / silence / timeout)
RECORDING_STOPPED  or  RECORDING_CANCELLED
  ↓
PROCESSING
  ↓
IDLE
```

### Event Flow

```
User Action → Keyboard Handler → Event Queue → Controller → State Machine
                                      ↓
                                  Recorder
                                      ↓
                                 Audio Data
```

## Installation

The PTT module is included in CHATTA's voice_mode package:

```bash
pip install sounddevice numpy pynput
```

## Quick Start

### Basic Usage

```python
from voice_mode.ptt import PTTController

# Create controller with defaults
controller = PTTController()

# Enable PTT
controller.enable()

# Wait for user to press key combo and record...
# (Controller handles all events internally)

# Disable when done
controller.disable()
```

### With Callbacks

```python
from voice_mode.ptt import PTTController

async def on_start():
    print("Recording started!")

async def on_stop(audio_data):
    print(f"Recording stopped! Got {len(audio_data)} samples")
    # Process audio_data...

async def on_cancel():
    print("Recording cancelled")

controller = PTTController(
    key_combo="down+right",      # Arrow keys
    on_recording_start=on_start,
    on_recording_stop=on_stop,
    on_recording_cancel=on_cancel,
    timeout=30.0                 # 30 second max
)

controller.enable()
```

## Configuration

### Environment Variables

```bash
# Mode selection
export PTT_MODE="hold"              # "hold", "toggle", or "hybrid"

# Key combinations
export PTT_KEY_COMBO="down+right"   # Default recording trigger
export PTT_CANCEL_KEY="escape"      # Cancel recording

# Timing
export PTT_TIMEOUT=30.0             # Max recording duration (seconds)
export PTT_MIN_DURATION=0.5         # Min hold duration (seconds)

# Audio
export SILENCE_THRESHOLD_MS=1000    # Hybrid mode silence timeout
```

### Programmatic Configuration

```python
from voice_mode.ptt import PTTController

controller = PTTController(
    key_combo="ctrl+space",      # Custom key combo
    cancel_key="escape",         # Cancel key
    timeout=60.0,                # 60 second max
)
```

## Mode Comparison

| Feature | Hold Mode | Toggle Mode | Hybrid Mode |
|---------|-----------|-------------|-------------|
| Manual Control | ✅ Full | ⚠️ Start/Stop | ✅ Full |
| Hands-Free | ❌ No | ✅ Yes | ⚠️ After Release |
| Auto-Stop | ❌ No | ❌ No | ✅ On Silence |
| Min Duration | ✅ Yes | ❌ No | ✅ Yes |
| Best For | Quick inputs | Long recordings | Natural speech |
| Accessibility | Medium | High | High |

### When to Use Each Mode

**Hold Mode:**
- Quick voice commands
- Precise control needed
- Noisy environments (no auto-stop)
- User familiar with PTT

**Toggle Mode:**
- Long-form dictation
- Accessibility requirements
- Hands-free operation needed
- Reading from notes

**Hybrid Mode:**
- Natural conversation
- Variable-length responses
- Combination of manual + auto
- Best of both worlds

## API Reference

### PTTController

Main orchestration class for PTT functionality.

#### Constructor

```python
PTTController(
    key_combo: Optional[str] = None,
    cancel_key: Optional[str] = None,
    on_recording_start: Optional[Callable] = None,
    on_recording_stop: Optional[Callable[[np.ndarray], None]] = None,
    on_recording_cancel: Optional[Callable] = None,
    logger: Optional[PTTLogger] = None,
    timeout: Optional[float] = None
)
```

#### Properties

```python
controller.is_enabled -> bool           # PTT currently enabled?
controller.is_recording -> bool         # Currently recording?
controller.current_state -> PTTState    # Current state machine state
controller.current_state_name -> str    # State as string
```

#### Methods

```python
controller.enable() -> bool
    """Enable PTT mode and start keyboard listener."""

controller.disable() -> bool
    """Disable PTT mode and stop keyboard listener."""

async controller.wait_for_event(timeout: float = None) -> Dict[str, Any]
    """Wait for next PTT event (for event-driven usage)."""

controller.get_status() -> Dict[str, Any]
    """Get current status snapshot."""
```

### PTTState

State machine states:

```python
from voice_mode.ptt import PTTState

PTTState.IDLE                 # Not active
PTTState.WAITING_FOR_KEY      # Waiting for user input
PTTState.KEY_PRESSED          # Key detected, validating
PTTState.RECORDING            # Actively recording
PTTState.RECORDING_STOPPED    # Stopped normally
PTTState.RECORDING_CANCELLED  # Cancelled by user/timeout
PTTState.PROCESSING           # Processing audio
```

### PTTRecorder / AsyncPTTRecorder

Audio recording classes (usually not used directly):

```python
from voice_mode.ptt import create_ptt_recorder, create_async_ptt_recorder

# Sync version
recorder = create_ptt_recorder(sample_rate=16000, channels=1)
recorder.start()
audio_data = recorder.stop()

# Async version (recommended)
recorder = create_async_ptt_recorder(sample_rate=16000, channels=1)
await recorder.start()
audio_data = await recorder.stop()
```

### PTTLogger

Event logging for diagnostics:

```python
from voice_mode.ptt import get_ptt_logger, reset_ptt_logger

logger = get_ptt_logger()

# Log custom event
logger.log_event("custom_event", {"key": "value"})

# Log error
try:
    # ... code ...
except Exception as e:
    logger.log_error(e, {"context": "operation"})

# Get all events
events = logger.get_events()

# Reset logger
reset_ptt_logger()
```

## Usage Examples

### Example 1: Hold Mode with Status Monitoring

```python
from voice_mode.ptt import PTTController
from voice_mode import config

# Configure hold mode
config.PTT_MODE = "hold"
config.PTT_MIN_DURATION = 0.5  # Must hold for 500ms

controller = PTTController(
    key_combo="ctrl+space",
    timeout=30.0
)

controller.enable()
print(f"PTT enabled. Press {controller._key_combo} to record.")

# Monitor status
while controller.is_enabled:
    status = controller.get_status()
    if status['is_recording']:
        print(f"Recording... {status['state']}")
    await asyncio.sleep(0.1)
```

### Example 2: Toggle Mode with Async Callbacks

```python
from voice_mode.ptt import PTTController
from voice_mode import config

config.PTT_MODE = "toggle"

async def process_audio(audio_data):
    if audio_data is not None:
        print(f"Processing {len(audio_data)} audio samples")
        # Send to STT service...
        await transcribe_audio(audio_data)

controller = PTTController(
    key_combo="F9",
    on_recording_stop=process_audio,
    timeout=120.0  # 2 minute max for long dictation
)

controller.enable()
print("Press F9 to start, F9 again to stop")

# Keep alive
while True:
    await asyncio.sleep(1)
```

### Example 3: Hybrid Mode with Silence Detection

```python
from voice_mode.ptt import PTTController
from voice_mode import config

# Configure hybrid mode
config.PTT_MODE = "hybrid"
config.PTT_MIN_DURATION = 0.5
config.SILENCE_THRESHOLD_MS = 1500  # 1.5 seconds of silence

controller = PTTController(
    key_combo="down+right",
    timeout=60.0
)

controller.enable()
print("Hold down+right arrows to speak.")
print("Release or stay silent for 1.5s to stop.")

# Event-driven loop
while controller.is_enabled:
    event = await controller.wait_for_event(timeout=1.0)
    if event:
        print(f"Event: {event['type']}")
```

### Example 4: Event-Driven Architecture

```python
from voice_mode.ptt import PTTController
import asyncio

async def ptt_event_loop():
    controller = PTTController(key_combo="space")
    controller.enable()

    try:
        while controller.is_enabled:
            event = await controller.wait_for_event(timeout=1.0)

            if not event:
                continue

            event_type = event.get("type")

            if event_type == "start_recording":
                await controller._handle_start_recording(event)
                print("🎤 Recording started")

            elif event_type == "stop_recording":
                await controller._handle_stop_recording(event)
                print("⏹️  Recording stopped")

            elif event_type == "cancel_recording":
                await controller._handle_cancel_recording(event)
                print("❌ Recording cancelled")

    finally:
        controller.disable()

asyncio.run(ptt_event_loop())
```

### Example 5: Custom Key Combinations

```python
from voice_mode.ptt import PTTController

# Single key
controller = PTTController(key_combo="F12")

# Modifier + key
controller = PTTController(key_combo="ctrl+r")

# Multiple modifiers
controller = PTTController(key_combo="ctrl+shift+r")

# Multiple keys (chord)
controller = PTTController(key_combo="down+right")

# Cancel key
controller = PTTController(
    key_combo="space",
    cancel_key="escape"
)
```

## Error Handling

### Built-in Error Recovery

The PTT controller includes automatic error recovery:

```python
# Automatic retry with exponential backoff
controller = PTTController()
controller._max_retries = 3  # Default

# Errors are logged but don't crash
controller.enable()  # Returns False on failure, doesn't raise
```

### Manual Error Handling

```python
from voice_mode.ptt import PTTController, get_ptt_logger

controller = PTTController()
logger = get_ptt_logger()

if not controller.enable():
    print("Failed to enable PTT")
    errors = [e for e in logger.get_events() if e.event_type == "error"]
    for error in errors:
        print(f"Error: {error.data}")
    exit(1)

# Monitor for errors during operation
while controller.is_enabled:
    status = controller.get_status()
    if status['state'] == 'IDLE' and not status['enabled']:
        # Something went wrong
        errors = [e for e in logger.get_events() if e.event_type == "error"]
        print(f"Errors detected: {len(errors)}")
        break
```

## Troubleshooting

### Keyboard Permissions

**macOS:**
```bash
# Grant accessibility permissions to your terminal
System Preferences → Security & Privacy → Privacy → Accessibility
# Add Terminal.app or your IDE
```

**Linux:**
```bash
# May need to run with elevated permissions
sudo python your_script.py
# Or add user to input group
sudo usermod -a -G input $USER
```

**Windows:**
- Usually works without special permissions
- May need to run as Administrator for some key combinations

### Audio Device Issues

```python
# Check available audio devices
from voice_mode.ptt import check_audio_devices

devices = check_audio_devices()
print(devices)
```

### Debugging Events

```python
from voice_mode.ptt import get_ptt_logger

logger = get_ptt_logger()

# Enable detailed logging
controller = PTTController(logger=logger)
controller.enable()

# After operation, review events
for event in logger.get_events():
    print(f"{event.timestamp}: {event.event_type} - {event.data}")
```

### Common Issues

**Issue:** Keys not detected
- Check keyboard permissions
- Try different key combination
- Verify key combination format (e.g., "ctrl+space", not "control+space")

**Issue:** Recording starts but doesn't stop
- Check timeout setting
- Verify key release is detected
- For toggle mode, ensure second press is registered

**Issue:** Hybrid mode doesn't auto-stop
- Verify SILENCE_THRESHOLD_MS is set
- Check audio device is working
- Ensure voice activity detection is enabled

## Testing

### Running Tests

```bash
# All PTT tests
uv run pytest tests/unit/ptt/ -v

# Integration tests only
uv run pytest tests/integration/ptt/ -v

# Specific test file
uv run pytest tests/unit/ptt/test_controller.py -v
```

### Test Coverage

Current test coverage (Phase 3 complete):
- Unit tests: 125 tests across 7 test files
- Integration tests: 18 tests
- Total: 143 tests, 100% passing
- Code coverage: ~95% (estimated)

## Performance

### Resource Usage

- **CPU**: Minimal (<1% during idle, <5% during recording)
- **Memory**: ~50MB base + audio buffer
- **Audio Buffer**: ~2MB per minute of recording (16kHz mono)

### Latency

- **Key Detection**: <10ms
- **Recording Start**: <50ms
- **Recording Stop**: <100ms
- **State Transitions**: <5ms

## Future Enhancements

### Completed Phases

- ✅ **Phase 1-3:** Core PTT implementation (state machine, keyboard handling, audio recording)
- ✅ **Phase 4:** Integration with CHATTA voice transport (34/34 tests passing)

### Planned Phases

- **Phase 5:** Enhanced features (visual feedback, audio cues, statistics, UX improvements)
- **Phase 6:** Comprehensive cross-platform testing
- **Phase 7:** User documentation and examples
- **Phase 8:** Production deployment preparation
- **Phase 9:** Monitoring and continuous improvement

## Contributing

### Code Style

- Follow PEP 8
- Type hints required for all public APIs
- Docstrings required (Google style)
- 100% test coverage for new features

### Testing Requirements

- Unit tests for all new functions
- Integration tests for workflows
- Manual testing on all platforms
- Performance regression testing

## License

Part of the CHATTA project. See main LICENSE file.

## Support

- GitHub Issues: https://github.com/your-org/CHATTA/issues
- Documentation: https://docs.chatta.ai/ptt
- Discord: https://discord.gg/chatta

---

**Last Updated:** 2025-11-09
**Phase:** 4 Complete (Transport Integration)
**Next Phase:** 5 (Enhanced Features)
