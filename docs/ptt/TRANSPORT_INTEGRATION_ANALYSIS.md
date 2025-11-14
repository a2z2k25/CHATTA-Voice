# PTT Transport Integration Analysis

**Sprint:** Phase 4 Sprint 4.1
**Date:** 2025-11-09
**Status:** Complete

---

## Executive Summary

This document analyzes CHATTA's existing voice transport layer to identify integration points for the Push-to-Talk (PTT) feature. The analysis reveals a clean architecture with two distinct transport modes (local microphone and LiveKit rooms) that can be enhanced with PTT keyboard control.

**Key Finding:** PTT integration requires replacing a single recording call (`record_audio_with_silence_detection()`) with PTT-aware recording while maintaining the existing interface contract.

---

## Current Transport Architecture

### 1. Transport Modes

CHATTA supports three transport modes via the `converse()` tool:

**Mode: "auto" (default)**
- Checks LiveKit availability first
- Falls back to local microphone if LiveKit unavailable
- Selection logic: `converse.py:1801-1812`

**Mode: "local"**
- Direct microphone access via sounddevice
- VAD-based silence detection
- Implementation: `converse.py:1837-2060`

**Mode: "livekit"**
- Room-based real-time communication
- LiveKit Agent framework
- Implementation: `converse.py:1260-1398`

### 2. Local Transport Flow

The local transport follows this sequence:

```
1. TTS: Speak message
   └─ text_to_speech_with_failover()
   └─ Audio playback

2. Pause: Brief 0.5s delay

3. Audio Feedback: Play "listening" chime
   └─ play_audio_feedback("listening")

4. RECORDING: Capture user response ⭐ PTT INTEGRATION POINT
   └─ record_audio_with_silence_detection()
   └─ Parameters: listen_duration, disable_silence_detection, min_listen_duration, vad_aggressiveness
   └─ Returns: (audio_data, speech_detected)

5. Audio Feedback: Play "finished" chime
   └─ play_audio_feedback("finished")

6. STT: Transcribe audio
   └─ speech_to_text()

7. Return: Transcribed text
```

**Implementation Location:** `src/voice_mode/tools/converse.py:1837-2060`

**Critical Recording Call:** Lines 1941-1943
```python
audio_data, speech_detected = await asyncio.get_event_loop().run_in_executor(
    None, record_audio_with_silence_detection, listen_duration,
    disable_silence_detection, min_listen_duration, vad_aggressiveness
)
```

### 3. LiveKit Transport Flow

The LiveKit transport uses a different approach:

```
1. Connect to LiveKit room
2. Create VoiceAgent with TTS/STT clients
3. Agent speaks message on enter
4. Agent listens via LiveKit's built-in VAD
5. Agent processes user speech events
6. Return transcribed response
```

**Implementation Location:** `src/voice_mode/tools/converse.py:1260-1398`

**Key Characteristic:** Uses LiveKit Agent framework which handles recording internally

---

## Recording Functions Analysis

### Current Recording Implementation

**Function: `record_audio_with_silence_detection()`**
- **Location:** `converse.py:946-1226`
- **Purpose:** Record audio with automatic silence detection using WebRTC VAD
- **Signature:**
  ```python
  def record_audio_with_silence_detection(
      max_duration: float = 120.0,
      disable_silence_detection: bool = False,
      min_duration: float = 2.0,
      vad_aggressiveness: int = 2
  ) -> Tuple[np.ndarray, bool]:
  ```
- **Returns:** `(audio_data, speech_detected)` tuple
- **Behavior:**
  - Starts recording immediately (no keyboard trigger)
  - Uses WebRTC VAD for speech detection
  - Stops on: silence threshold OR max duration
  - Minimum duration enforcement
  - Audio device recovery on errors

**Function: `record_audio()`**
- **Location:** `converse.py:834-943`
- **Purpose:** Simple fixed-duration recording (fallback)
- **Signature:**
  ```python
  def record_audio(duration: float = 5.0) -> np.ndarray:
  ```
- **Returns:** Audio data as numpy array
- **Behavior:** Records for exactly `duration` seconds

### Interface Contract

All recording functions must:

1. **Accept** standard parameters:
   - `max_duration` / `duration`: Maximum recording time
   - `disable_silence_detection`: Flag to disable VAD
   - `min_duration`: Minimum recording duration
   - `vad_aggressiveness`: VAD sensitivity (0-3)

