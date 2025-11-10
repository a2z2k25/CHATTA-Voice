# PTT Testing Strategy
Date: November 9, 2025
Sprint: 1.7

## Test Coverage Requirements

### Target Metrics
- **Unit Test Coverage**: >90%
- **Integration Test Coverage**: >80%
- **Platform Coverage**: macOS, Windows, Linux
- **Performance Regression**: <5%
- **Memory Leak Detection**: 0 leaks

## Unit Testing Approach

### 1. State Machine Tests

```python
# tests/unit/test_ptt_state_machine.py
import pytest
from voice_mode.ptt.controller import PTTState, PTTController

class TestPTTStateMachine:
    """Test PTT state transitions"""

    def test_initial_state(self):
        controller = PTTController()
        assert controller.state == PTTState.IDLE

    def test_enable_transition(self):
        controller = PTTController()
        controller.enable()
        assert controller.state == PTTState.WAITING_FOR_KEY

    def test_key_press_transition(self):
        controller = PTTController()
        controller.enable()
        controller.handle_key_down()
        assert controller.state == PTTState.KEY_PRESSED

    def test_invalid_transition(self):
        controller = PTTController()
        with pytest.raises(InvalidStateTransition):
            controller.handle_key_down()  # Can't press key when IDLE

    @pytest.mark.parametrize("from_state,event,to_state", [
        (PTTState.IDLE, "enable", PTTState.WAITING_FOR_KEY),
        (PTTState.WAITING_FOR_KEY, "key_down", PTTState.KEY_PRESSED),
        (PTTState.RECORDING, "key_up", PTTState.RECORDING_STOPPED),
        (PTTState.RECORDING, "cancel", PTTState.RECORDING_CANCELLED),
    ])
    def test_all_transitions(self, from_state, event, to_state):
        """Test all valid state transitions"""
        controller = PTTController()
        controller.state = from_state
        controller.handle_event(event)
        assert controller.state == to_state
```

### 2. Keyboard Handler Tests

```python
# tests/unit/test_keyboard_handler.py
from unittest.mock import Mock, patch
from voice_mode.ptt.keyboard import KeyboardHandler

class TestKeyboardHandler:
    """Test keyboard event handling"""

    @patch('pynput.keyboard.Listener')
    def test_listener_creation(self, mock_listener):
        handler = KeyboardHandler()
        handler.start()
        mock_listener.assert_called_once()

    def test_key_combination_detection(self):
        handler = KeyboardHandler(key_combo="ctrl+space")
        handler.on_press(Mock(name='ctrl'))
        handler.on_press(Mock(name='space'))
        assert handler.combo_pressed

    def test_debouncing(self):
        handler = KeyboardHandler(debounce_ms=100)
        handler.on_press(Mock())
        handler.on_press(Mock())  # Should be ignored
        assert handler.event_count == 1

    def test_modifier_handling(self):
        handler = KeyboardHandler()
        ctrl_key = Mock()
        ctrl_key.name = 'ctrl'
        handler.on_press(ctrl_key)
        assert 'ctrl' in handler.pressed_keys
```

### 3. Configuration Tests

```python
# tests/unit/test_ptt_config.py
import os
import tempfile
from voice_mode.ptt.config import PTTConfig

class TestPTTConfiguration:
    """Test configuration management"""

    def test_default_values(self):
        config = PTTConfig()
        assert config.get("key_combo") == "down+right"
        assert config.get("mode") == "hold"

    def test_env_override(self):
        os.environ["CHATTA_PTT_KEY_COMBO"] = "ctrl+alt"
        config = PTTConfig()
        assert config.get("key_combo") == "ctrl+alt"

    def test_config_file_loading(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml") as f:
            f.write(b"key_combo: space\nmode: toggle")
            f.flush()
            config = PTTConfig(config_file=f.name)
            assert config.get("mode") == "toggle"

    def test_validation(self):
        config = PTTConfig()
        # Invalid key combo
        with pytest.raises(ValueError):
            config.set("key_combo", "ctrl+c")  # Reserved
```

## Integration Testing

### 1. End-to-End PTT Flow

