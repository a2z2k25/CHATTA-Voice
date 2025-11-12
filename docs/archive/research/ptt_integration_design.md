# PTT Integration Design - Converse Tool Integration
Date: November 9, 2025
Sprint: 1.4

## Integration Architecture

### Current Converse Tool Flow
```
converse(message, wait_for_response=True)
    ├─ TTS Phase (speak message)
    ├─ Recording Phase (if wait_for_response)
    │   ├─ Play start chime
    │   ├─ Record with silence detection
    │   └─ Play end chime
    └─ STT Phase (transcribe)
```

### Enhanced PTT Flow
```
converse(message, wait_for_response=True, push_to_talk=False)
    ├─ TTS Phase (speak message)
    ├─ PTT Decision Point
    │   ├─ [PTT=True] → PTT Recording Flow
    │   │   ├─ Show PTT prompt
    │   │   ├─ Wait for key press
    │   │   ├─ Record while held
    │   │   └─ Stop on release
    │   └─ [PTT=False] → Standard Recording Flow
    └─ STT Phase (transcribe)
```

## Parameter Additions to Converse Tool

```python
@tool
async def converse(
    message: str,
    wait_for_response: bool = True,

    # New PTT parameters
    push_to_talk: bool = False,
    ptt_key_combo: Optional[str] = None,  # e.g., "cmd+shift", "down+right"
    ptt_mode: str = "hold",  # "hold", "toggle", "hybrid"
    ptt_timeout: float = 120.0,  # Max recording time in PTT mode

    # Existing parameters remain unchanged
    listen_duration: float = 120.0,
    min_listen_duration: float = 2.0,
    transport: str = "auto",
    room_name: str = "",
    voice: Optional[str] = None,
    # ... other existing parameters
) -> str:
    """
    Enhanced converse with Push-to-Talk support.

    New Parameters:
    - push_to_talk: Enable PTT mode instead of auto-recording
    - ptt_key_combo: Key combination to trigger recording (uses config default if None)
    - ptt_mode: "hold" (record while held), "toggle" (press to start/stop), "hybrid"
    - ptt_timeout: Maximum recording duration in PTT mode
    """
```

## Integration Points

### 1. Configuration Integration
```python
# In config.py, add:
CHATTA_PTT_ENABLED = get_bool_env("CHATTA_PTT_ENABLED", False)
CHATTA_PTT_KEY_COMBO = get_str_env("CHATTA_PTT_KEY_COMBO", "down+right")
CHATTA_PTT_MODE = get_str_env("CHATTA_PTT_MODE", "hold")  # hold, toggle, hybrid
CHATTA_PTT_TIMEOUT = get_float_env("CHATTA_PTT_TIMEOUT", 120.0)
CHATTA_PTT_FEEDBACK = get_bool_env("CHATTA_PTT_FEEDBACK", True)
CHATTA_PTT_CANCEL_KEY = get_str_env("CHATTA_PTT_CANCEL_KEY", "escape")
```

### 2. Recording Function Integration
```python
# In converse.py, modify recording section:

if wait_for_response:
    if push_to_talk:
        # PTT-specific recording flow
        from voice_mode.ptt import PTTController

        ptt = PTTController(
            key_combo=ptt_key_combo or config.CHATTA_PTT_KEY_COMBO,
            mode=ptt_mode,
            timeout=ptt_timeout
        )

        # Show PTT-specific prompt
        print(f"\n🎤 Press and hold {ptt.key_combo_display} to speak...")

        # Different from standard: no automatic start chime
        # Chime plays when keys are pressed

        audio_data, speech_detected = await ptt.record_with_ptt()

    else:
        # Existing recording flow
        if audio_feedback:
            await play_chime_start()

        audio_data, speech_detected = await record_audio_with_silence_detection(
            listen_duration=listen_duration,
            min_listen_duration=min_listen_duration,
            disable_silence_detection=disable_silence_detection
        )

        if audio_feedback:
            await play_chime_end()
```

### 3. Transport Compatibility
```python
class PTTTransportAdapter:
    """Adapt PTT for different transports"""

    def __init__(self, transport: str):
        self.transport = transport

    def is_ptt_compatible(self) -> tuple[bool, str]:
        """Check if transport supports PTT"""
        compatibility = {
            "local": (True, "Full PTT support"),
            "livekit": (False, "PTT not available with LiveKit - using standard mode"),
            "auto": (True, "PTT will use local transport")
        }
        return compatibility.get(self.transport, (False, "Unknown transport"))

    def get_recommended_transport(self, ptt_enabled: bool) -> str:
        """Get best transport for PTT"""
        if ptt_enabled and self.transport == "auto":
            return "local"  # Prefer local for PTT
        return self.transport
```