2. **Return** compatible data:
   - Tuple format: `(audio_data, speech_detected)`
   - Audio data: `np.ndarray` with dtype='int16'
   - Sample rate: 16000 Hz (from config.SAMPLE_RATE)
   - Channels: 1 (mono)

3. **Handle** edge cases:
   - Empty recordings: Return `(np.array([]), False)`
   - Audio device errors: Automatic recovery or graceful fallback
   - Cancellation: Clean resource cleanup

---

## PTT Integration Points

### Primary Integration Point: Local Transport Recording

**Location:** `converse.py:1941-1943`

**Current Code:**
```python
audio_data, speech_detected = await asyncio.get_event_loop().run_in_executor(
    None, record_audio_with_silence_detection, listen_duration,
    disable_silence_detection, min_listen_duration, vad_aggressiveness
)
```

**PTT Replacement Strategy:**

Replace with PTT-aware recording function that:
- Waits for keyboard key press before starting recording
- Monitors keyboard state during recording
- Stops based on PTT mode (hold/toggle/hybrid)
- Maintains the same interface contract

**Proposed Code:**
```python
# Determine recording function based on PTT configuration
if config.PTT_ENABLED:
    from voice_mode.ptt import record_with_ptt

    audio_data, speech_detected = await asyncio.get_event_loop().run_in_executor(
        None, record_with_ptt, listen_duration,
        disable_silence_detection, min_listen_duration, vad_aggressiveness
    )
else:
    # Original behavior
    audio_data, speech_detected = await asyncio.get_event_loop().run_in_executor(
        None, record_audio_with_silence_detection, listen_duration,
        disable_silence_detection, min_listen_duration, vad_aggressiveness
    )
```

### Secondary Integration Point: LiveKit Transport

**Location:** `converse.py:1260-1398`

**Current Behavior:** LiveKit Agent handles recording internally via its event system

**PTT Integration Strategy:**

LiveKit PTT requires a different approach:
- Cannot directly control LiveKit's recording via keyboard
- Options:
  1. **Skip PTT for LiveKit** - Keep LiveKit transport as-is (automatic VAD)
  2. **Frontend Integration** - Add PTT controls to LiveKit frontend UI
  3. **Agent Modification** - Extend VoiceAgent with PTT event handling

**Recommendation:** Skip PTT for LiveKit transport in Phase 4
- LiveKit is room-based and designed for real-time multi-user interaction
- PTT is most valuable for local single-user microphone control
- Can add LiveKit PTT in future phase if needed

---

## PTT Mode Mapping

### Configuration Parameters Mapping

| PTT Mode | PTT Config | Converse Parameter Mapping |
|----------|-----------|----------------------------|
| **Hold** | `PTT_MODE="hold"` | `disable_silence_detection=True`<br/>Uses keyboard hold duration as recording duration |
| **Toggle** | `PTT_MODE="toggle"` | `disable_silence_detection=True`<br/>First press starts, second press stops |
| **Hybrid** | `PTT_MODE="hybrid"` | `disable_silence_detection=False`<br/>Keyboard hold + VAD silence detection |

### Mode Behavior

**Hold Mode:**
- User presses key combination → Recording starts
- User holds keys → Recording continues
- User releases keys → Recording stops (if min_duration met)
- Timeout: Still enforced as safety (`listen_duration`)

**Toggle Mode:**
- User presses key combination → Recording starts
- User can release keys → Recording continues
- User presses combination again → Recording stops
- Timeout: Still enforced as safety (`listen_duration`)

**Hybrid Mode:**
- User presses key combination → Recording starts
- User holds keys → Recording continues
- Silence detected → Recording stops automatically
- User releases keys → Recording stops (whichever comes first)
- Combines manual control with automatic silence detection

### Parameter Preservation

All existing `converse()` parameters must continue to work:

- ✅ `listen_duration` → Becomes PTT timeout (max recording time)
- ✅ `disable_silence_detection` → Overrides hybrid mode VAD
- ✅ `min_listen_duration` → Enforced in all PTT modes
- ✅ `vad_aggressiveness` → Used in hybrid mode
- ✅ `wait_for_response` → PTT only applies when True
- ✅ `transport` → PTT only applies to "local" and "auto" (when falling back to local)

