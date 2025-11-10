"""
Push-to-Talk (PTT) module for CHATTA voice mode.

This module provides keyboard-controlled voice recording functionality,
allowing users to control when audio recording starts and stops via
configurable key combinations.

Features:
- Hold-to-record mode
- Toggle mode (press to start/stop)
- Hybrid mode (hold + silence detection)
- Cross-platform support (macOS, Windows, Linux)
- Graceful fallback when permissions unavailable

Usage:
    from voice_mode.ptt import PTTController

    controller = PTTController()
    audio_data = await controller.record_with_ptt()
"""

__version__ = "0.1.0"

# Import public components
from .logging import PTTLogger, PTTEvent, get_ptt_logger, reset_ptt_logger
from .keyboard import KeyboardHandler, check_keyboard_permissions
from .state_machine import (
    PTTState,
    PTTStateMachine,
    StateTransition,
    create_ptt_state_machine
)
from .controller import PTTController, create_ptt_controller
from .recorder import (
    PTTRecorder,
    AsyncPTTRecorder,
    create_ptt_recorder,
    create_async_ptt_recorder
)

# Public API
__all__ = [
    # Logging
    "PTTLogger",
    "PTTEvent",
    "get_ptt_logger",
    "reset_ptt_logger",

    # Keyboard
    "KeyboardHandler",
    "check_keyboard_permissions",

    # State Machine
    "PTTState",
    "PTTStateMachine",
    "StateTransition",
    "create_ptt_state_machine",

    # Controller
    "PTTController",
    "create_ptt_controller",

    # Recorder
    "PTTRecorder",
    "AsyncPTTRecorder",
    "create_ptt_recorder",
    "create_async_ptt_recorder",
]
