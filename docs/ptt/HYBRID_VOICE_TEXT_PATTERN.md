# Hybrid Voice-Text Response Pattern

## Overview

The Hybrid Voice-Text Response Pattern ensures seamless conversation flow during voice interactions by automatically following lengthy text responses with brief voice notifications.

## Problem Statement

When AI assistants provide lengthy or technical responses during voice conversations:
- Users experience abrupt silence after receiving text responses
- It's unclear whether the conversation is still active
- Users don't know if they should wait or continue speaking
- The conversation flow feels broken

## Solution

Implement a two-phase response pattern:
1. **Phase 1**: Output detailed text response (for complex content)
2. **Phase 2**: Voice follow-up confirming continuation

## Implementation Pattern

### Detection Criteria

Trigger hybrid pattern when response contains:
- **Character count**: >500 characters
- **Code blocks**: Any response with code/configuration
- **Multiple paragraphs**: 3+ paragraphs
- **Technical content**: API docs, architecture, troubleshooting
- **Lists/Tables**: Structured data presentation
- **File paths**: Multiple file references

### Response Structure

```python
# 1. Output detailed text response
print("""
[Detailed technical explanation]
[Code examples]
[Step-by-step instructions]
""")

# 2. Voice follow-up to continue conversation
converse(
    "I've provided a detailed response above. Take your time to review it, and let me know when you're ready to continue.",
    wait_for_response=True
)
```

### Key Requirements

1. **Always use `wait_for_response=True`** - Keeps conversation active
2. **Keep voice message concise** - 1-2 sentences maximum
3. **Maintain natural flow** - Should feel seamless, not disruptive
4. **Be contextually appropriate** - Adjust message to content type

## Voice Follow-up Templates

### General Technical Response
```
"I've shared a detailed response above. Review it when you're ready, and we can continue."
```

### Code/Implementation
```
"There's a code example above. Take a look and let me know if you have questions."
```

### Troubleshooting/Debugging
```
"I've outlined the troubleshooting steps in text. Try those and let me know the results."
```

### Architecture/Design
```
"I've provided the technical details above. Review them and we can discuss further."
```

### Multiple Options/Decisions
```
"There are several options outlined above. Take a moment to review them and let me know your preference."
```

### Configuration/Setup
```
"The configuration steps are detailed above. Follow along and let me know if you need help."
```

## Examples

### Example 1: Technical Explanation

**Context**: User asks about PTT architecture during voice conversation

**Response**:
```
[Text Output]
The PTT system consists of several layers:

1. **KeyboardHandler** - Monitors keyboard events using pynput
   - Supports multiple key combinations
   - Platform-specific optimizations

2. **PTTController** - State machine managing PTT lifecycle
   - States: IDLE, WAITING, RECORDING, PROCESSING
   - Event queue for async handling

3. **AudioRecorder** - Captures microphone input
   - Real-time audio streaming
   - Silence detection with WebRTC VAD

[Voice Follow-up]
"I've explained the PTT architecture in detail above. Review the three main layers, and we can dive deeper into any component you're interested in."
```

### Example 2: Code Implementation

**Context**: User asks how to implement a feature during voice conversation

**Response**:
```
[Text Output]
Here's how to implement the feature:

```python
def implement_feature():
    # Step 1: Initialize controller
    controller = PTTController(
        key_combo="alt_r",
        timeout=120.0
    )

    # Step 2: Set up callbacks
    controller._on_recording_start = handle_start
    controller._on_recording_stop = handle_stop

    # Step 3: Enable and run
    controller.enable()
    await controller.process_events()
```

Key points:
- Use underscore prefix for callback assignment
- Always enable before processing events
- Handle cleanup in finally block

[Voice Follow-up]
"There's a complete code example above with three key steps. Try it out and let me know how it goes."
```

### Example 3: Troubleshooting Guide

**Context**: User reports an issue during voice conversation