---

## Architecture Proposal

### Component Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                      converse() MCP Tool                        │
│                                                                 │
│  Parameters: transport, listen_duration, disable_silence_det... │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴───────────────┐
                │                            │
         ┌──────▼──────┐            ┌────────▼─────────┐
         │   LiveKit   │            │   Local Mic      │
         │  Transport  │            │   Transport      │
         └──────┬──────┘            └────────┬─────────┘
                │                            │
         (Agent VAD)                         │
         No PTT needed              ┌────────▼─────────┐
                                    │  PTT Enabled?    │
                                    └────────┬─────────┘
                                             │
                                    ┌────────┴─────────┐
                                    │        No        │  Yes
                          ┌─────────▼──────┐      ┌───▼────────────────┐
                          │ record_audio_  │      │  record_with_ptt() │
                          │ with_silence_  │      │                    │
                          │ detection()    │      │  ┌──────────────┐  │
                          └────────────────┘      │  │ PTT Adapter  │  │
                                                  │  │              │  │
                                                  │  │ - Hold       │  │
                                                  │  │ - Toggle     │  │
                                                  │  │ - Hybrid     │  │
                                                  │  └──────────────┘  │
                                                  │                    │
                                                  │  ┌──────────────┐  │
                                                  │  │PTT Controller│  │
                                                  │  └──────────────┘  │
                                                  └────────────────────┘
```

### New Component: `record_with_ptt()`

**Location:** `src/voice_mode/ptt/transport_adapter.py` (new file)

**Purpose:** Bridge between converse() transport layer and PTT controller

**Signature:**
```python
def record_with_ptt(
    max_duration: float = 120.0,
    disable_silence_detection: bool = False,
    min_duration: float = 2.0,
    vad_aggressiveness: int = 2
) -> Tuple[np.ndarray, bool]:
    """
    Record audio using PTT keyboard control.

    Maintains interface compatibility with record_audio_with_silence_detection()
    while adding keyboard-triggered recording.

    Args:
        max_duration: Maximum recording duration (becomes PTT timeout)
        disable_silence_detection: Disable VAD (affects hybrid mode)
        min_duration: Minimum recording duration
        vad_aggressiveness: VAD sensitivity for hybrid mode

    Returns:
        (audio_data, speech_detected): Same format as original recording functions
    """
```

**Implementation Strategy:**

1. Create PTTController instance with configured mode
2. Enable controller and wait for key press
3. Start recording when key pressed
4. Monitor for stop condition based on mode:
   - Hold: Key release + min_duration
   - Toggle: Second key press
   - Hybrid: Key release OR silence detection
5. Get audio data from recorder
6. Disable controller and cleanup
7. Return `(audio_data, speech_detected)` tuple

### Configuration Integration

**New Config Variables:**

```python
# src/voice_mode/config.py

# PTT Feature Flag
PTT_ENABLED: bool = env.bool("VOICEMODE_PTT_ENABLED", False)

# PTT is already configured with:
# - PTT_MODE: "hold" | "toggle" | "hybrid"
# - PTT_KEY_COMBO: Key combination (e.g., "down+right")
# - PTT_CANCEL_KEY: Cancel key (e.g., "esc")
# - PTT_TIMEOUT: Maximum recording duration
# - PTT_MIN_DURATION: Minimum recording duration
# - SILENCE_THRESHOLD_MS: Hybrid mode silence threshold
```

**Config Precedence:**

1. Explicit `disable_silence_detection` parameter → Overrides hybrid mode
2. PTT_MODE setting → Determines default behavior
3. Function parameters → Override config defaults

---

## Integration Challenges

### 1. Sync/Async Boundary

**Challenge:** `converse()` is async, but `record_with_ptt()` must be sync (called via `run_in_executor`)

**Solution:**
- Make `record_with_ptt()` synchronous
- Use sync PTTRecorder (not AsyncPTTRecorder)
- Run PTT event loop in blocking manner within executor thread

**Implementation:**
```python
def record_with_ptt(...) -> Tuple[np.ndarray, bool]:
    """Synchronous PTT recording for executor thread"""
    controller = PTTController(...)
    controller.enable()

    # Block until recording completes
    audio_data = _wait_for_recording_sync(controller, max_duration)

    controller.disable()
    return (audio_data, audio_data is not None and len(audio_data) > 0)
