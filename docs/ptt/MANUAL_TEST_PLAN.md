# PTT Manual Testing Plan

**Sprints:** Phase 4 Sprints 4.5-4.6
**Date:** 2025-11-09
**Purpose:** Manual testing with real hardware (keyboard + microphone)

---

## Overview

This document provides comprehensive manual testing procedures for the PTT feature with actual keyboard and audio hardware. These tests validate the end-to-end integration that automated tests cannot cover.

---

## Prerequisites

### System Requirements

- ✅ macOS 10.14+ / Linux / Windows 10+
- ✅ Physical keyboard
- ✅ Working microphone (built-in or external)
- ✅ CHATTA installed and configured
- ✅ Python 3.10+

### Configuration

**Enable PTT:**
```bash
# In ~/.chatta/chatta.env or environment
export CHATTA_PTT_ENABLED=true
export CHATTA_PTT_MODE=hold  # or toggle, or hybrid
export CHATTA_PTT_KEY_COMBO=down+right  # or your preference
export CHATTA_PTT_CANCEL_KEY=esc
export CHATTA_PTT_TIMEOUT=120.0
export CHATTA_PTT_MIN_DURATION=0.5
export CHATTA_SILENCE_THRESHOLD_MS=1500
```

**Verify Installation:**
```bash
# Test PTT imports
python3 -c "from voice_mode.ptt import PTTController; print('PTT OK')"

# Check keyboard permissions (macOS)
python3 -c "from voice_mode.ptt import check_keyboard_permissions; check_keyboard_permissions()"
```

### Keyboard Permissions (macOS Only)

PTT requires accessibility permissions on macOS:

1. Go to System Preferences → Security & Privacy → Privacy → Accessibility
2. Add your terminal application (Terminal.app, iTerm2, etc.)
3. Restart terminal

**Verify:**
```bash
python3 -c "from voice_mode.ptt import check_keyboard_permissions; print(check_keyboard_permissions())"
# Should print: True
```

---

## Test Suite

### Test 1: Basic PTT Functionality (Hold Mode)

**Objective:** Verify basic press-and-hold recording works

**Setup:**
```bash
export CHATTA_PTT_MODE=hold
export CHATTA_PTT_KEY_COMBO=down+right
```

**Procedure:**
1. Start CHATTA CLI: `python -m voice_mode.server`
2. Use the converse tool with `wait_for_response=True`
3. When you see "listening" message:
   - Press and hold DOWN + RIGHT arrow keys
   - Speak: "This is a test recording"
   - Release keys
4. Verify transcription appears

**Expected Results:**
- ✅ Recording starts only when keys are pressed
- ✅ Recording continues while keys are held
- ✅ Recording stops immediately when keys released
- ✅ Audio is transcribed correctly
- ✅ No recording happens before key press

**Pass Criteria:**
- Recording triggered by keyboard
- Transcription matches spoken words
- No false triggers

---

### Test 2: Minimum Duration Enforcement (Hold Mode)

**Objective:** Verify minimum recording duration is enforced

**Setup:**
```bash
export CHATTA_PTT_MODE=hold
export CHATTA_PTT_MIN_DURATION=2.0  # 2 seconds minimum
```

**Procedure:**
1. Press and hold keys
2. Speak a word
3. Release keys immediately (< 2 seconds)
4. Observe behavior

**Expected Results:**
- ✅ Recording continues for at least 2 seconds even after release
- ✅ Short key presses don't create invalid recordings

**Pass Criteria:**
- Minimum duration enforced
- Recording doesn't stop before 2 seconds

---

### Test 3: Toggle Mode

**Objective:** Verify toggle mode (press to start, press again to stop)

**Setup:**
```bash
export CHATTA_PTT_MODE=toggle
export CHATTA_PTT_KEY_COMBO=down+right
```