**Response**:
```
[Text Output]
Let's troubleshoot this step by step:

**Check 1: Permissions**
- macOS: System Settings > Privacy & Security > Accessibility
- Verify terminal app has checkbox enabled

**Check 2: Configuration**
```bash
export CHATTA_PTT_ENABLED=true
export CHATTA_PTT_KEY_COMBO=alt_r
```

**Check 3: Test keyboard detection**
```bash
python /tmp/test_keyboard_detection.py
```

**Check 4: Review logs**
- Look for "PTT enabled" in output
- Check for any ERROR messages

[Voice Follow-up]
"I've outlined four troubleshooting checks above. Work through them in order and let me know where you get stuck."
```

## Anti-Patterns (What NOT to Do)

### ❌ Don't: Long voice follow-ups
```python
# BAD - Too verbose
converse(
    "So I've provided you with a really detailed response above that covers all the technical aspects of the implementation, and I think you should take some time to carefully review each section, paying particular attention to the code examples and configuration steps, and then when you're done reading through everything, we can continue our discussion and address any questions you might have.",
    wait_for_response=True
)
```

### ❌ Don't: Skip wait_for_response
```python
# BAD - Conversation appears to end
converse(
    "I've provided details above.",
    wait_for_response=False  # User thinks conversation is over!
)
```

### ❌ Don't: Use for short responses
```python
# BAD - Unnecessary for brief responses
print("PTT is enabled in your config.")
converse("I just answered your question above.", wait_for_response=True)
# Just use voice directly!
```

### ❌ Don't: Repeat content in voice
```python
# BAD - Duplicating information
print("The config requires CHATTA_PTT_ENABLED=true and CHATTA_PTT_KEY_COMBO=alt_r")
converse(
    "So you need to set CHATTA_PTT_ENABLED to true and CHATTA_PTT_KEY_COMBO to alt_r.",
    wait_for_response=True
)
# Text is already sufficient!
```

## Configuration

### Environment Variables

```bash
# Enable hybrid pattern (future enhancement)
export CHATTA_HYBRID_RESPONSE_ENABLED=true

# Character threshold for triggering pattern
export CHATTA_HYBRID_RESPONSE_THRESHOLD=500

# Custom voice template
export CHATTA_HYBRID_RESPONSE_TEMPLATE="I've shared details above. Review and let me know your thoughts."
```

## Benefits

1. **Continuous Conversation Flow** - No awkward silences
2. **Clear Expectations** - User knows to read then respond
3. **Better UX** - Feels natural and conversational
4. **Accessibility** - Accommodates both reading and listening
5. **Flexibility** - Text for detail, voice for flow

## Testing

### Manual Test Script

```python
#!/usr/bin/env python3
"""Test hybrid voice-text pattern"""

import asyncio
from voice_mode.tools.converse import converse

async def test_hybrid_pattern():
    """Demonstrate hybrid pattern"""

    # Lengthy technical response
    print("""
    PTT System Architecture
    =======================

    The PTT system consists of:

    1. KeyboardHandler - Event monitoring
    2. PTTController - State management
    3. AudioRecorder - Audio capture

    Each component has specific responsibilities...
    [... 500+ more characters ...]
    """)

    # Voice follow-up
    await converse(
        "I've explained the architecture above. Review the three components and let me know which you'd like to explore.",
        wait_for_response=True
    )

if __name__ == "__main__":
    asyncio.run(test_hybrid_pattern())
```

## Future Enhancements

1. **Automatic Detection** - AI automatically applies pattern based on response analysis
2. **Configurable Thresholds** - User-customizable triggers
3. **Context Awareness** - Adapt to conversation context
4. **Voice Tone Control** - Use TTS instructions for natural delivery
5. **Multi-language Support** - Localized follow-up templates

## Related Documentation

- [PTT User Guide](README.md)
- [Converse Tool Documentation](../tools/converse.md)
- [Voice Conversation Best Practices](VOICE_BEST_PRACTICES.md)

## Changelog

- **2025-11-10**: Initial pattern documentation
- **2025-11-10**: Added examples and anti-patterns

---

**Pattern Status**: Recommended Best Practice
**Applicability**: All voice conversations with lengthy responses
**Implementation**: Manual (AI assistant behavioral pattern)
