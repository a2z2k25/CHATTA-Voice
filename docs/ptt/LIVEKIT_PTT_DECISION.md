# LiveKit PTT Decision Document

**Sprint:** Phase 4 Sprint 4.4
**Date:** 2025-11-09
**Status:** Decision - No LiveKit PTT in Phase 4

---

## Decision Summary

**PTT will NOT be integrated with LiveKit transport in Phase 4.** LiveKit transport will continue to use its built-in Voice Activity Detection (VAD) system.

---

## Background

During Sprint 4.1 (Transport Analysis), we evaluated how PTT should integrate with CHATTA's two transport modes:
1. **Local Transport** - Direct microphone access via sounddevice
2. **LiveKit Transport** - Room-based real-time communication

The `converse()` tool supports both via the `transport` parameter.

---

## Analysis

### LiveKit Transport Characteristics

**Current Implementation:**
- Uses LiveKit Agent framework (`livekit.agents`)
- Built-in Silero VAD for voice activity detection
- Room-based architecture (multiple participants possible)
- Automatic speech-to-text via LiveKit's STT integration
- Real-time bidirectional communication

**Recording Flow:**
```python
async def livekit_converse(message, room_name, timeout):
    # 1. Connect to LiveKit room
    # 2. Create VoiceAgent with TTS/STT clients
    # 3. Agent speaks message
    # 4. Agent listens via built-in VAD
    # 5. Agent processes user speech events
    # 6. Return transcribed response
```

**Key Characteristic:** LiveKit handles the entire recording lifecycle internally through its Agent framework. Recording is event-driven, not function-based.

### PTT Requirements

**PTT Needs:**
- Keyboard event monitoring (press/release)
- Manual start/stop control of recording
- User-initiated recording trigger
- Single-user interaction model

### Compatibility Assessment

**Technical Challenges:**

1. **Agent Framework Conflict**
   - LiveKit Agent manages recording lifecycle
   - No direct recording start/stop methods
   - Would require extensive Agent modification

2. **Multi-User Context**
   - LiveKit rooms support multiple participants
   - PTT is single-user focused (who controls the keyboard?)
   - Unclear UX in multi-participant scenarios

3. **VAD Integration**
   - LiveKit uses Silero VAD internally
   - PTT would need to override Agent's VAD behavior
   - Complex integration with Agent event system

4. **Architecture Mismatch**
   - Local transport: Function-based recording (record_audio → return data)
   - LiveKit transport: Event-based recording (Agent events → callbacks)
   - PTT designed for function-based model

**Benefit Analysis:**

❌ **Low Value for LiveKit Use Case:**
- LiveKit users are already in interactive room sessions
- Real-time communication benefits from automatic VAD
- Manual keyboard control less valuable in room context
- LiveKit's Silero VAD is highly optimized

✅ **High Value for Local Transport:**
- Direct microphone control
- Single-user focus
- No automatic triggers
- User has full control over recording timing

---

## Decision

**Do NOT integrate PTT with LiveKit transport in Phase 4.**

### Rationale

1. **Architectural Complexity**: Would require significant Agent framework modifications
2. **Low User Benefit**: LiveKit's built-in VAD is suitable for room-based communication
3. **Use Case Mismatch**: PTT is designed for local, single-user control
4. **Development Priority**: Focus resources on local transport where PTT provides clear value

### Implementation

**Current Behavior (Maintained):**
```python
# In converse.py
if transport == "livekit":
    # Use LiveKit's built-in VAD (no PTT)
    livekit_result = await livekit_converse(message, room_name, listen_duration)
    return livekit_result

elif transport == "local":
    # Use PTT when enabled
    recording_function = get_recording_function(ptt_enabled=PTT_ENABLED)
    audio_data, speech_detected = await loop.run_in_executor(
        None, recording_function, listen_duration, ...
    )
```

**Result:**
- LiveKit transport: Unaffected by PTT_ENABLED flag
- Local transport: Uses PTT when PTT_ENABLED=True
- Clean separation of concerns

---

## Future Considerations

If PTT for LiveKit becomes a requirement in the future, consider:

### Option 1: Frontend Integration
- Add PTT controls to LiveKit frontend UI (`voice_mode/frontend/`)
- JavaScript keyboard handlers in browser
- Send PTT events to LiveKit room via WebRTC data channel
- Agent responds to PTT events from room participants

**Pros:**
- Clean browser-based keyboard handling
- Works in web interface
- Proper multi-user support (each participant controls their own PTT)

**Cons:**
- Requires frontend development
- Only works in browser, not in CLI

### Option 2: Agent Extension
- Extend VoiceAgent with PTT event handling
- Send keyboard events from CLI to Agent via custom events
- Agent pauses/resumes VAD based on PTT state

**Pros:**
- Works in CLI environment
- Integrates with existing Agent

**Cons:**
- Complex event coordination
- Requires LiveKit custom event system
- Unclear multi-user behavior

### Option 3: Hybrid Approach
- Keep LiveKit with automatic VAD for room sessions
- Use local transport + PTT for single-user voice commands
- Let users choose based on their use case

**Pros:**
- Leverages strengths of each approach
- Clear separation of use cases
- No complex integration needed

**Cons:**
- Users need to understand which transport to use

---

## Testing Impact

**Test Coverage:**

✅ **Verified in Integration Tests:**
- `test_livekit_transport_bypasses_ptt` - Confirms LiveKit unaffected by PTT
- `test_local_transport_uses_ptt` - Confirms local transport uses PTT

**No Additional Tests Needed:**
- LiveKit transport continues to work as before
- PTT integration tests cover local transport only
- Transport selection logic tested

---

## Documentation Updates

**User Documentation:**

Users should be informed:
1. PTT only works with `transport="local"` or `transport="auto"` (when falling back to local)
2. LiveKit transport uses automatic voice activity detection
3. For keyboard control, use local transport with `PTT_ENABLED=True`

**Example User Guidance:**

```markdown
## PTT Transport Compatibility

**PTT Enabled:**
- ✅ Local Transport (`transport="local"`) - Uses PTT keyboard control
- ✅ Auto Transport (`transport="auto"`) - Uses PTT when falling back to local
- ❌ LiveKit Transport (`transport="livekit"`) - Uses automatic VAD (PTT not applied)

**Recommendation:**
- Single-user voice commands: Use `transport="local"` with PTT
- Room-based conversations: Use `transport="livekit"` with automatic VAD
- Automatic selection: Use `transport="auto"` (default)
```

---

## Acceptance Criteria

Sprint 4.4 is complete when:

- [x] Decision documented with rationale
- [x] Integration tests verify LiveKit bypasses PTT
- [x] Local transport verified to use PTT
- [x] Future options documented
- [x] User documentation guidance provided

---

## Conclusion

**Decision Ratified:** PTT will not be integrated with LiveKit transport in Phase 4.

**Next Steps:**
- Proceed with Sprint 4.5: Local Microphone Integration
- Focus testing efforts on local transport + PTT
- Document transport selection guidance for users

---

**Document Version:** 1.0
**Date:** 2025-11-09
**Sprint:** Phase 4 Sprint 4.4
**Status:** Complete