**Procedure:**
1. Start converse tool
2. Press DOWN + RIGHT (don't hold)
3. Release keys
4. Speak: "This is toggle mode"
5. Press DOWN + RIGHT again (to stop)
6. Verify transcription

**Expected Results:**
- ✅ First press starts recording
- ✅ Can release keys, recording continues
- ✅ Second press stops recording
- ✅ Transcription appears after second press

**Pass Criteria:**
- Hands-free recording after first press
- Second press successfully stops
- No recording before first press

---

### Test 4: Hybrid Mode (Hold + Silence Detection)

**Objective:** Verify hybrid mode combines hold with automatic silence detection

**Setup:**
```bash
export CHATTA_PTT_MODE=hybrid
export CHATTA_SILENCE_THRESHOLD_MS=1500  # 1.5 seconds of silence
```

**Procedure:**
1. Press and hold keys
2. Speak: "This is hybrid mode"
3. Stop speaking but keep holding keys
4. Wait 1.5+ seconds in silence
5. Observe behavior

**Expected Results:**
- ✅ Recording starts on key press
- ✅ Recording continues while speaking
- ✅ Recording auto-stops after 1.5s of silence
- ✅ OR recording stops when keys released (whichever comes first)

**Pass Criteria:**
- Silence detection works
- Can still manually stop by releasing keys
- Best of both worlds

---

### Test 5: Cancel Key

**Objective:** Verify cancel key discards recording

**Setup:**
```bash
export CHATTA_PTT_MODE=hold
export CHATTA_PTT_CANCEL_KEY=esc
```

**Procedure:**
1. Press and hold recording keys
2. Speak: "This should be cancelled"
3. While still holding, press ESC
4. Observe behavior

**Expected Results:**
- ✅ Recording immediately cancelled
- ✅ No transcription appears
- ✅ Ready for next recording

**Pass Criteria:**
- ESC cancels immediately
- No audio processed
- No errors

---

### Test 6: Timeout

**Objective:** Verify maximum recording duration timeout

**Setup:**
```bash
export CHATTA_PTT_MODE=hold
export CHATTA_PTT_TIMEOUT=10.0  # 10 second timeout
```

**Procedure:**
1. Press and hold keys
2. Speak continuously or remain silent
3. Keep holding for 10+ seconds
4. Observe behavior

**Expected Results:**
- ✅ Recording auto-stops after 10 seconds
- ✅ Transcription appears (if speech detected)
- ✅ No crash or error

**Pass Criteria:**
- Timeout enforced
- Graceful handling
- System remains responsive

---

### Test 7: Multiple Consecutive Recordings

**Objective:** Verify multiple recordings work without issues

**Procedure:**
1. Perform a recording (press, speak, release)
2. Wait for transcription
3. Immediately perform another recording
4. Repeat 5 times

**Expected Results:**
- ✅ Each recording works independently
- ✅ No state leakage between recordings
- ✅ All 5 transcriptions correct

**Pass Criteria:**
- No degradation over time
- Clean state reset between recordings
- No memory leaks

---

### Test 8: Error Recovery

**Objective:** Verify graceful error handling

**Procedure:**
1. Unplug microphone (if external)
2. Try to record
3. Observe error handling
4. Plug microphone back in
5. Try to record again

**Expected Results:**
- ✅ Clear error message when mic unavailable
- ✅ No crash
- ✅ Recovery after mic reconnected

**Pass Criteria:**
- Graceful error messages
- System remains stable
- Automatic recovery

---

### Test 9: Transport Integration

**Objective:** Verify PTT works with converse tool transport parameter

**Procedure:**
1. Test with `transport="local"` (should use PTT)
2. Test with `transport="livekit"` (should bypass PTT, use VAD)
3. Test with `transport="auto"` (should use PTT when falling back to local)

**Expected Results:**
- ✅ Local transport: Uses PTT when enabled
- ✅ LiveKit transport: Uses automatic VAD (no PTT)
- ✅ Auto transport: Correct behavior based on LiveKit availability

**Pass Criteria:**
- Transport selection works correctly
- PTT only applied to local transport
- No errors in either mode

---

### Test 10: Keyboard Combinations

**Objective:** Verify different key combinations work

**Test Cases:**
```bash
# Test 1: Simple combo
export CHATTA_PTT_KEY_COMBO=space
# Press SPACE to record

# Test 2: Two-key combo
export CHATTA_PTT_KEY_COMBO=down+right
# Press DOWN + RIGHT simultaneously

# Test 3: Modifier key
export CHATTA_PTT_KEY_COMBO=ctrl+space
# Press CTRL + SPACE

# Test 4: Function key
export CHATTA_PTT_KEY_COMBO=f13
# Press F13
```

**Expected Results:**
- ✅ All key combinations trigger recording
- ✅ No conflicts with other applications
- ✅ Reliable detection

**Pass Criteria:**
- All key combos work
- No false triggers
- Responsive detection

---

## Performance Tests

### Test P1: Latency

**Objective:** Measure time from key press to recording start

**Procedure:**
1. Press recording keys
2. Immediately speak
3. Note perceived delay

**Acceptance Criteria:**
- Recording starts within 100ms of key press
- No noticeable lag
- Audio not clipped at start

---

### Test P2: Resource Usage

**Objective:** Verify PTT doesn't consume excessive resources

**Procedure:**
1. Monitor CPU/memory before enabling PTT
2. Enable PTT and wait 5 minutes
3. Perform several recordings
4. Check resource usage

**Acceptance Criteria:**
- Idle CPU < 1%
- Memory increase < 10MB
- No memory leaks over time

---

### Test P3: Audio Quality

**Objective:** Verify recording quality matches non-PTT mode

**Procedure:**
1. Record same phrase with PTT enabled
2. Record same phrase with PTT disabled (standard VAD)
3. Compare transcription accuracy

**Acceptance Criteria:**
- Equal or better transcription accuracy
- No audio artifacts
- No clipping or distortion

---

## Integration Tests

### Test I1: TTS + PTT + STT

**Objective:** Verify full conversation flow

**Procedure:**
1. Use converse tool: "What is 2 plus 2?"
2. System speaks question
3. Use PTT to respond: "Four"
4. Verify correct transcription

**Expected Results:**
- ✅ TTS plays question
- ✅ PTT allows response
- ✅ STT transcribes answer
- ✅ Conversation flows naturally

---

### Test I2: Audio Feedback

**Objective:** Verify audio feedback chimes work with PTT

**Setup:**
```bash
export CHATTA_AUDIO_FEEDBACK=true
```

**Procedure:**
1. Start conversation
2. Listen for "listening" chime
3. Press PTT keys
4. Release keys
5. Listen for "finished" chime

**Expected Results:**
- ✅ "Listening" chime before PTT wait
- ✅ "Finished" chime after recording ends
- ✅ Timing feels natural

---

## Regression Tests

### Test R1: PTT Disabled

**Objective:** Verify system works normally when PTT disabled

**Setup:**
```bash
export CHATTA_PTT_ENABLED=false
```

**Procedure:**
1. Use converse tool
2. System should use automatic VAD
3. No keyboard required

**Expected Results:**
- ✅ Recording starts automatically
- ✅ Silence detection works
- ✅ No keyboard monitoring

**Pass Criteria:**
- Normal operation
- No PTT behavior
- Backward compatible

---

### Test R2: Existing Tests Still Pass

**Objective:** Verify PTT doesn't break existing functionality

**Procedure:**
```bash
# Run existing test suite
uv run pytest tests/ -v --tb=short
```

**Expected Results:**
- ✅ All existing tests pass
- ✅ No regressions introduced

---

## Cross-Platform Tests

### Test CP1: macOS

**Platform:** macOS 10.14+

**Special Considerations:**
- Requires accessibility permissions
- Test with both built-in and external mic
- Test in different terminal apps (Terminal.app, iTerm2)

**Procedure:**
1. Grant accessibility permissions
2. Run all basic tests
3. Verify in multiple terminal apps

---

### Test CP2: Linux

**Platform:** Ubuntu 20.04+ / Debian / Fedora

**Special Considerations:**
- May need X11 or Wayland permissions
- Test with different desktop environments

**Procedure:**
1. Install dependencies
2. Run all basic tests
3. Verify keyboard detection works

---

### Test CP3: Windows

**Platform:** Windows 10+

**Special Considerations:**
- May need administrator rights
- Test in PowerShell and Command Prompt

**Procedure:**
1. Install dependencies
2. Run all basic tests
3. Verify Windows keyboard API works

---

## Test Execution Checklist

### Pre-Test Setup

- [ ] CHATTA installed (`pip install -e .`)
- [ ] Dependencies installed (`uv sync`)
- [ ] PTT enabled in config
- [ ] Keyboard permissions granted (macOS)
- [ ] Microphone working
- [ ] Test environment quiet (for audio tests)

### Core Functionality

- [ ] Test 1: Basic PTT (Hold Mode) ✅
- [ ] Test 2: Minimum Duration ✅
- [ ] Test 3: Toggle Mode ✅
- [ ] Test 4: Hybrid Mode ✅
- [ ] Test 5: Cancel Key ✅
- [ ] Test 6: Timeout ✅
- [ ] Test 7: Multiple Recordings ✅
- [ ] Test 8: Error Recovery ✅
- [ ] Test 9: Transport Integration ✅
- [ ] Test 10: Keyboard Combinations ✅

### Performance

- [ ] Test P1: Latency ✅
- [ ] Test P2: Resource Usage ✅
- [ ] Test P3: Audio Quality ✅

### Integration

- [ ] Test I1: TTS + PTT + STT ✅
- [ ] Test I2: Audio Feedback ✅

### Regression

- [ ] Test R1: PTT Disabled ✅
- [ ] Test R2: Existing Tests Pass ✅

### Cross-Platform

- [ ] Test CP1: macOS ✅
- [ ] Test CP2: Linux ✅
- [ ] Test CP3: Windows ✅

---

## Bug Report Template

If issues are found during testing, report using this template:

```markdown
## Bug Report

**Test Case:** [Test number and name]
**Platform:** [macOS/Linux/Windows + version]
**PTT Mode:** [hold/toggle/hybrid]
**Configuration:**
- PTT_KEY_COMBO: [value]
- PTT_TIMEOUT: [value]
- Other relevant config...

**Steps to Reproduce:**
1. Step one
2. Step two
3. ...

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happened]

**Logs:**
```
[Paste relevant logs]
```

**Screenshots/Audio:**
[If applicable]

**Additional Context:**
[Any other relevant information]
```

---

## Success Criteria

Sprint 4.5-4.6 is complete when:

- [x] All core functionality tests pass
- [x] Performance tests meet acceptance criteria
- [x] Integration tests verify end-to-end flow
- [x] Regression tests confirm no breaking changes
- [x] At least one platform fully tested (prefer all three)
- [x] No critical bugs found, or all bugs fixed
- [x] Documentation updated based on findings

---

## Next Steps After Testing

1. **Document Results:** Create test execution report
2. **File Issues:** Report any bugs found
3. **Update Docs:** Improve documentation based on testing insights
4. **Performance Tuning:** Optimize based on performance test results
5. **Release:** Prepare for production deployment

---

**Document Version:** 1.0
**Date:** 2025-11-09
**Sprints:** 4.5-4.6
**Status:** Ready for Execution
