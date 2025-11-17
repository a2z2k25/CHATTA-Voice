# Contributing to PTT Module

## Development Workflow

### Setting Up Development Environment

1. **Clone and install dependencies:**
```bash
cd /Users/az/Claude/CHATTA
source .venv/bin/activate
pip install -e ".[dev]"
```

2. **Verify installation:**
```bash
python -c "from voice_mode.ptt import KeyboardHandler; print('PTT module loaded successfully')"
```

3. **Run existing tests:**
```bash
python -m pytest tests/unit/ptt/ -v
```

## Code Organization

### Module Structure
```
src/voice_mode/ptt/
├── __init__.py          # Public API exports
├── keyboard.py          # Keyboard event handling
├── logging.py           # PTT logging infrastructure
├── controller.py        # Main PTT controller (Phase 3)
├── permissions.py       # Permission management (Phase 3)
├── recorder.py          # PTT-specific recording (Phase 3)
├── README.md            # Module documentation
├── TESTING.md           # Testing guide
└── CONTRIBUTING.md      # This file
```

### Import Conventions

```python
# Public API (from __init__.py)
from voice_mode.ptt import KeyboardHandler, PTTLogger

# Internal imports (within ptt module)
from .logging import get_ptt_logger
from .keyboard import check_keyboard_permissions

# External dependencies
import asyncio
from pynput.keyboard import Listener, Key
```

## Coding Standards

### Style Guide

- **PEP 8 compliance:** Use 4 spaces for indentation
- **Type hints:** Always use type annotations
- **Docstrings:** Google-style docstrings for all public functions

