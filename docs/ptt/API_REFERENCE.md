# PTT API Reference

Complete API documentation for the CHATTA Push-to-Talk module.

## Table of Contents

- [Core Classes](#core-classes)
  - [PTTController](#pttcontroller)
  - [PTTStateMachine](#pttstatemachine)
  - [PTTRecorder](#pttrecorder)
  - [AsyncPTTRecorder](#asyncpttrecorder)
  - [KeyboardHandler](#keyboardhandler)
  - [PTTLogger](#pttlogger)
- [Enums](#enums)
  - [PTTState](#pttstate)
- [Factory Functions](#factory-functions)
- [Utility Functions](#utility-functions)
- [Configuration](#configuration)
- [Type Definitions](#type-definitions)

---

## Core Classes

### PTTController

Main orchestration class for PTT functionality.

**Module:** `voice_mode.ptt.controller`

#### Constructor

```python
PTTController(
    key_combo: Optional[str] = None,
    cancel_key: Optional[str] = None,
    on_recording_start: Optional[Callable[[], Any]] = None,
    on_recording_stop: Optional[Callable[[Optional[np.ndarray]], None]] = None,
    on_recording_cancel: Optional[Callable[[], None]] = None,
    logger: Optional[PTTLogger] = None,
    timeout: Optional[float] = None
)
```

**Parameters:**
- `key_combo` (str, optional): Key combination to trigger recording
  - Default: `config.PTT_KEY_COMBO` (usually "down+right")
  - Format: `"key"` or `"mod+key"` or `"key1+key2"`
  - Examples: `"space"`, `"ctrl+r"`, `"down+right"`, `"F12"`

- `cancel_key` (str, optional): Key to cancel recording
  - Default: `config.PTT_CANCEL_KEY` (usually "escape")

- `on_recording_start` (Callable, optional): Callback when recording starts
  - Signature: `async def on_start() -> None` or `def on_start() -> None`
  - Called after recorder successfully starts

- `on_recording_stop` (Callable, optional): Callback when recording stops
  - Signature: `async def on_stop(audio_data: Optional[np.ndarray]) -> None`
  - Parameters:
    - `audio_data`: Numpy array of audio samples, or None if recording failed
    - Shape: `(n_samples,)` for mono
    - Dtype: `int16` by default

- `on_recording_cancel` (Callable, optional): Callback when recording is cancelled
  - Signature: `async def on_cancel() -> None`
  - Called when user cancels or timeout occurs

- `logger` (PTTLogger, optional): Logger instance for event tracking
  - Default: Global PTT logger

- `timeout` (float, optional): Maximum recording duration in seconds
  - Default: `config.PTT_TIMEOUT` (usually 30.0)
  - Set to 0 to disable timeout

**Example:**
```python
from voice_mode.ptt import PTTController

async def handle_audio(audio_data):
    print(f"Got {len(audio_data)} samples")

controller = PTTController(
    key_combo="ctrl+space",
    on_recording_stop=handle_audio,
    timeout=60.0
)
```

#### Properties

##### is_enabled

```python
controller.is_enabled -> bool
```

Returns whether PTT is currently enabled (keyboard listener active).

**Returns:** `bool` - True if enabled, False otherwise

**Example:**
```python
if controller.is_enabled:
    print("PTT is active")
```

---

##### is_recording

```python
controller.is_recording -> bool
```

Returns whether currently recording audio.

**Returns:** `bool` - True if actively recording

**Example:**
```python
if controller.is_recording:
    print(f"Recording... {controller.current_state_name}")
```

---

##### current_state

```python
controller.current_state -> PTTState
```

Get current state machine state as enum.

**Returns:** `PTTState` enum value

**Example:**
```python
if controller.current_state == PTTState.RECORDING:
    print("Recording in progress")
```

---

##### current_state_name

```python
controller.current_state_name -> str
```

Get current state as human-readable string.

**Returns:** `str` - State name (e.g., "RECORDING", "IDLE")

**Example:**
```python
print(f"Current state: {controller.current_state_name}")
```

#### Methods

##### enable()

```python
controller.enable() -> bool
```

Enable PTT mode and start keyboard listener.

**Returns:** `bool` - True if successfully enabled, False if already enabled or error

**Side Effects:**
- Creates and starts keyboard listener
- Transitions state machine to WAITING_FOR_KEY
- Sets `_enabled` flag to True

**Example:**
```python
if controller.enable():
    print("PTT enabled successfully")
else:
    print("Failed to enable PTT")
```

**Errors:**
- Returns False if keyboard listener fails to start
- Returns False if already enabled
- Logs error events on failure

---

##### disable()

```python
controller.disable() -> bool
```

Disable PTT mode and stop keyboard listener.

**Returns:** `bool` - True if successfully disabled, False if not enabled

**Side Effects:**
- Stops keyboard listener
- Cancels any active recording
- Transitions state machine to IDLE
- Sets `_enabled` flag to False

**Example:**
```python
controller.disable()
print("PTT disabled")
```

**Errors:**
- Returns False if not currently enabled
- Logs errors if cleanup fails (but still disables)

---

##### wait_for_event()

```python
async controller.wait_for_event(
    timeout: Optional[float] = None
) -> Optional[Dict[str, Any]]
```

Wait for next PTT event from the event queue.

**Parameters:**
- `timeout` (float, optional): Maximum time to wait in seconds
  - Default: None (wait indefinitely)

**Returns:** `Optional[Dict[str, Any]]`
- Event dictionary if event received
- None if timeout occurs

**Event Types:**
```python
{
    "type": "start_recording",
    "timestamp": float
}

{
    "type": "stop_recording",
    "timestamp": float
}

{
    "type": "cancel_recording",
    "timestamp": float
}
```

**Example:**
```python
event = await controller.wait_for_event(timeout=1.0)
if event:
    print(f"Event: {event['type']} at {event['timestamp']}")
else:
    print("No event within timeout")
```

**Usage Pattern:**
```python
# Event-driven loop
while controller.is_enabled:
    event = await controller.wait_for_event(timeout=1.0)
    if event and event["type"] == "start_recording":
        await controller._handle_start_recording(event)
```

---

##### get_status()

```python
controller.get_status() -> Dict[str, Any]
```

Get current PTT controller status snapshot.

**Returns:** `Dict[str, Any]` with keys:
```python
{
    "enabled": bool,           # PTT enabled?
    "state": str,              # Current state name
    "is_recording": bool,      # Currently recording?
    "key_combo": str,          # Configured key combination
    "cancel_key": str,         # Configured cancel key
    "timeout": float,          # Configured timeout
    "mode": str,               # PTT mode (hold/toggle/hybrid)
    "toggle_active": bool      # Toggle mode flag (toggle mode only)
}
```

**Example:**
```python
status = controller.get_status()
print(f"Enabled: {status['enabled']}")
print(f"State: {status['state']}")
print(f"Mode: {status['mode']}")
```

---

### PTTStateMachine

State machine for managing PTT lifecycle.

**Module:** `voice_mode.ptt.state_machine`

#### Constructor

```python
PTTStateMachine(
    initial_state: PTTState = PTTState.IDLE,
    logger: Optional[PTTLogger] = None,
    on_state_change: Optional[Callable] = None
)
```

**Parameters:**
- `initial_state` (PTTState): Starting state (default: IDLE)
- `logger` (PTTLogger, optional): Logger for state transitions
- `on_state_change` (Callable, optional): Callback on state changes
  - Signature: `def callback(from_state, to_state, trigger)`

#### Properties

##### current_state

```python
state_machine.current_state -> PTTState
```

Get current state as enum.

##### current_state_name

```python
state_machine.current_state_name -> str
```

Get current state as string.

#### Methods

##### transition()

```python
state_machine.transition(
    to_state: PTTState,
    trigger: str = "unknown"
) -> None
```

Attempt state transition.

**Parameters:**
- `to_state` (PTTState): Target state
- `trigger` (str): Reason for transition (for logging)

**Raises:**
- `ValueError`: If transition is invalid

**Valid Transitions:**
```python
IDLE → WAITING_FOR_KEY
WAITING_FOR_KEY → KEY_PRESSED | IDLE
KEY_PRESSED → RECORDING | IDLE
RECORDING → RECORDING_STOPPED | RECORDING_CANCELLED
RECORDING_STOPPED → PROCESSING | IDLE
RECORDING_CANCELLED → IDLE
PROCESSING → IDLE
```

**Example:**
```python
try:
    state_machine.transition(PTTState.RECORDING, trigger="key_pressed")
except ValueError as e:
    print(f"Invalid transition: {e}")
```

---

##### is_recording()

```python
state_machine.is_recording() -> bool
```

Check if currently in recording state.

**Returns:** `bool` - True if state is RECORDING

---

##### can_transition()

```python
state_machine.can_transition(to_state: PTTState) -> bool
```

Check if transition to target state is valid.

**Parameters:**
- `to_state` (PTTState): Target state to check

**Returns:** `bool` - True if transition is allowed

**Example:**
```python
if state_machine.can_transition(PTTState.RECORDING):
    state_machine.transition(PTTState.RECORDING)
```

---

### PTTRecorder

Synchronous audio recorder for PTT.

**Module:** `voice_mode.ptt.recorder`

#### Constructor

```python
PTTRecorder(
    sample_rate: int = 16000,
    channels: int = 1,
    dtype: str = 'int16',
    logger: Optional[PTTLogger] = None
)
```

**Parameters:**
- `sample_rate` (int): Audio sample rate in Hz (default: 16000)
- `channels` (int): Number of audio channels (default: 1 = mono)
- `dtype` (str): Audio data type (default: 'int16')
- `logger` (PTTLogger, optional): Logger instance

#### Properties

##### is_recording

```python
recorder.is_recording -> bool
```

Check if currently recording.

##### duration

```python
recorder.duration -> float
```

Get current recording duration in seconds.

#### Methods

##### start()

```python
recorder.start() -> bool
```

Start recording audio.

**Returns:** `bool` - True if started successfully, False if already recording

---

##### stop()

```python
recorder.stop() -> Optional[np.ndarray]
```

Stop recording and return audio data.

**Returns:** `Optional[np.ndarray]`
- Audio samples as numpy array if successful
- Empty array if no audio captured
- None if not recording

**Array Properties:**
- Shape: `(n_samples,)` for mono, `(n_samples, channels)` for stereo
- Dtype: As configured (default `int16`)

---

##### cancel()

```python
recorder.cancel() -> None
```

Cancel recording without returning audio data.

**Side Effects:**
- Stops recording
- Discards all audio chunks
- Clears internal buffers

---

### AsyncPTTRecorder

Asynchronous wrapper around PTTRecorder.

**Module:** `voice_mode.ptt.recorder`

#### Constructor

```python
AsyncPTTRecorder(
    sample_rate: int = 16000,
    channels: int = 1,
    dtype: str = 'int16',
    logger: Optional[PTTLogger] = None
)
```

Same parameters as `PTTRecorder`.

#### Properties

Same as `PTTRecorder`: `is_recording`, `duration`

#### Methods

##### start()

```python
await recorder.start() -> bool
```

Async version of start().

---

##### stop()

```python
await recorder.stop() -> Optional[np.ndarray]
```

Async version of stop().

---

##### cancel()

```python
await recorder.cancel() -> None
```

Async version of cancel().

---

### KeyboardHandler

Cross-platform keyboard event handler.

**Module:** `voice_mode.ptt.keyboard`

#### Constructor

```python
KeyboardHandler(
    key_combo: str,
    on_press_callback: Optional[Callable] = None,
    on_release_callback: Optional[Callable] = None
)
```

**Parameters:**
- `key_combo` (str): Key combination to monitor
- `on_press_callback` (Callable, optional): Called when combo pressed
- `on_release_callback` (Callable, optional): Called when combo released

#### Methods

##### start()

```python
handler.start() -> bool
```

Start keyboard listener.

**Returns:** `bool` - True if started successfully

---

##### stop()

```python
handler.stop() -> None
```

Stop keyboard listener.

---

### PTTLogger

Event logging system for PTT.

**Module:** `voice_mode.ptt.logging`

#### Constructor

```python
PTTLogger()
```

Creates a new logger instance.

#### Methods

##### log_event()

```python
logger.log_event(
    event_type: str,
    data: Optional[Dict[str, Any]] = None
) -> None
```

Log a PTT event.

**Parameters:**
- `event_type` (str): Type of event (e.g., "recording_started")
- `data` (dict, optional): Event metadata

**Example:**
```python
logger.log_event("custom_event", {
    "key": "value",
    "duration": 1.5
})
```

---

##### log_error()

```python
logger.log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> None
```

Log an error event.

**Parameters:**
- `error` (Exception): The exception that occurred
- `context` (dict, optional): Additional context

**Example:**
```python
try:
    # ... code ...
except Exception as e:
    logger.log_error(e, {"operation": "start_recording"})
```

---

##### get_events()

```python
logger.get_events(
    event_type: Optional[str] = None,
    since: Optional[float] = None
) -> List[PTTEvent]
```

Retrieve logged events.

**Parameters:**
- `event_type` (str, optional): Filter by event type
- `since` (float, optional): Only events after this timestamp

**Returns:** `List[PTTEvent]` - List of event objects

**Example:**
```python
# All events
all_events = logger.get_events()

# Only errors
errors = logger.get_events(event_type="error")

# Recent events
import time
recent = logger.get_events(since=time.time() - 60)  # Last minute
```

---

##### clear()

```python
logger.clear() -> None
```

Clear all logged events.

---

## Enums

### PTTState

State machine states.

**Module:** `voice_mode.ptt.state_machine`

#### Values

```python
class PTTState(Enum):
    IDLE = "IDLE"                           # Not active
    WAITING_FOR_KEY = "WAITING_FOR_KEY"     # Waiting for key press
    KEY_PRESSED = "KEY_PRESSED"             # Key detected, validating
    RECORDING = "RECORDING"                 # Actively recording
    RECORDING_STOPPED = "RECORDING_STOPPED" # Stopped normally
    RECORDING_CANCELLED = "RECORDING_CANCELLED"  # Cancelled
    PROCESSING = "PROCESSING"               # Processing audio
```

**Usage:**
```python
from voice_mode.ptt import PTTState

if state == PTTState.RECORDING:
    print("Currently recording")
```

---

## Factory Functions

### create_ptt_controller()

```python
create_ptt_controller(
    key_combo: Optional[str] = None,
    logger: Optional[PTTLogger] = None,
    timeout: Optional[float] = None
) -> PTTController
```

Factory function to create PTT controller with defaults from config.

**Returns:** Configured `PTTController` instance

**Example:**
```python
from voice_mode.ptt import create_ptt_controller

controller = create_ptt_controller(key_combo="space")
```

---

### create_ptt_state_machine()

```python
create_ptt_state_machine(
    logger: Optional[PTTLogger] = None
) -> PTTStateMachine
```

Factory function to create state machine.

---

### create_ptt_recorder()

```python
create_ptt_recorder(
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None,
    logger: Optional[PTTLogger] = None
) -> PTTRecorder
```

Factory function to create synchronous recorder.

---

### create_async_ptt_recorder()

```python
create_async_ptt_recorder(
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None,
    logger: Optional[PTTLogger] = None
) -> AsyncPTTRecorder
```

Factory function to create async recorder.

---

## Utility Functions

### get_ptt_logger()

```python
get_ptt_logger() -> PTTLogger
```

Get global PTT logger instance (singleton).

**Returns:** Global `PTTLogger`

**Example:**
```python
from voice_mode.ptt import get_ptt_logger

logger = get_ptt_logger()
events = logger.get_events()
```

---

### reset_ptt_logger()

```python
reset_ptt_logger() -> PTTLogger
```

Reset global logger (clear all events) and return it.

**Returns:** Global `PTTLogger` (cleared)

---

### check_keyboard_permissions()

```python
check_keyboard_permissions() -> bool
```

Check if application has keyboard monitoring permissions.

**Returns:** `bool` - True if permissions granted

**Platform Notes:**
- **macOS**: Requires Accessibility permissions
- **Linux**: May require input group membership or root
- **Windows**: Usually works without special permissions

**Example:**
```python
from voice_mode.ptt import check_keyboard_permissions

if not check_keyboard_permissions():
    print("Please grant keyboard permissions in System Preferences")
```

---

## Configuration

### Environment Variables

```python
# Mode
PTT_MODE = "hold"  # "hold" | "toggle" | "hybrid"

# Keys
PTT_KEY_COMBO = "down+right"
PTT_CANCEL_KEY = "escape"

# Timing
PTT_TIMEOUT = 30.0          # Max duration (seconds)
PTT_MIN_DURATION = 0.5      # Min duration (seconds)

# Audio
SILENCE_THRESHOLD_MS = 1000 # Hybrid mode silence timeout
```

### Programmatic Configuration

```python
from voice_mode import config

# Set PTT mode
config.PTT_MODE = "hybrid"

# Set keys
config.PTT_KEY_COMBO = "ctrl+space"
config.PTT_CANCEL_KEY = "escape"

# Set timing
config.PTT_TIMEOUT = 60.0
config.PTT_MIN_DURATION = 0.5

# Set audio
config.SILENCE_THRESHOLD_MS = 1500
```

---

## Type Definitions

### PTTEvent

Event object returned by logger.

```python
@dataclass
class PTTEvent:
    timestamp: float              # Unix timestamp
    event_type: str               # Event type
    data: Dict[str, Any]          # Event data
```

**Example:**
```python
events = logger.get_events()
for event in events:
    print(f"{event.timestamp}: {event.event_type}")
    print(f"  Data: {event.data}")
```

---

### StateTransition

State transition record.

```python
@dataclass
class StateTransition:
    from_state: PTTState
    to_state: PTTState
    trigger: str
    timestamp: float
```

---

## Complete Example

```python
import asyncio
from voice_mode.ptt import (
    PTTController,
    PTTState,
    get_ptt_logger,
    check_keyboard_permissions
)

async def main():
    # Check permissions
    if not check_keyboard_permissions():
        print("Keyboard permissions required!")
        return

    # Create controller with callbacks
    async def on_audio(audio_data):
        if audio_data is not None:
            print(f"Received {len(audio_data)} samples")
            # Process audio...

    controller = PTTController(
        key_combo="ctrl+space",
        on_recording_stop=on_audio,
        timeout=30.0
    )

    # Enable PTT
    if not controller.enable():
        print("Failed to enable PTT")
        return

    print("PTT enabled. Press Ctrl+Space to record.")

    # Event loop
    try:
        while controller.is_enabled:
            event = await controller.wait_for_event(timeout=1.0)

            if not event:
                continue

            if event["type"] == "start_recording":
                await controller._handle_start_recording(event)
                print("🎤 Recording...")

            elif event["type"] == "stop_recording":
                await controller._handle_stop_recording(event)
                print("⏹️  Stopped")

            elif event["type"] == "cancel_recording":
                await controller._handle_cancel_recording(event)
                print("❌ Cancelled")

    finally:
        controller.disable()
        print("PTT disabled")

if __name__ == "__main__":
    asyncio.run(main())
```

---

**Last Updated:** 2025-11-09
**Version:** 0.1.0
**Phase:** 3 Complete
