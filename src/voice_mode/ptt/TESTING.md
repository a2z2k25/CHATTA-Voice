# PTT Testing Guide

## Overview
This document describes the testing infrastructure and practices for the Push-to-Talk (PTT) module.

## Test Organization

```
tests/
├── conftest.py              # Shared pytest fixtures
├── fixtures/
│   └── ptt/
│       ├── __init__.py      # Fixture exports
│       └── test_helpers.py  # Helper utilities
├── unit/
│   └── ptt/
│       ├── test_keyboard_handler.py  # Keyboard event tests
│       ├── test_ptt_config.py        # Configuration tests
│       ├── test_ptt_logging.py       # Logging tests
│       └── test_fixtures.py          # Fixture validation
└── integration/
    └── ptt/                  # Integration tests (future)
```

## Running Tests

### Run All PTT Tests
```bash
# Activate virtual environment
source .venv/bin/activate

# Run all PTT tests with verbose output
python -m pytest tests/unit/ptt/ -v

# Run with coverage report
python -m pytest tests/unit/ptt/ --cov=voice_mode.ptt --cov-report=html

# Run specific test file
python -m pytest tests/unit/ptt/test_keyboard_handler.py -v

# Run specific test
python -m pytest tests/unit/ptt/test_keyboard_handler.py::test_key_combo_parsing -v
```

### Run with Different Output Modes
```bash
# Short traceback
python -m pytest tests/unit/ptt/ --tb=short

# No traceback (quiet)
python -m pytest tests/unit/ptt/ --tb=no -q

# Show local variables in failures
python -m pytest tests/unit/ptt/ -l
```

## Test Coverage Summary

| Component | Tests | Coverage |
|-----------|-------|----------|
| Keyboard Handler | 10 | 100% |
| Configuration | 7 | 100% |
| Logging | 16 | 100% |
| Test Fixtures | 21 | 100% |
| **Total** | **54** | **100%** |

## Available Fixtures

### Configuration Fixtures

#### `clean_env`
Removes all PTT environment variables for isolated testing.

```python
def test_default_config(clean_env):
    # PTT env vars are cleared
    assert os.getenv("CHATTA_PTT_ENABLED") is None
```

#### `ptt_config`
Provides default PTT configuration dictionary.

```python
def test_config_structure(ptt_config):
    assert ptt_config["enabled"] is False
    assert ptt_config["key_combo"] == "down+right"
```

#### `ptt_enabled_config`
Configuration with PTT enabled.

```python
def test_enabled_mode(ptt_enabled_config):
    assert ptt_enabled_config.PTT_ENABLED is True
```

### Keyboard Fixtures

#### `mock_keyboard_key()`
Factory for creating mock keyboard keys.

```python
def test_key_press(mock_keyboard_key):
    key = mock_keyboard_key(name="space")
    assert key.name == "space"
```

#### `mock_keyboard_listener`
Mock pynput keyboard listener.

```python
def test_listener(mock_keyboard_listener):
    mock_keyboard_listener.start()
    assert mock_keyboard_listener.start.called
```

#### `mock_keyboard_handler`
Mock KeyboardHandler instance with common configuration.

```python
def test_handler(mock_keyboard_handler):
    assert mock_keyboard_handler.key_combo == {"down", "right"}
```

### Audio Fixtures

#### `sample_audio_data`
1 second of silent 16kHz audio.

```python
def test_audio_processing(sample_audio_data):
    assert len(sample_audio_data) == 16000
    assert sample_audio_data.dtype == np.int16
```

#### `sample_audio_with_speech`
2 seconds of audio with simulated speech.

```python
def test_speech_detection(sample_audio_with_speech):
    assert len(sample_audio_with_speech) == 32000
    assert np.std(sample_audio_with_speech) > 0
```

### Logging Fixtures

#### `ptt_logger`
Fresh PTTLogger instance with test session ID.

```python
def test_logging(ptt_logger):
    ptt_logger.log_event("test", {"key": "value"})
    assert len(ptt_logger.events) == 1
```

#### `mock_ptt_logger`
Mock PTTLogger for testing without actual logging.

