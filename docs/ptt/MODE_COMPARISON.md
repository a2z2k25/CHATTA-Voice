# PTT Mode Comparison Guide

This guide helps you choose the right PTT mode for your use case.

## Quick Decision Matrix

| Your Need | Recommended Mode |
|-----------|------------------|
| Quick voice commands | **Hold Mode** |
| Long dictation | **Toggle Mode** |
| Natural conversation | **Hybrid Mode** |
| Accessibility requirements | **Toggle or Hybrid** |
| Noisy environment | **Hold Mode** |
| Hands-free operation | **Toggle Mode** |
| Variable-length inputs | **Hybrid Mode** |
| Precise timing control | **Hold Mode** |

## Detailed Mode Comparison

### Hold Mode (Classic PTT)

**How it works:**
1. Press and hold key combination
2. Speak while holding
3. Release key to stop

**Pros:**
- ✅ Precise manual control
- ✅ Familiar PTT experience
- ✅ Works in noisy environments
- ✅ No accidental long recordings
- ✅ Visual feedback (key held = recording)

**Cons:**
- ❌ Requires continuous key press
- ❌ Can be tiring for long recordings
- ❌ Not hands-free
- ❌ May accidentally release too early

**Best For:**
- Radio-style communications
- Quick commands ("search for X", "send message")
- Gaming voice chat
- Users experienced with PTT
- Situations requiring precise control

**Configuration:**
```python
from voice_mode import config
config.PTT_MODE = "hold"
config.PTT_MIN_DURATION = 0.5  # Prevent accidental quick presses
```

**Example Use Cases:**
- Voice commands in FPS games
- Quick queries to AI assistant
- Walkie-talkie style communication
- Controlled dictation in noisy office

---

### Toggle Mode (Hands-Free PTT)

**How it works:**
1. Press key once to start
2. Speak hands-free
3. Press key again to stop

**Pros:**
- ✅ Completely hands-free after start
- ✅ Great for long recordings
- ✅ Accessible for users with motor limitations
- ✅ Can type or use mouse while speaking
- ✅ No fatigue from holding key

**Cons:**
- ❌ Need to remember to press again to stop
- ❌ May forget it's recording
- ❌ Requires two deliberate actions
- ❌ Less immediate control
- ❌ Risk of recording too much

**Best For:**
- Long-form dictation
- Reading prepared text
- Accessibility use cases
- Multi-tasking while speaking
- Presentations or narration

**Configuration:**
```python
from voice_mode import config
config.PTT_MODE = "toggle"
config.PTT_TIMEOUT = 120.0  # 2 minute safety timeout
```

**Example Use Cases:**
- Writing emails via dictation
- Code review commentary
- Podcast recording
- Accessibility-focused applications
- Reading from notes while recording

---

### Hybrid Mode (Smart PTT)

**How it works:**
1. Press and hold key (like Hold mode)
2. Speak while holding
3. Release OR stay silent for N seconds
4. Auto-stops on silence detection

**Pros:**
- ✅ Manual control like Hold mode
- ✅ Auto-stop on silence (smart)
- ✅ Best of both worlds
- ✅ Natural conversation flow
- ✅ Flexible for variable-length inputs
- ✅ Can release early OR let silence stop it

**Cons:**
- ⚠️ Requires silence detection setup
- ⚠️ May stop on natural pauses
- ⚠️ Slightly more complex
- ⚠️ Silence threshold needs tuning

**Best For:**
- Natural conversation with AI
- Variable-length responses
- Users who want smart automation
- Mixed short/long inputs
- Professional voice assistant use

**Configuration:**
```python
from voice_mode import config
config.PTT_MODE = "hybrid"
config.PTT_MIN_DURATION = 0.5
config.SILENCE_THRESHOLD_MS = 1500  # 1.5s silence = auto-stop
```

**Example Use Cases:**
- Conversing with Claude Code
- Q&A sessions
- Voice-driven coding assistance
- Interactive voice applications
- Smart home voice control

---

## Feature Comparison Table