### 4. Backward Compatibility

```python
class BackwardCompatibilityLayer:
    """Ensure existing code continues to work"""

    @staticmethod
    def validate_parameters(kwargs: dict) -> dict:
        """Ensure new params don't break old calls"""

        # Default PTT to False for backward compatibility
        if "push_to_talk" not in kwargs:
            kwargs["push_to_talk"] = False

        # If PTT is enabled but transport is LiveKit, warn and disable
        if kwargs.get("push_to_talk") and kwargs.get("transport") == "livekit":
            logging.warning("PTT not supported with LiveKit, falling back to standard mode")
            kwargs["push_to_talk"] = False

        return kwargs
```

### 5. Event Logging Integration
```python
# Extend existing event logging for PTT events

def log_ptt_event(event_type: str, data: dict):
    """Log PTT-specific events"""
    event = {
        "timestamp": time.time(),
        "type": f"ptt_{event_type}",
        "data": data
    }

    # Write to existing conversation log
    if config.CHATTA_EVENT_LOGGING:
        with open(get_event_log_path(), "a") as f:
            f.write(json.dumps(event) + "\n")
```

### 6. Statistics Integration
```python
# Add PTT metrics to voice_statistics.py

class PTTStatistics:
    """Track PTT-specific metrics"""

    def __init__(self):
        self.ptt_sessions = 0
        self.total_key_hold_time = 0.0
        self.cancelled_recordings = 0
        self.successful_recordings = 0
        self.key_press_latencies = []

    def to_dict(self) -> dict:
        return {
            "ptt_enabled": True,
            "total_sessions": self.ptt_sessions,
            "avg_hold_time": self.total_key_hold_time / max(1, self.ptt_sessions),
            "cancellation_rate": self.cancelled_recordings / max(1, self.ptt_sessions),
            "avg_response_time": statistics.mean(self.key_press_latencies) if self.key_press_latencies else 0
        }
```

## File Structure Changes

```
voice_mode/
├── tools/
│   ├── converse.py          # Modified with PTT support
│   └── ptt/                 # New PTT module
│       ├── __init__.py
│       ├── controller.py    # Main PTT controller
│       ├── keyboard.py      # Keyboard handling
│       ├── permissions.py   # Permission management
│       └── recorder.py      # PTT-specific recording
├── config.py                # Add PTT configuration
└── audio/
    ├── ptt_ready.wav       # New PTT-specific sounds
    └── ptt_activated.wav
```

## API Compatibility Matrix

| Scenario | Behavior |
|----------|----------|
| Existing code, no PTT params | Works identically (PTT disabled) |
| PTT=True with local transport | Full PTT functionality |
| PTT=True with LiveKit | Falls back to standard mode with warning |
| PTT=True, no permissions | Falls back to standard mode with message |
| Invalid key combo | Uses default from config |
| PTT timeout exceeded | Automatically stops recording |

## Migration Path

### Phase 1: Soft Launch (Current Design)
- PTT disabled by default
- Opt-in via parameter or config
- Full backward compatibility
- No breaking changes

### Phase 2: Gradual Adoption
- Add PTT to documentation
- Include in examples
- Monitor usage metrics
- Gather feedback

### Phase 3: Potential Future Default
- Based on user feedback
- Could become default for local transport
- Always optional

## Testing Integration Points

```python
# Test cases to ensure integration works

async def test_ptt_backward_compatibility():
    """Existing code still works"""
    result = await converse("Test message")
    assert result  # Should work without PTT params

async def test_ptt_parameter_addition():
    """New parameters work correctly"""
    result = await converse(
        "Test message",
        push_to_talk=True,
        ptt_key_combo="ctrl+space"
    )
    assert "Press and hold" in captured_output

async def test_ptt_transport_fallback():
    """PTT falls back gracefully with LiveKit"""
    result = await converse(
        "Test",
        push_to_talk=True,
        transport="livekit"
    )
    assert "PTT not available" in captured_logs

async def test_ptt_config_override():
    """Config can be overridden by parameters"""
    os.environ["CHATTA_PTT_KEY_COMBO"] = "alt+shift"
    result = await converse(
        "Test",
        push_to_talk=True,
        ptt_key_combo="ctrl+space"  # Should override config
    )
    assert "ctrl+space" in captured_output
```

## Performance Considerations

- PTT adds ~50-100ms initialization overhead (keyboard listener)
- No performance impact when PTT disabled
- Memory: Additional ~10MB for keyboard library
- CPU: Negligible (<1% for keyboard monitoring)

## Security Considerations

- Keyboard monitoring only active during PTT session
- No keystroke logging beyond PTT keys
- Permissions checked before activation
- Clear user consent required