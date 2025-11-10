# Keyboard Library Evaluation for Push-to-Talk Feature
Date: November 9, 2025
Sprint: 1.1

## Libraries Evaluated

### 1. pynput
**Version**: Latest (1.7.6+)
**License**: LGPL-3.0 (Compatible ✅)
**Repository**: https://github.com/moses-palmer/pynput

**Pros:**
- Excellent cross-platform support (Windows, macOS, Linux)
- Can both monitor and control keyboard
- Automatic backend selection per OS
- Well-maintained with active development
- Thread-safe design
- Supports global hotkeys
- Good documentation

**Cons:**
- macOS requires accessibility permissions
- Not trusted by default on macOS (requires user approval)
- Callbacks run in OS thread (careful with blocking ops)
- Slightly higher memory footprint

**PTT Suitability**: ⭐⭐⭐⭐⭐ **RECOMMENDED**

### 2. keyboard
**Version**: Latest (0.13.5+)
**License**: MIT (Compatible ✅)
**Repository**: https://github.com/boppreh/keyboard

**Pros:**
- Simple, pythonic API
- Pure Python implementation
- Good hotkey support
- Can record and playback sequences
- MIT licensed

**Cons:**
- Requires root/admin on macOS ❌
- Acts like keylogger on Windows (triggers AV)
- Less reliable on Linux (X11/Wayland issues)
- Not as actively maintained

**PTT Suitability**: ⭐⭐☆☆☆ (Permission issues)

### 3. PyAutoGUI
**Version**: Latest (0.9.54+)
**License**: BSD (Compatible ✅)
**Repository**: https://github.com/asweigart/pyautogui

**Pros:**
- Good for keyboard control
- Cross-platform
- Well documented
- Also handles mouse

**Cons:**
- Cannot detect key presses ❌
- Only for sending keys, not monitoring
- Heavier dependency

**PTT Suitability**: ⭐☆☆☆☆ (No monitoring capability)

### 4. asyncio-keyboard (theoretical)
**Status**: Not a real library
**Note**: No async-native keyboard library exists

**Alternative**: Use pynput with asyncio executor pattern

## Platform-Specific Considerations

### macOS
- **pynput**: Requires accessibility permissions (user prompt)
- **keyboard**: Requires root (unacceptable)
- **Fallback**: If permissions denied, revert to standard mode

### Windows
- **pynput**: Works without elevation
- **keyboard**: May trigger antivirus warnings
- **Best choice**: pynput

### Linux
- **pynput**: Works with X11 and Wayland
- **keyboard**: Issues with Wayland
- **Best choice**: pynput

## Recommendation for CHATTA PTT

**Selected Library**: `pynput`

**Reasoning:**
1. Best cross-platform support
2. No root/admin required (only accessibility permissions on macOS)
3. Thread-safe design fits our async architecture
4. Active maintenance and community
5. LGPL-3.0 license compatible with MIT

**Implementation Strategy:**
```python
# Use pynput with asyncio executor pattern
from pynput import keyboard
import asyncio
from concurrent.futures import ThreadPoolExecutor

class PTTController:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.listener = None

    async def start_listening(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._start_listener
        )
```

## License Compatibility Check

CHATTA is MIT licensed. Library compatibility:
- ✅ pynput (LGPL-3.0) - Can be used as dependency
- ✅ keyboard (MIT) - Fully compatible
- ✅ PyAutoGUI (BSD) - Fully compatible

## Decision Matrix

| Criteria | pynput | keyboard | PyAutoGUI |
|----------|--------|----------|-----------|
| Cross-platform | ✅✅✅ | ⚠️ | ✅✅ |
| No elevation needed | ✅✅ | ❌ | ✅✅ |
| Key monitoring | ✅ | ✅ | ❌ |
| Thread safety | ✅ | ⚠️ | ⚠️ |
| Active maintenance | ✅ | ⚠️ | ✅ |
| PTT suitable | ✅ | ❌ | ❌ |

## Final Decision

**Use `pynput` for CHATTA Push-to-Talk implementation**

Next steps:
1. Add pynput to pyproject.toml
2. Create permission request handler for macOS
3. Implement fallback for permission denial