| Feature | Hold | Toggle | Hybrid |
|---------|------|--------|--------|
| **Control** |
| Manual Start | ✅ Key Press | ✅ Key Press | ✅ Key Press |
| Manual Stop | ✅ Key Release | ✅ Key Press | ✅ Key Release |
| Auto Stop | ❌ No | ❌ No | ✅ Silence |
| **Behavior** |
| Hands-Free | ❌ No | ✅ Yes | ⚠️ Partial |
| Continuous Hold | ✅ Required | ❌ No | ⚠️ Optional |
| Silence Detection | ❌ No | ❌ No | ✅ Yes |
| Minimum Duration | ✅ Yes | ❌ No | ✅ Yes |
| Maximum Duration | ✅ Timeout | ✅ Timeout | ✅ Timeout |
| **Use Cases** |
| Quick Commands | ✅ Excellent | ⚠️ Ok | ✅ Excellent |
| Long Dictation | ⚠️ Ok | ✅ Excellent | ✅ Good |
| Natural Speech | ✅ Good | ⚠️ Ok | ✅ Excellent |
| Noisy Environment | ✅ Excellent | ✅ Good | ⚠️ Fair |
| Quiet Environment | ✅ Good | ✅ Good | ✅ Excellent |
| **Accessibility** |
| Motor Limitations | ⚠️ Challenging | ✅ Excellent | ✅ Good |
| Visual Impairment | ✅ Good | ⚠️ Ok | ✅ Good |
| Cognitive Load | ✅ Low | ⚠️ Medium | ⚠️ Medium |
| **Technical** |
| Setup Complexity | ✅ Simple | ✅ Simple | ⚠️ Moderate |
| CPU Usage | ✅ Low | ✅ Low | ⚠️ Medium |
| Accuracy | ✅ High | ✅ High | ⚠️ Depends |

## Configuration Recommendations

### Hold Mode - Optimal Settings

```python
from voice_mode import config

config.PTT_MODE = "hold"
config.PTT_MIN_DURATION = 0.5      # Prevent accidental clicks
config.PTT_TIMEOUT = 30.0          # 30s max (safety)
config.PTT_KEY_COMBO = "ctrl+space"  # Easy to hold
```

**Key Combo Recommendations:**
- `space` - Very easy but may conflict
- `ctrl+space` - Good balance
- `alt+space` - Alternative
- `F12` - Dedicated function key
- Avoid: `shift` (used in typing)

---

### Toggle Mode - Optimal Settings

```python
from voice_mode import config

config.PTT_MODE = "toggle"
config.PTT_TIMEOUT = 120.0         # 2 min max (longer for dictation)
config.PTT_KEY_COMBO = "F9"        # Dedicated key
```

**Key Combo Recommendations:**
- `F9` or `F10` - Dedicated, hard to accidentally press
- `ctrl+alt+r` - Deliberate combination
- Avoid: `space`, `enter` (accidental toggling)

---

### Hybrid Mode - Optimal Settings

```python
from voice_mode import config

config.PTT_MODE = "hybrid"
config.PTT_MIN_DURATION = 0.5
config.SILENCE_THRESHOLD_MS = 1500  # Tune based on speech patterns
config.PTT_TIMEOUT = 60.0           # 1 min max
config.PTT_KEY_COMBO = "option_r" # Right Option Key (default)
```

**Silence Threshold Tuning:**
- Fast speakers: 1000ms (1 second)
- Normal pace: 1500ms (1.5 seconds)
- Thoughtful/slow: 2000-3000ms (2-3 seconds)
- Language learning: 3000-5000ms (3-5 seconds)

**Key Combo Recommendations:**
- `option_r` - Right Option Key (default, macOS friendly)
- `ctrl+r` - Memorable
- `F11` - Dedicated key
- Avoid: Single keys (may stop on pause)

---

## Migration Guide

### Moving from Hold to Hybrid

If you're comfortable with Hold mode but want smarter behavior:

1. Keep the same key combo
2. Set silence threshold conservatively high (3000ms)
3. Gradually decrease threshold as you get used to it
4. You can still release manually like Hold mode

```python
# Before (Hold)
config.PTT_MODE = "hold"
config.PTT_KEY_COMBO = "ctrl+space"

# After (Hybrid) - conservative
config.PTT_MODE = "hybrid"
config.PTT_KEY_COMBO = "ctrl+space"  # Same key
config.SILENCE_THRESHOLD_MS = 3000   # Conservative
```

### Moving from Toggle to Hybrid

If you use Toggle for hands-free but want more control:

1. Switch to Hybrid
2. Use higher silence threshold
3. Benefit: Can release early if needed

```python
# Before (Toggle)
config.PTT_MODE = "toggle"

# After (Hybrid)
config.PTT_MODE = "hybrid"
config.SILENCE_THRESHOLD_MS = 2000  # Let silence end most recordings
# Can still release key manually when needed
```