```python
# tests/integration/test_ptt_e2e.py
import asyncio
from voice_mode.tools.converse import converse

class TestPTTE2E:
    """Test complete PTT flow"""

    @pytest.mark.asyncio
    async def test_ptt_recording_flow(self, mock_audio):
        """Test full PTT recording cycle"""

        # Simulate PTT conversation
        result = await converse(
            "Test message",
            push_to_talk=True,
            ptt_key_combo="space"
        )

        # Verify flow executed
        assert mock_audio.recording_started
        assert mock_audio.recording_stopped
        assert result == "transcribed text"

    @pytest.mark.asyncio
    async def test_ptt_cancellation(self, mock_keyboard):
        """Test ESC key cancellation"""

        # Start PTT recording
        task = asyncio.create_task(
            converse("Test", push_to_talk=True)
        )

        # Simulate ESC press
        await asyncio.sleep(0.5)
        mock_keyboard.press_escape()

        result = await task
        assert "cancelled" in result.lower()
```

### 2. Platform-Specific Tests

```python
# tests/integration/test_platform_specific.py
import platform
import pytest

class TestPlatformIntegration:
    """Platform-specific integration tests"""

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
    def test_macos_accessibility(self):
        """Test macOS accessibility permission check"""
        from voice_mode.ptt.permissions import check_macos_accessibility
        result = check_macos_accessibility()
        # Should return False in CI (no permissions)
        assert result is False

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
    def test_windows_hook(self):
        """Test Windows keyboard hook"""
        from voice_mode.ptt.keyboard import WindowsKeyboardHandler
        handler = WindowsKeyboardHandler()
        handler.install_hook()
        assert handler.hook_installed

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux only")
    def test_linux_x11(self):
        """Test Linux X11 keyboard monitoring"""
        from voice_mode.ptt.keyboard import LinuxKeyboardHandler
        handler = LinuxKeyboardHandler()
        assert handler.display_server in ["x11", "wayland"]
```

## Manual Testing Checklist

### Basic Functionality
- [ ] PTT enables without errors
- [ ] Key combination detected correctly
- [ ] Recording starts on key press
- [ ] Recording stops on key release
- [ ] Audio quality acceptable
- [ ] Transcription accurate
- [ ] Visual feedback displays

### Key Combinations
- [ ] Default keys (↓+→) work
- [ ] Custom keys configurable
- [ ] Single key mode works
- [ ] Modifier keys work (Ctrl, Alt, Shift)
- [ ] Function keys work (F1-F24)
- [ ] Reserved keys blocked (Ctrl+C)

### Modes
- [ ] Hold mode: Records while held
- [ ] Toggle mode: Press to start/stop
- [ ] Hybrid mode: Hold + silence detection
- [ ] Mode switching works

### Error Handling
- [ ] Permission denied handled gracefully
- [ ] Microphone busy handled
- [ ] Device disconnection recovery
- [ ] Network interruption recovery
- [ ] Timeout enforcement

### Platform Testing
- [ ] macOS: Accessibility prompt shown
- [ ] macOS: Works after permission grant
- [ ] Windows: No elevation required
- [ ] Windows: SmartScreen handled
- [ ] Linux/X11: Works without root
- [ ] Linux/Wayland: Fallback message shown

### Performance
- [ ] Response time <100ms
- [ ] No audio dropouts
- [ ] No memory leaks
- [ ] CPU usage acceptable
- [ ] Thread cleanup verified

## Edge Cases & Stress Tests

### Edge Cases to Test

```python
# tests/edge_cases/test_ptt_edge_cases.py

class TestPTTEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_rapid_key_press_release(self):
        """Test rapid key press/release cycles"""
        # Should debounce properly

    def test_simultaneous_recordings(self):
        """Test preventing concurrent recordings"""
        # Should block second recording

    def test_max_duration_enforcement(self):
        """Test automatic stop at max duration"""
        # Should stop at configured timeout

    def test_min_duration_enforcement(self):
        """Test minimum recording duration"""
        # Should record at least min_duration

    def test_system_sleep_resume(self):
        """Test behavior across system sleep"""
        # Should recover gracefully

    def test_permission_revocation_during_use(self):
        """Test permission revoked while recording"""
        # Should handle gracefully

    def test_audio_device_switching(self):
        """Test switching audio devices mid-recording"""
        # Should continue or recover

    def test_keyboard_layout_changes(self):
        """Test keyboard layout switching"""
        # Should adapt to new layout
```

