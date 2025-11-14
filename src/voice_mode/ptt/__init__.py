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
from .transport_adapter import (
    record_with_ptt,
    record_with_ptt_fallback,
    get_recording_function,
    PTTRecordingSession
)
from .visual_feedback import (
    PTTVisualFeedback,
    get_visual_feedback,
    reset_visual_feedback,
    create_visual_feedback_callbacks
)
from .status_display import (
    PTTStatusDisplay,
    DisplayStyle,
    get_status_display,
    reset_status_display
)
from .terminal_utils import (
    supports_color,
    colorize,
    Color,
    Style,
    bold,
    green,
    red,
    yellow,
    cyan
)
from .audio_feedback import (
    PTTAudioFeedback,
    PTTAudioEvent,
    get_audio_feedback,
    reset_audio_feedback,
    create_audio_feedback_callbacks,
    play_ptt_tone
)
from .audio_tones import (
    generate_sine_wave,
    generate_beep,
    ptt_start_tone,
    ptt_stop_tone,
    ptt_cancel_tone,
    ptt_waiting_tone,
    ptt_error_tone
)
from .statistics import (
    PTTStatistics,
    PTTOutcome,
    PTTRecordingStats,
    PTTSessionStats,
    get_ptt_statistics,
    reset_ptt_statistics,
    create_statistics_callbacks
)
from .config_validation import (
    PTTConfigValidator,
    ValidationLevel,
    ValidationIssue,
    validate_ptt_config,
    get_config_from_env,
    validate_current_config
)
from .permissions import (
    PTTPermissionsChecker,
    PermissionStatus,
    check_ptt_permissions,
    print_permission_instructions,
    verify_ptt_can_run
)
from .setup_helper import (
    PTTSetupWizard,
    run_ptt_setup_wizard,
    check_ptt_prerequisites,
    diagnose_ptt_setup,
    print_quick_start_guide
)
from .error_messages import (
    PTTError,
    PTTErrorCode,
    PTTErrorMessages,
    get_error_messages,
    format_exception,
    raise_keyboard_init_failed,
    raise_permissions_denied,
    raise_library_missing,
    raise_invalid_mode,
    raise_invalid_key_combo,
    raise_recording_failed,
    raise_timeout_exceeded,
    raise_audio_device_error,
    raise_already_recording,
    raise_not_recording
)
from .help_system import (
    PTTHelpSystem,
    HelpTopic,
    get_help_system,
    get_help,
    list_help_topics,
    get_faq,
    search_help,
    print_help,
    print_faq,
    print_help_topics
)
from .cancel_handler import (
    CancelReason,
    CancelEvent,
    PTTCancelHandler,
    CancelFeedbackManager,
    get_cancel_handler,
    reset_cancel_handler,
    create_cancel_callbacks,
    format_cancel_stats
)
from .performance import (
    PerformanceMetrics,
    PerformanceTarget,
    PTTPerformanceMonitor,
    PerformanceBenchmark,
    get_performance_monitor,
    reset_performance_monitor,
    benchmark_ptt_performance,
    get_performance_report
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

    # Transport Adapter
    "record_with_ptt",
    "record_with_ptt_fallback",
    "get_recording_function",
    "PTTRecordingSession",

    # Visual Feedback
    "PTTVisualFeedback",
    "get_visual_feedback",
    "reset_visual_feedback",
    "create_visual_feedback_callbacks",

    # Status Display
    "PTTStatusDisplay",
    "DisplayStyle",
    "get_status_display",
    "reset_status_display",

    # Terminal Utils
    "supports_color",
    "colorize",
    "Color",
    "Style",
    "bold",
    "green",
    "red",
    "yellow",
    "cyan",

    # Audio Feedback
    "PTTAudioFeedback",
    "PTTAudioEvent",
    "get_audio_feedback",
    "reset_audio_feedback",
    "create_audio_feedback_callbacks",
    "play_ptt_tone",

    # Audio Tones
    "generate_sine_wave",
    "generate_beep",
    "ptt_start_tone",
    "ptt_stop_tone",
    "ptt_cancel_tone",
    "ptt_waiting_tone",
    "ptt_error_tone",

    # Statistics
    "PTTStatistics",
    "PTTOutcome",
    "PTTRecordingStats",
    "PTTSessionStats",
    "get_ptt_statistics",
    "reset_ptt_statistics",
    "create_statistics_callbacks",

    # Configuration & Validation
    "PTTConfigValidator",
    "ValidationLevel",
    "ValidationIssue",
    "validate_ptt_config",
    "get_config_from_env",
    "validate_current_config",

    # Permissions
    "PTTPermissionsChecker",
    "PermissionStatus",
    "check_ptt_permissions",
    "print_permission_instructions",
    "verify_ptt_can_run",

    # Setup & Diagnostics
    "PTTSetupWizard",
    "run_ptt_setup_wizard",
    "check_ptt_prerequisites",
    "diagnose_ptt_setup",
    "print_quick_start_guide",

    # Error Messages
    "PTTError",
    "PTTErrorCode",
    "PTTErrorMessages",
    "get_error_messages",
    "format_exception",
    "raise_keyboard_init_failed",
    "raise_permissions_denied",
    "raise_library_missing",
    "raise_invalid_mode",
    "raise_invalid_key_combo",
    "raise_recording_failed",
    "raise_timeout_exceeded",
    "raise_audio_device_error",
    "raise_already_recording",
    "raise_not_recording",

    # Help System
    "PTTHelpSystem",
    "HelpTopic",
    "get_help_system",
    "get_help",
    "list_help_topics",
    "get_faq",
    "search_help",
    "print_help",
    "print_faq",
    "print_help_topics",

    # Cancel Handler
    "CancelReason",
    "CancelEvent",
    "PTTCancelHandler",
    "CancelFeedbackManager",
    "get_cancel_handler",
    "reset_cancel_handler",
    "create_cancel_callbacks",
    "format_cancel_stats",

    # Performance
    "PerformanceMetrics",
    "PerformanceTarget",
    "PTTPerformanceMonitor",
    "PerformanceBenchmark",
    "get_performance_monitor",
    "reset_performance_monitor",
    "benchmark_ptt_performance",
    "get_performance_report",
]