```python
def test_with_mock_logger(mock_ptt_logger):
    mock_ptt_logger.log_event("test", {})
    mock_ptt_logger.log_event.assert_called_once()
```

#### `temp_log_dir`
Temporary directory for log files.

```python
def test_log_export(ptt_logger, temp_log_dir):
    log_file = temp_log_dir / "session.jsonl"
    ptt_logger.export_session(log_file)
```

### State Machine Fixtures

#### `ptt_states`
PTT state enumeration values.

```python
def test_state_transitions(ptt_states):
    assert ptt_states["IDLE"] == "IDLE"
    assert ptt_states["RECORDING"] == "RECORDING"
```

### Helper Fixtures

#### `callback_tracker`
Tracks callback invocations during tests.

```python
def test_callbacks(callback_tracker):
    callback_tracker.on_press()
    assert callback_tracker.press_count == 1
```

#### `performance_thresholds`
Performance threshold values for testing.

```python
def test_performance(performance_thresholds):
    assert duration_ms <= performance_thresholds["key_detection"]
```

#### `full_ptt_stack`
Complete PTT stack for integration testing.

```python
def test_integration(full_ptt_stack):
    keyboard = full_ptt_stack["keyboard"]
    logger = full_ptt_stack["logger"]
    # Test full interaction
```

## Test Helper Functions

### Event Assertions

#### `assert_ptt_event_logged()`
Assert that a specific event was logged.

```python
from tests.fixtures.ptt.test_helpers import assert_ptt_event_logged

def test_key_press_logging(ptt_logger, handler):
    handler.simulate_press("space")
    assert_ptt_event_logged(ptt_logger, "key_press", expected_count=1)
```

#### `assert_state_transition()`
Assert that a state transition occurred.

```python
from tests.fixtures.ptt.test_helpers import assert_state_transition

def test_recording_start(ptt_logger):
    # ... trigger recording ...
    assert_state_transition(ptt_logger, "IDLE", "RECORDING")
```

### Timing Assertions

#### `assert_timing_within_threshold()`
Assert operation completed within time threshold.

```python
from tests.fixtures.ptt.test_helpers import assert_timing_within_threshold

def test_key_detection_speed():
    start = time.time()
    handler.detect_key()
    duration_ms = (time.time() - start) * 1000
    assert_timing_within_threshold(duration_ms, 10.0, "key_detection")
```

#### `assert_performance_acceptable()`
Assert all timing events for an operation are within threshold.

```python
from tests.fixtures.ptt.test_helpers import assert_performance_acceptable

def test_recording_performance(ptt_logger):
    # ... perform recording operations ...
    assert_performance_acceptable(ptt_logger, "recording_start", 100.0)
```

### Mock Utilities

#### `create_mock_key_sequence()`
Create sequence of mock keyboard keys.

```python
from tests.fixtures.ptt.test_helpers import create_mock_key_sequence

def test_key_combo():
    keys = create_mock_key_sequence(["ctrl", "alt", "space"])
    assert len(keys) == 3
```

#### `create_test_audio()`
Create test audio data with configurable parameters.

```python
from tests.fixtures.ptt.test_helpers import create_test_audio

def test_audio_processing():
    # 0.5 seconds of silence
    silence = create_test_audio(sample_rate=16000, duration=0.5, noise_level=0)

    # 1 second with noise
    noisy = create_test_audio(sample_rate=16000, duration=1.0, noise_level=100)
```

## Writing New Tests

### Test Structure Template

```python
import pytest
from voice_mode.ptt import KeyboardHandler
from tests.fixtures.ptt.test_helpers import assert_ptt_event_logged

class TestFeatureName:
    """Test suite for feature X"""

    def test_basic_functionality(self, fixture_name):
        """Test basic feature behavior"""
        # Arrange
        handler = KeyboardHandler("space")

        # Act
        result = handler.do_something()

        # Assert
        assert result is True

    def test_error_handling(self):
        """Test error conditions"""
        with pytest.raises(ValueError):
            handler.do_invalid_thing()

    @pytest.mark.parametrize("input,expected", [
        ("space", True),
        ("invalid", False),
    ])
    def test_multiple_inputs(self, input, expected):
        """Test with multiple input values"""
        result = process(input)
        assert result == expected
```

