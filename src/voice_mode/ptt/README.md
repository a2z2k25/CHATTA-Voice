# Push-to-Talk (PTT) Module

## Overview
This module implements keyboard-controlled voice recording for CHATTA, allowing users to control recording via configurable key combinations instead of automatic silence detection.

## Status
🚧 **In Development** - Phase 2: Foundation Setup

## Module Structure
```
ptt/
├── __init__.py              # Module initialization and public API
├── controller.py            # Main PTT controller (Phase 3)
├── keyboard.py              # Keyboard event handling (Phase 3)
├── permissions.py           # Permission management (Phase 3)
├── recorder.py              # PTT-specific recording (Phase 3)
├── config.py                # PTT configuration (Phase 2)
└── README.md                # This file
```

## Features (Planned)

### Core Functionality
- [x] Module structure created
- [ ] State machine implementation
- [ ] Keyboard event detection
- [ ] Recording control
- [ ] Thread-safe communication

### Recording Modes
- [ ] Hold-to-record (default)
- [ ] Toggle mode (press to start/stop)
- [ ] Hybrid mode (hold + silence detection)

### Platform Support
- [ ] macOS (with accessibility permissions)
- [ ] Windows (no elevation required)
- [ ] Linux (X11 and Wayland)

### Configuration
- [ ] Environment variables
- [ ] YAML configuration files
- [ ] Runtime overrides
- [ ] Configuration presets

## Usage (When Complete)

```python
from voice_mode.tools.converse import converse

# Enable PTT for this conversation
response = await converse(
    "Hello",
    push_to_talk=True,
    ptt_key_combo="down+right"
)
```

## Development Progress

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Research & Design | ✅ Complete | 100% |
| Phase 2: Foundation Setup | 🚧 In Progress | 17% |
| Phase 3: Core PTT | ⏳ Not Started | 0% |
| Phase 4: Transport Adaptation | ⏳ Not Started | 0% |
| Phase 5: Enhanced Features | ⏳ Not Started | 0% |
| Phase 6: Testing & Quality | ⏳ Not Started | 0% |
| Phase 7: Documentation | ⏳ Not Started | 0% |
| Phase 8: Release Preparation | ⏳ Not Started | 0% |
| Phase 9: Post-Release Support | ⏳ Not Started | 0% |

## Dependencies
- `pynput`: Cross-platform keyboard monitoring
- `sounddevice`: Audio recording
- `asyncio`: Async/await support

## Testing
```bash
# Run PTT unit tests
pytest tests/unit/ptt/ -v

# Run PTT integration tests
pytest tests/integration/ptt/ -v

# Run all PTT tests with coverage
pytest tests/*/ptt/ --cov=voice_mode.ptt --cov-report=html
```

## References
- [Research Documentation](../../../docs/research/)
- [Sprint Plan](/Users/az/Desktop/PTT_Feature_Sprint_Plan.md)
- [Main CHATTA README](../../../README.md)