---

## Real-World Scenarios

### Scenario 1: Customer Service Call Center

**Need:** Quick, controlled responses to customers

**Recommendation:** **Hold Mode**
- Fast response times
- Precise control
- No accidental long recordings
- Familiar to operators

```python
config.PTT_MODE = "hold"
config.PTT_MIN_DURATION = 0.3
config.PTT_TIMEOUT = 20.0  # Responses should be concise
```

---

### Scenario 2: Legal Dictation

**Need:** Long transcriptions of notes/documents

**Recommendation:** **Toggle Mode**
- Hands-free for long sessions
- Can use both hands for documents
- Deliberate start/stop points

```python
config.PTT_MODE = "toggle"
config.PTT_TIMEOUT = 300.0  # 5 minutes max
config.PTT_KEY_COMBO = "F9"
```

---

### Scenario 3: AI Coding Assistant (CHATTA)

**Need:** Variable-length questions and commands

**Recommendation:** **Hybrid Mode**
- Natural conversation flow
- Auto-stops on pause
- Manual override available
- Best UX for interactive AI

```python
config.PTT_MODE = "hybrid"
config.SILENCE_THRESHOLD_MS = 1500
config.PTT_MIN_DURATION = 0.5
config.PTT_KEY_COMBO = "option_r"
```

---

### Scenario 4: Accessibility Use Case

**Need:** User with limited fine motor control

**Recommendation:** **Toggle Mode**
- Single press to start/stop
- No need to hold key
- Can use adaptive switches
- No fatigue

```python
config.PTT_MODE = "toggle"
config.PTT_KEY_COMBO = "F12"  # Large key
config.PTT_TIMEOUT = 180.0     # Generous timeout
```

---

### Scenario 5: Noisy Office Environment

**Need:** Accurate recordings despite background noise

**Recommendation:** **Hold Mode**
- Manual control prevents false triggers
- Background noise won't auto-stop recording
- Clear start/end points

```python
config.PTT_MODE = "hold"
config.PTT_MIN_DURATION = 0.7  # Higher to prevent noise triggering
config.PTT_KEY_COMBO = "ctrl+space"
# Disable silence detection (not applicable in Hold mode anyway)
```

---

## Performance Comparison

| Metric | Hold | Toggle | Hybrid |
|--------|------|--------|--------|
| CPU Usage (idle) | <1% | <1% | <1% |
| CPU Usage (recording) | 2-4% | 2-4% | 4-6%* |
| Memory Usage | 50MB | 50MB | 55MB* |
| Latency (start) | <50ms | <50ms | <50ms |
| Latency (stop) | <100ms | <100ms | 100-200ms* |
| Battery Impact | Low | Low | Medium* |

*Higher due to silence detection processing

---

## Troubleshooting by Mode

### Hold Mode Issues

**Problem:** Accidentally stops too early
- **Solution:** Increase `PTT_MIN_DURATION` to 0.7-1.0 seconds

**Problem:** Tiring to hold key
- **Solution:** Switch to Hybrid or Toggle mode

---

### Toggle Mode Issues

**Problem:** Forget to stop recording
- **Solution:** Lower `PTT_TIMEOUT` for safety

**Problem:** Accidental double-tap stops immediately
- **Solution:** Use dedicated function key (F9-F12)

---

### Hybrid Mode Issues

**Problem:** Stops on natural speech pauses
- **Solution:** Increase `SILENCE_THRESHOLD_MS` to 2000-3000ms

**Problem:** Takes too long to auto-stop
- **Solution:** Decrease `SILENCE_THRESHOLD_MS` or release key manually

**Problem:** Doesn't auto-stop at all
- **Solution:** Check silence detection is configured, verify microphone works

---

## Summary Recommendations

**Choose Hold Mode if:**
- You need precise, manual control
- You're familiar with classic PTT
- Quick commands are your primary use case
- You work in a noisy environment

**Choose Toggle Mode if:**
- You need hands-free operation
- You do long-form dictation
- You have accessibility requirements
- You're multi-tasking while speaking

**Choose Hybrid Mode if:**
- You want the best of both worlds
- You have variable-length inputs
- You're using an AI assistant
- You want smart auto-stop behavior

**Still unsure?**
Start with **Hybrid Mode** - it provides manual control like Hold but auto-stops when you're done speaking. It's the most versatile option for interactive voice applications.

---

**Last Updated:** 2025-11-09
**Phase:** 3 Complete