### Testing Async Code

```python
import pytest
import asyncio

class TestAsyncFeature:
    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async functionality"""
        result = await async_function()
        assert result is not None
```

### Testing Platform-Specific Code

```python
import platform
import pytest

class TestPlatformSpecific:
    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS-specific test"
    )
    def test_macos_feature(self):
        """Test macOS-specific functionality"""
        assert check_macos_permissions() is True
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures to provide fresh state
- Clean up resources in teardown

```python
@pytest.fixture
def clean_state():
    # Setup
    state = create_fresh_state()
    yield state
    # Teardown
    state.cleanup()
```

### 2. Descriptive Test Names
```python
# Good
def test_keyboard_handler_detects_two_key_combo():
    pass

# Bad
def test_keys():
    pass
```

### 3. Arrange-Act-Assert Pattern
```python
def test_feature():
    # Arrange - set up test data
    handler = KeyboardHandler("space")

    # Act - perform the action
    result = handler.process_key()

    # Assert - verify results
    assert result is True
```

### 4. Use Parametrize for Multiple Cases
```python
@pytest.mark.parametrize("combo,expected", [
    ("space", {"space"}),
    ("ctrl+c", {"ctrl", "c"}),
    ("down+right", {"down", "right"}),
])
def test_key_combo_parsing(combo, expected):
    handler = KeyboardHandler(combo)
    assert handler.key_combo == expected
```

### 5. Test Both Success and Failure
```python
def test_valid_input():
    assert process("valid") is True

def test_invalid_input():
    with pytest.raises(ValueError):
        process("invalid")
```

### 6. Mock External Dependencies
```python
from unittest.mock import Mock, patch

def test_with_mocked_dependency():
    with patch("voice_mode.ptt.keyboard.Listener") as mock_listener:
        mock_listener.return_value = Mock()
        handler = KeyboardHandler()
        handler.start()
        mock_listener.assert_called_once()
```

## Continuous Integration

### Pre-commit Checks
```bash
# Run before committing
python -m pytest tests/unit/ptt/ --cov=voice_mode.ptt --cov-report=term-missing
```

### CI Pipeline (Future)
```yaml
# .github/workflows/ptt-tests.yml
name: PTT Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: [3.10, 3.11, 3.12]
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest tests/unit/ptt/ -v --cov=voice_mode.ptt
```

## Performance Testing

### Benchmarking
```python
import time

def test_key_detection_performance(benchmark):
    """Test key detection speed"""
    handler = KeyboardHandler("space")

    def detect_key():
        handler._on_press(MockKey(name="space"))

    result = benchmark(detect_key)
    assert result < 0.010  # Less than 10ms
```

### Load Testing
```python
def test_rapid_key_presses(ptt_logger):
    """Test handling 100 rapid key presses"""
    handler = KeyboardHandler("space", logger=ptt_logger)

    for _ in range(100):
        handler._on_press(MockKey(name="space"))
        handler._on_release(MockKey(name="space"))

    # Should handle all without errors
    assert len(ptt_logger.events) == 200  # 100 press + 100 release
```

## Troubleshooting Tests

### Common Issues

#### Tests Not Discovered
```bash
# Ensure __init__.py exists in test directories
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/unit/ptt/__init__.py
```

#### Fixture Not Found
```bash
# Ensure conftest.py is in the right location
# pytest looks for conftest.py in test directory and parents
ls tests/conftest.py  # Should exist
```

#### Import Errors
```bash
# Ensure package is installed in development mode
pip install -e .

# Or activate virtual environment
source .venv/bin/activate
```

#### Mocks Not Working
```python
# Ensure you're patching the right path
# Patch where the object is USED, not where it's DEFINED

# If keyboard.py imports: from pynput.keyboard import Listener
# Then patch it in keyboard module:
with patch("voice_mode.ptt.keyboard.Listener"):
    # Not patch("pynput.keyboard.Listener")
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [PTT Sprint Plan](/Users/az/Desktop/PTT_Feature_Sprint_Plan.md)