### Stress Testing

```python
# tests/stress/test_ptt_stress.py

class TestPTTStress:
    """Stress testing for PTT"""

    def test_long_recording_session(self):
        """Test 1 hour continuous recording"""
        # Memory should stay stable

    def test_thousand_key_events(self):
        """Test 1000 key press/release cycles"""
        # Should handle without errors

    def test_parallel_operations(self):
        """Test PTT with heavy background load"""
        # Should maintain responsiveness

    def test_memory_pressure(self):
        """Test under low memory conditions"""
        # Should degrade gracefully
```

## Performance Benchmarks

```python
# tests/performance/test_ptt_performance.py
import time
import memory_profiler

class TestPTTPerformance:
    """Performance benchmarking"""

    def test_response_latency(self):
        """Measure key press to recording start"""
        start = time.perf_counter()
        # Trigger PTT
        latency = time.perf_counter() - start
        assert latency < 0.1  # 100ms max

    def test_cpu_usage(self):
        """Measure CPU usage during recording"""
        # Should stay under 5% for monitoring

    @memory_profiler.profile
    def test_memory_usage(self):
        """Profile memory consumption"""
        # Should not exceed 50MB additional

    def test_thread_overhead(self):
        """Measure thread creation/cleanup"""
        # Should complete in <10ms
```

## Test Data & Fixtures

```python
# tests/fixtures/ptt_fixtures.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_keyboard():
    """Mock keyboard for testing"""
    keyboard = Mock()
    keyboard.pressed_keys = set()
    return keyboard

@pytest.fixture
def mock_audio():
    """Mock audio system"""
    audio = Mock()
    audio.sample_rate = 16000
    audio.channels = 1
    return audio

@pytest.fixture
def sample_audio_data():
    """Sample audio data for testing"""
    import numpy as np
    # 1 second of silence
    return np.zeros(16000, dtype=np.int16)

@pytest.fixture
def ptt_config():
    """Test configuration"""
    return {
        "key_combo": "space",
        "mode": "hold",
        "timeout": 10.0
    }
```

## Continuous Integration

### CI Test Matrix

```yaml
# .github/workflows/ptt_tests.yml
name: PTT Tests

on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ["3.10", "3.11", "3.12"]

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python }}

      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt
          pip install pynput

      - name: Run unit tests
        run: pytest tests/unit/test_ptt_*.py -v

      - name: Run integration tests
        run: pytest tests/integration/test_ptt_*.py -v

      - name: Check coverage
        run: |
          pytest --cov=voice_mode.ptt --cov-report=xml
          codecov
```

## Test Reporting

### Coverage Report Format
```
Module                     Coverage
--------------------------------------
ptt/controller.py          95%
ptt/keyboard.py           92%
ptt/config.py             98%
ptt/permissions.py        85%
ptt/recorder.py           90%
--------------------------------------
Total                      92%
```

### Performance Report Format
```
Metric                    Target    Actual   Status
-----------------------------------------------------
Response Latency         <100ms     87ms      ✅
Memory Usage            <50MB      42MB      ✅
CPU Usage               <5%        3.2%      ✅
Thread Overhead         <10ms      8ms       ✅
```

## Test Documentation

Each test should include:
1. **Purpose**: What is being tested
2. **Setup**: Required configuration
3. **Steps**: How to execute
4. **Expected**: What should happen
5. **Cleanup**: Resource cleanup

Example:
```python
def test_ptt_timeout():
    """
    Test that PTT recording stops at configured timeout.

    Setup:
        - Configure timeout to 5 seconds
        - Enable PTT mode

    Steps:
        1. Start PTT recording
        2. Hold keys for 10 seconds

    Expected:
        - Recording stops at 5 seconds
        - Timeout event logged

    Cleanup:
        - Stop recording
        - Reset configuration
    """
```