Example:
```python
def parse_key_combo(key_combo: str) -> Set[str]:
    """Parse key combination string into set of key names.

    Args:
        key_combo: Key combination string (e.g., "ctrl+c", "option_r")

    Returns:
        Set of normalized key names

    Raises:
        ValueError: If key_combo is empty or invalid

    Examples:
        >>> parse_key_combo("space")
        {'space'}
        >>> parse_key_combo("ctrl+c")
        {'ctrl', 'c'}
    """
    if not key_combo:
        raise ValueError("Key combination cannot be empty")

    return {key.strip().lower() for key in key_combo.split("+")}
```

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `KeyboardHandler`, `PTTLogger`)
- **Functions/methods:** `snake_case` (e.g., `start_recording`, `log_event`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- **Private members:** `_leading_underscore` (e.g., `_on_press`, `_combo_active`)

### Type Annotations

```python
from typing import Optional, Callable, Set, Dict, Any

class KeyboardHandler:
    def __init__(
        self,
        key_combo: str = "option_r",
        on_press_callback: Optional[Callable[[], None]] = None,
        on_release_callback: Optional[Callable[[], None]] = None,
        debounce_ms: int = 50
    ) -> None:
        """Initialize keyboard handler."""
        self.key_combo: Set[str] = self._parse_key_combo(key_combo)
        self.pressed_keys: Set[str] = set()
        self._callbacks: Dict[str, Optional[Callable]] = {
            "press": on_press_callback,
            "release": on_release_callback
        }
```

## Writing Tests

### Test Organization

Every new feature must include tests:

```
tests/
└── unit/
    └── ptt/
        ├── test_keyboard_handler.py    # For keyboard.py
        ├── test_ptt_logging.py         # For logging.py
        ├── test_ptt_controller.py      # For controller.py (future)
        └── test_ptt_permissions.py     # For permissions.py (future)
```

### Test Requirements

1. **Minimum coverage:** 90% for new code
2. **Test isolation:** Each test should be independent
3. **Naming:** `test_<feature>_<scenario>_<expected_outcome>`
4. **Fixtures:** Use existing fixtures from `tests/conftest.py`

Example test:
```python
import pytest
from voice_mode.ptt import KeyboardHandler

class TestKeyboardHandler:
    """Tests for KeyboardHandler class"""

    def test_key_combo_parsing_with_single_key(self):
        """Test that single key combo is parsed correctly"""
        # Arrange & Act
        handler = KeyboardHandler("space")

        # Assert
        assert handler.key_combo == {"space"}

    def test_key_combo_parsing_with_multiple_keys(self):
        """Test that multi-key combo is parsed correctly"""
        handler = KeyboardHandler("ctrl+alt+delete")
        assert handler.key_combo == {"ctrl", "alt", "delete"}

    def test_invalid_key_combo_raises_error(self):
        """Test that empty key combo raises ValueError"""
        with pytest.raises(ValueError, match="Key combination cannot be empty"):
            KeyboardHandler("")
```

### Running Tests

```bash
# Run all PTT tests
python -m pytest tests/unit/ptt/ -v

# Run specific test file
python -m pytest tests/unit/ptt/test_keyboard_handler.py -v

# Run with coverage
python -m pytest tests/unit/ptt/ --cov=voice_mode.ptt --cov-report=html

# Run specific test
python -m pytest tests/unit/ptt/test_keyboard_handler.py::TestKeyboardHandler::test_key_combo_parsing_with_single_key -v
```

## Adding New Features

### Feature Development Process

1. **Check sprint plan:** Refer to `/Users/az/Desktop/PTT_Feature_Sprint_Plan.md`
2. **Create feature branch:** `git checkout -b feature/ptt-<feature-name>`
3. **Write tests first (TDD):**
   ```bash
   # Create test file
   touch tests/unit/ptt/test_new_feature.py

   # Write failing tests
   # Run tests to confirm they fail
   python -m pytest tests/unit/ptt/test_new_feature.py -v
   ```
4. **Implement feature:**
   ```bash
   # Create implementation file
   touch src/voice_mode/ptt/new_feature.py

   # Write code until tests pass
   ```
5. **Update public API:**
   ```python
   # In src/voice_mode/ptt/__init__.py
   from .new_feature import NewFeatureClass

   __all__ = [
       # ... existing exports
       "NewFeatureClass",
   ]
   ```
6. **Update documentation:**
   - Add docstrings to all public functions/classes
   - Update README.md with usage examples
   - Update TESTING.md if new test patterns introduced

### Example: Adding State Machine Component

1. **Create test file:**
```python
# tests/unit/ptt/test_state_machine.py
import pytest
from voice_mode.ptt import PTTStateMachine

class TestPTTStateMachine:
    def test_initial_state_is_idle(self):
        """Test state machine starts in IDLE state"""
        sm = PTTStateMachine()
        assert sm.current_state == "IDLE"

    def test_transition_from_idle_to_recording(self):
        """Test valid transition from IDLE to RECORDING"""
        sm = PTTStateMachine()
        sm.transition("RECORDING")
        assert sm.current_state == "RECORDING"

    def test_invalid_transition_raises_error(self):
        """Test invalid transition raises error"""
        sm = PTTStateMachine()
        with pytest.raises(ValueError):
            sm.transition("PROCESSING")  # Can't go directly to PROCESSING
```

2. **Implement feature:**
```python
# src/voice_mode/ptt/state_machine.py
from typing import Set, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class PTTState(Enum):
    """PTT state enumeration"""
    IDLE = "IDLE"
    WAITING_FOR_KEY = "WAITING_FOR_KEY"
    KEY_PRESSED = "KEY_PRESSED"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"

@dataclass
class StateTransition:
    """State transition definition"""
    from_state: PTTState
    to_state: PTTState
    trigger: str

class PTTStateMachine:
    """State machine for PTT lifecycle management"""

    # Valid state transitions
    TRANSITIONS: Dict[PTTState, Set[PTTState]] = {
        PTTState.IDLE: {PTTState.WAITING_FOR_KEY},
        PTTState.WAITING_FOR_KEY: {PTTState.KEY_PRESSED, PTTState.IDLE},
        PTTState.KEY_PRESSED: {PTTState.RECORDING, PTTState.IDLE},
        PTTState.RECORDING: {PTTState.PROCESSING, PTTState.IDLE},
        PTTState.PROCESSING: {PTTState.IDLE},
    }

    def __init__(self) -> None:
        """Initialize state machine in IDLE state"""
        self._current_state = PTTState.IDLE

    @property
    def current_state(self) -> str:
        """Get current state as string"""
        return self._current_state.value

    def transition(self, to_state: str) -> None:
        """Transition to new state.

        Args:
            to_state: Target state name

        Raises:
            ValueError: If transition is invalid
        """
        target = PTTState(to_state)

        if target not in self.TRANSITIONS[self._current_state]:
            raise ValueError(
                f"Invalid transition from {self.current_state} to {to_state}"
            )

        self._current_state = target
```

3. **Update public API:**
```python
# src/voice_mode/ptt/__init__.py
from .state_machine import PTTStateMachine, PTTState

__all__ = [
    # ... existing exports
    "PTTStateMachine",
    "PTTState",
]
```

4. **Run tests:**
```bash
python -m pytest tests/unit/ptt/test_state_machine.py -v
```

## Configuration Changes

When adding new configuration options:

1. **Add to config.py:**
```python
# In src/voice_mode/config.py
PTT_NEW_SETTING = os.getenv("CHATTA_PTT_NEW_SETTING", "default_value")
```

2. **Document in .env.ptt.example:**
```bash
# New setting description
# Options: value1, value2, value3
# Default: default_value
CHATTA_PTT_NEW_SETTING=default_value
```

3. **Add configuration test:**
```python
# In tests/unit/ptt/test_ptt_config.py
def test_new_setting_default(clean_env):
    """Test NEW_SETTING has correct default"""
    from voice_mode import config
    assert config.PTT_NEW_SETTING == "default_value"

def test_new_setting_from_env(monkeypatch):
    """Test NEW_SETTING reads from environment"""
    monkeypatch.setenv("CHATTA_PTT_NEW_SETTING", "custom_value")
    from importlib import reload
    from voice_mode import config
    reload(config)
    assert config.PTT_NEW_SETTING == "custom_value"
```

## Logging Guidelines

### Use Structured Logging

```python
from voice_mode.ptt import get_ptt_logger

# Get the PTT logger instance
ptt_logger = get_ptt_logger()

# Log events with structured data
ptt_logger.log_event("key_press", {
    "key": "space",
    "timestamp": time.time(),
    "combo_active": True
})

# Log performance timing
timer_id = ptt_logger.start_timer("recording_start")
# ... perform operation ...
duration_ms = ptt_logger.stop_timer(timer_id)
```

### Log Levels

- **Events:** Normal operation events (key presses, state transitions)
- **Timing:** Performance measurements
- **Errors:** Error conditions and exceptions
- **Debug:** Detailed diagnostic information (only when PTT_DEBUG=true)

## Error Handling

### Exception Hierarchy

```python
class PTTError(Exception):
    """Base exception for PTT module"""
    pass

class PTTPermissionError(PTTError):
    """Raised when required permissions are not available"""
    pass

class PTTConfigurationError(PTTError):
    """Raised when configuration is invalid"""
    pass

class PTTStateError(PTTError):
    """Raised when state transition is invalid"""
    pass
```

### Error Handling Pattern

```python
from voice_mode.ptt.logging import get_ptt_logger

def risky_operation() -> bool:
    """Perform operation that might fail"""
    ptt_logger = get_ppt_logger()

    try:
        # Attempt operation
        result = perform_operation()
        return True

    except PTTPermissionError as e:
        # Log structured error
        ptt_logger.log_error("permission_denied", {
            "error": str(e),
            "required_permission": "accessibility"
        })
        # Graceful degradation
        return False

    except Exception as e:
        # Log unexpected errors
        ptt_logger.log_error("unexpected_error", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        # Re-raise if critical
        raise
```

## Platform Compatibility

### Testing on Multiple Platforms

When adding platform-specific code:

```python
import platform

def get_platform_handler():
    """Get platform-specific keyboard handler"""
    system = platform.system()

    if system == "Darwin":
        return MacOSKeyboardHandler()
    elif system == "Windows":
        return WindowsKeyboardHandler()
    elif system == "Linux":
        return LinuxKeyboardHandler()
    else:
        raise PTTError(f"Unsupported platform: {system}")
```

### Platform-Specific Tests

```python
import platform
import pytest

@pytest.mark.skipif(
    platform.system() != "Darwin",
    reason="macOS-specific test"
)
def test_macos_accessibility_permissions():
    """Test macOS accessibility permission checking"""
    from voice_mode.ptt import check_macos_permissions
    # This test only runs on macOS
    assert check_macos_permissions() in [True, False]
```

## Documentation Standards

### Docstring Format

Use Google-style docstrings:

```python
def complex_function(
    param1: str,
    param2: int,
    optional_param: Optional[bool] = None
) -> Dict[str, Any]:
    """Brief one-line description.

    More detailed description if needed. Can span
    multiple lines and include implementation details.

    Args:
        param1: Description of param1
        param2: Description of param2
        optional_param: Description of optional parameter.
            Can span multiple lines if needed.

    Returns:
        Dictionary containing:
            - key1: Description of key1
            - key2: Description of key2

    Raises:
        ValueError: When param1 is empty
        PTTError: When operation fails

    Examples:
        >>> result = complex_function("test", 42)
        >>> print(result)
        {'key1': 'value1', 'key2': 'value2'}

    Note:
        Any additional notes about usage, performance,
        or platform-specific behavior.
    """
    pass
```

### README Updates

When adding significant features, update README.md:

```markdown
## New Feature

Brief description of what the feature does.

### Usage

\`\`\`python
from voice_mode.ptt import NewFeature

# Example usage
feature = NewFeature()
result = feature.do_something()
\`\`\`

### Configuration

Required environment variables:
- `CHATTA_PTT_FEATURE_ENABLED`: Enable/disable feature (default: false)
- `CHATTA_PTT_FEATURE_OPTION`: Feature option (default: value)
```

## Performance Considerations

### Benchmarking

Add performance tests for time-critical operations:

```python
import time

def test_key_detection_latency():
    """Test key detection completes in < 10ms"""
    handler = KeyboardHandler("space")

    start = time.perf_counter()
    handler._on_press(MockKey(name="space"))
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 10.0, f"Key detection took {duration_ms:.2f}ms"
```

### Optimization Guidelines

1. **Minimize allocations in hot paths**
2. **Use sets for key lookups (O(1) vs O(n))**
3. **Avoid blocking operations in keyboard thread**
4. **Cache frequently accessed values**

## Git Workflow

### Commit Messages

Follow conventional commits:

```
type(scope): brief description

Longer description if needed.

- Detail 1
- Detail 2

Refs: #issue-number
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `test`: Adding tests
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `perf`: Performance improvements

Examples:
```
feat(keyboard): add support for three-key combinations

Extends keyboard handler to support up to 3 simultaneous keys.
Maintains backward compatibility with existing two-key combos.

- Updated key combo parsing logic
- Added tests for 3-key combinations
- Updated documentation

Refs: Sprint 3.4
```

### Pull Request Process

1. **Branch from master:** `git checkout -b feature/ptt-feature-name`
2. **Make changes:** Implement feature with tests
3. **Run full test suite:** Ensure all tests pass
4. **Update documentation:** README, docstrings, TESTING.md
5. **Commit changes:** Use conventional commit messages
6. **Push branch:** `git push origin feature/ptt-feature-name`
7. **Create PR:** Include description, screenshots if applicable
8. **Address review feedback:** Make requested changes
9. **Merge:** After approval, squash and merge

## Questions and Support

- **Sprint Plan:** `/Users/az/Desktop/PTT_Feature_Sprint_Plan.md`
- **Research Docs:** `docs/research/`
- **Testing Guide:** `TESTING.md`
- **Module README:** `README.md`

## Phase 3 Preview

Upcoming components to implement:

1. **State Machine** (`state_machine.py`)
   - Manage PTT lifecycle
   - Validate state transitions
   - Handle edge cases

2. **Controller** (`controller.py`)
   - Coordinate keyboard, audio, and logging
   - Manage async/sync boundaries
   - Handle cancellation and timeout

3. **Permissions** (`permissions.py`)
   - Check platform permissions
   - Request permissions if needed
   - Graceful degradation

4. **Recorder** (`recorder.py`)
   - PTT-specific audio recording
   - Integration with existing audio system
   - Buffer management

Stay tuned for Phase 3 implementation!