```

### 2. Event Queue Integration

**Challenge:** PTTController uses async event queue, but we need sync interface

**Solution:**
- Use `queue.Queue` (thread-safe, blocking) instead of `asyncio.Queue`
- OR implement sync wrapper that polls async queue
- OR use threading.Event for synchronization

**Preferred:** Use sync Queue for executor compatibility

### 3. Audio Feedback Timing

**Challenge:** Audio feedback chimes ("listening", "finished") are currently played around recording

**Current Flow:**
```python
play_audio_feedback("listening")   # Before recording
record_audio_with_silence_detection()
play_audio_feedback("finished")    # After recording
```

**PTT Flow:**
```python
play_audio_feedback("listening")   # Before waiting for key
# [User sees/hears "listening", THEN presses key to start recording]
record_with_ptt()                  # Waits for key, then records
play_audio_feedback("finished")    # After recording
```

**Solution:** Keep current flow, PTT just adds key-press requirement before actual recording starts

### 4. Cancellation

**Challenge:** How does user cancel mid-recording?

**Solutions:**
- Hold/Toggle modes: Press cancel key (config.PTT_CANCEL_KEY, default: "esc")
- Hybrid mode: Release key OR press cancel key
- All modes: Timeout (max_duration) acts as automatic cancel

**Implementation:** PTTController already handles cancel via keyboard handler

### 5. Error Recovery

**Challenge:** Audio device errors during PTT recording

**Solution:** Use same error recovery as `record_audio_with_silence_detection()`:
- Catch device errors
- Attempt sounddevice reinitialization
- Retry once with new device
- Fall back to error message on failure

---

## Testing Strategy

### Unit Tests

**File:** `tests/unit/ptt/test_transport_adapter.py`

Tests for `record_with_ptt()`:
- Interface contract compliance
- Parameter handling (all modes)
- Return value format
- Error handling
- Device recovery
- Cancellation

### Integration Tests

**File:** `tests/integration/ptt/test_transport_integration.py`

Tests for full transport integration:
- PTT enabled vs disabled behavior
- Local transport with PTT
- LiveKit transport (unaffected by PTT)
- Auto transport selection with PTT
- Audio feedback timing
- Conversation flow end-to-end

### Manual Tests

**File:** `tests/manual/test_ptt_conversation.py`

Interactive tests requiring real hardware:
- Hold mode conversation flow
- Toggle mode conversation flow
- Hybrid mode conversation flow
- Cancel during recording
- Device switching during PTT
- Audio feedback perception

---

## Migration Plan

### Phase 4 Sprint Breakdown

**Sprint 4.1: Transport Analysis** ✅ COMPLETE
- Analyze existing transport layer
- Identify integration points
- Document architecture proposal

**Sprint 4.2: Adapter Pattern** (Next)
- Create `transport_adapter.py` with `record_with_ptt()`
- Implement sync/async bridge
- Add configuration integration
- Write unit tests

**Sprint 4.3: Converse Tool Integration**
- Modify `converse()` to use PTT when enabled
- Add feature flag check
- Preserve backward compatibility
- Write integration tests

**Sprint 4.4: LiveKit Room Support**
- Document LiveKit PTT limitations
- Skip PTT for LiveKit transport
- Add documentation

**Sprint 4.5: Local Microphone Integration**
- End-to-end testing with real hardware
- Audio feedback timing validation
- Error recovery testing

**Sprint 4.6: Transport Testing**
- Comprehensive test suite
- Manual testing checklist
- Performance validation
- Documentation updates

---

## Backward Compatibility

### Requirements

1. **Default Behavior:** PTT disabled by default (`PTT_ENABLED=False`)
2. **Existing API:** All `converse()` parameters work as before
3. **No Breaking Changes:** Existing code continues to work without modification
4. **Graceful Degradation:** If PTT config invalid, fall back to standard recording

### Verification Checklist

- [ ] PTT disabled → Uses `record_audio_with_silence_detection()` as before
- [ ] PTT enabled → Uses `record_with_ptt()` with same interface
- [ ] All converse() parameters preserved
- [ ] LiveKit transport unaffected
- [ ] Speak-only mode (`wait_for_response=False`) unaffected
- [ ] Error messages remain clear and helpful

---

## Performance Considerations

### Latency Impact

**Concern:** Does PTT add latency to conversation flow?

**Analysis:**

**Without PTT:**
```
TTS → Pause → Feedback → [Recording starts immediately] → STT
```

**With PTT:**
```
TTS → Pause → Feedback → [Wait for key press] → [Recording starts] → STT
```

**Impact:** Adds user reaction time (typically 0.5-2 seconds), but this is intentional - gives user thinking time

**Mitigation:** None needed - this is desired behavior

### Resource Overhead

**Concern:** Does PTT consume extra resources?

**Analysis:**
- Keyboard monitoring: Minimal CPU (<1%)
- Additional thread for event loop: Negligible memory
- State machine: Lightweight (<1KB)

**Impact:** Negligible resource overhead

---

## Security Considerations

### Keyboard Monitoring

**Concern:** Keyboard monitoring could be seen as security risk

**Mitigations:**
- Explicit user consent (PTT_ENABLED must be set)
- Only monitors specific key combinations
- No keystroke logging
- No sensitive key capture (passwords, etc.)
- Permissions check via `check_keyboard_permissions()`

### Audio Privacy

**Concern:** Recording behavior changes with PTT

**Mitigations:**
- Same privacy model as before (local processing)
- User has explicit control (must press key)
- Clear audio feedback (chimes indicate listening state)
- Cancel functionality always available

---

## Documentation Updates

### User-Facing Documentation

1. **README.md**: Add PTT feature overview
2. **Configuration Guide**: PTT_ENABLED and related settings
3. **Usage Examples**: PTT conversation examples
4. **Troubleshooting**: PTT-specific issues

### Developer Documentation

1. **Architecture Docs**: Transport adapter pattern
2. **API Reference**: `record_with_ptt()` function
3. **Testing Guide**: PTT test scenarios
4. **Integration Guide**: How to add PTT to custom tools

---

## Next Steps

**Sprint 4.2: Adapter Pattern**

Create the transport adapter that bridges PTT with the existing recording interface:

1. Create `src/voice_mode/ptt/transport_adapter.py`
2. Implement `record_with_ptt()` function
3. Add sync/async bridge for executor compatibility
4. Implement mode-specific recording logic
5. Add error handling and recovery
6. Write comprehensive unit tests
7. Update configuration to add `PTT_ENABLED` flag

**Success Criteria:**
- `record_with_ptt()` passes all unit tests
- Interface matches `record_audio_with_silence_detection()`
- All three PTT modes functional
- Error recovery working
- Documentation complete

---

## Appendix A: Code References

### Key Files

- `src/voice_mode/tools/converse.py` - Main conversation tool
- `src/voice_mode/ptt/controller.py` - PTT controller
- `src/voice_mode/ptt/recorder.py` - PTT recorder
- `src/voice_mode/config.py` - Configuration

### Key Functions

- `converse()` - Line 1402: Main MCP tool
- `record_audio_with_silence_detection()` - Line 946: Current recording
- `livekit_converse()` - Line 1260: LiveKit transport
- `check_livekit_available()` - Line 1229: Transport selection

### Integration Point

- **Primary:** `converse.py:1941-1943` - Local transport recording call
- **Configuration:** `config.py` - Add `PTT_ENABLED` flag
- **New Module:** `ptt/transport_adapter.py` - PTT bridge

---

## Appendix B: Interface Contract

### Recording Function Interface

**Input Parameters:**
```python
max_duration: float       # Maximum recording duration (seconds)
disable_silence_detection: bool  # Disable VAD
min_duration: float       # Minimum recording duration (seconds)
vad_aggressiveness: int   # VAD sensitivity 0-3
```

**Output:**
```python
Tuple[np.ndarray, bool]   # (audio_data, speech_detected)

Where:
- audio_data: numpy array, dtype='int16', shape=(samples,)
- speech_detected: True if speech detected, False otherwise
```

**Error Handling:**
- Raise exception on unrecoverable errors
- Return `(np.array([]), False)` for empty/no-speech recordings
- Attempt automatic recovery for device errors

---

**Analysis Complete**
**Next Sprint:** 4.2 - Adapter Pattern
**Estimated Effort:** 3-4 hours
