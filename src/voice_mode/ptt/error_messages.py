"""
PTT error messages and help system.

Provides clear, actionable error messages with context-sensitive suggestions
and links to documentation.
"""

import sys
from typing import Optional, Dict, Any
from enum import Enum

from voice_mode.ptt.logging import get_ptt_logger


class PTTErrorCode(Enum):
    """PTT error codes for categorization."""

    # Initialization errors
    KEYBOARD_INIT_FAILED = "keyboard_init_failed"
    PERMISSIONS_DENIED = "permissions_denied"
    LIBRARY_MISSING = "library_missing"

    # Configuration errors
    INVALID_MODE = "invalid_mode"
    INVALID_KEY_COMBO = "invalid_key_combo"
    INVALID_CONFIG = "invalid_config"

    # Runtime errors
    RECORDING_FAILED = "recording_failed"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    AUDIO_DEVICE_ERROR = "audio_device_error"
    KEY_PRESS_ERROR = "key_press_error"

    # State errors
    ALREADY_RECORDING = "already_recording"
    NOT_RECORDING = "not_recording"
    INVALID_STATE = "invalid_state"


class PTTError(Exception):
    """
    PTT error with enhanced error messages.

    Provides:
    - Clear error description
    - Actionable suggestions
    - Platform-specific guidance
    - Links to documentation
    """

    def __init__(
        self,
        code: PTTErrorCode,
        message: str,
        suggestion: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize PTT error.

        Args:
            code: Error code for categorization
            message: Human-readable error message
            suggestion: Actionable suggestion to fix the error
            context: Additional error context
        """
        self.code = code
        self.message = message
        self.suggestion = suggestion
        self.context = context or {}

        super().__init__(self.format_error())

    def format_error(self) -> str:
        """
        Format error with all details.

        Returns:
            Formatted error string
        """
        lines = [
            f"PTT Error [{self.code.value}]",
            f"{self.message}"
        ]

        if self.suggestion:
            lines.append(f"\nSuggestion: {self.suggestion}")

        if self.context:
            lines.append(f"\nContext: {self.context}")

        # Add documentation link
        doc_url = self._get_doc_url()
        if doc_url:
            lines.append(f"\nDocumentation: {doc_url}")

        return "\n".join(lines)

    def _get_doc_url(self) -> Optional[str]:
        """Get documentation URL for error code."""
        base_url = "https://github.com/yourusername/chatta/blob/main/docs/ptt"

        doc_map = {
            PTTErrorCode.KEYBOARD_INIT_FAILED: f"{base_url}/troubleshooting.md#keyboard-initialization",
            PTTErrorCode.PERMISSIONS_DENIED: f"{base_url}/setup.md#permissions",
            PTTErrorCode.LIBRARY_MISSING: f"{base_url}/installation.md#dependencies",
            PTTErrorCode.INVALID_MODE: f"{base_url}/configuration.md#ptt-mode",
            PTTErrorCode.INVALID_KEY_COMBO: f"{base_url}/configuration.md#key-combination",
            PTTErrorCode.RECORDING_FAILED: f"{base_url}/troubleshooting.md#recording-issues",
            PTTErrorCode.AUDIO_DEVICE_ERROR: f"{base_url}/troubleshooting.md#audio-device",
        }

        return doc_map.get(self.code)


class PTTErrorMessages:
    """
    PTT error message builder.

    Provides platform-specific, context-aware error messages.
    """

    def __init__(self):
        """Initialize error message builder."""
        self.logger = get_ptt_logger()
        self.platform = sys.platform

    def keyboard_init_failed(self, original_error: Exception) -> PTTError:
        """Error: Keyboard initialization failed."""
        if self.platform == 'darwin':
            suggestion = (
                "Grant accessibility permissions:\n"
                "1. Open System Settings → Privacy & Security → Accessibility\n"
                "2. Add your terminal application\n"
                "3. Restart your terminal"
            )
        elif self.platform == 'linux':
            suggestion = (
                "Check display server and permissions:\n"
                "1. Verify you're running X11 or Wayland\n"
                "2. Ensure your user has input device access\n"
                "3. Try running with: GDK_BACKEND=x11"
            )
        else:
            suggestion = "Check that pynput library is properly installed and your application has keyboard access."

        return PTTError(
            code=PTTErrorCode.KEYBOARD_INIT_FAILED,
            message=f"Failed to initialize keyboard listener: {original_error}",
            suggestion=suggestion,
            context={'platform': self.platform, 'original_error': str(original_error)}
        )

    def permissions_denied(self) -> PTTError:
        """Error: Permissions denied for keyboard access."""
        if self.platform == 'darwin':
            message = "Accessibility permissions required for keyboard monitoring"
            suggestion = (
                "macOS requires accessibility permissions:\n"
                "1. Open System Settings (or System Preferences)\n"
                "2. Go to Privacy & Security → Accessibility\n"
                "3. Find your terminal application (Terminal, iTerm, VS Code, etc.)\n"
                "4. Enable the checkbox\n"
                "5. Restart your terminal application"
            )
        elif self.platform == 'linux':
            message = "Keyboard access permissions may be restricted"
            suggestion = (
                "Linux keyboard access options:\n"
                "1. Ensure you're in the 'input' group: sudo usermod -a -G input $USER\n"
                "2. Try X11 if on Wayland: export GDK_BACKEND=x11\n"
                "3. Check compositor keyboard grab settings"
            )
        else:
            message = "Keyboard access permissions denied"
            suggestion = "Ensure your application has permission to monitor keyboard input."

        return PTTError(
            code=PTTErrorCode.PERMISSIONS_DENIED,
            message=message,
            suggestion=suggestion,
            context={'platform': self.platform}
        )

    def library_missing(self, library_name: str) -> PTTError:
        """Error: Required library is missing."""
        install_cmd = {
            'pynput': 'pip install pynput',
            'sounddevice': 'pip install sounddevice',
            'numpy': 'pip install numpy',
            'pyaudio': 'pip install pyaudio'
        }.get(library_name, f'pip install {library_name}')

        return PTTError(
            code=PTTErrorCode.LIBRARY_MISSING,
            message=f"Required library '{library_name}' is not installed",
            suggestion=f"Install with: {install_cmd}",
            context={'library': library_name, 'install_command': install_cmd}
        )

    def invalid_mode(self, mode: str) -> PTTError:
        """Error: Invalid PTT mode."""
        return PTTError(
            code=PTTErrorCode.INVALID_MODE,
            message=f"Invalid PTT mode: '{mode}'",
            suggestion="Valid modes are: 'hold', 'toggle', or 'hybrid'. Set CHATTA_PTT_MODE environment variable.",
            context={'invalid_mode': mode, 'valid_modes': ['hold', 'toggle', 'hybrid']}
        )

    def invalid_key_combo(self, key_combo: str, reason: Optional[str] = None) -> PTTError:
        """Error: Invalid key combination."""
        message = f"Invalid key combination: '{key_combo}'"
        if reason:
            message += f" - {reason}"

        suggestion = (
            "Use valid key names separated by '+'\n"
            "Examples:\n"
            "  - down+right (arrow keys)\n"
            "  - ctrl+space (modifier + key)\n"
            "  - f12 (single key)\n"
            "Set CHATTA_PTT_KEY_COMBO environment variable."
        )

        return PTTError(
            code=PTTErrorCode.INVALID_KEY_COMBO,
            message=message,
            suggestion=suggestion,
            context={'key_combo': key_combo, 'reason': reason}
        )

    def recording_failed(self, reason: str) -> PTTError:
        """Error: Recording operation failed."""
        suggestion = (
            "Troubleshooting steps:\n"
            "1. Check that audio device is available and not in use\n"
            "2. Verify microphone permissions are granted\n"
            "3. Try with a different audio device\n"
            "4. Check audio settings: python -m voice_mode.ptt.setup_helper --diagnose"
        )

        return PTTError(
            code=PTTErrorCode.RECORDING_FAILED,
            message=f"Recording failed: {reason}",
            suggestion=suggestion,
            context={'reason': reason}
        )

    def timeout_exceeded(self, timeout: float) -> PTTError:
        """Error: Recording timeout exceeded."""
        return PTTError(
            code=PTTErrorCode.TIMEOUT_EXCEEDED,
            message=f"Recording exceeded timeout of {timeout} seconds",
            suggestion=(
                f"To allow longer recordings, increase CHATTA_PTT_TIMEOUT:\n"
                f"  export CHATTA_PTT_TIMEOUT=300  # 5 minutes"
            ),
            context={'timeout': timeout}
        )

    def audio_device_error(self, device_info: Optional[str] = None) -> PTTError:
        """Error: Audio device error."""
        message = "Audio device error"
        if device_info:
            message += f": {device_info}"

        suggestion = (
            "Audio device troubleshooting:\n"
            "1. Check device is connected and recognized\n"
            "2. List available devices: python -c 'import sounddevice; print(sounddevice.query_devices())'\n"
            "3. Try default device or specify device manually\n"
            "4. Check system audio settings"
        )

        return PTTError(
            code=PTTErrorCode.AUDIO_DEVICE_ERROR,
            message=message,
            suggestion=suggestion,
            context={'device_info': device_info}
        )

    def already_recording(self) -> PTTError:
        """Error: Already recording."""
        return PTTError(
            code=PTTErrorCode.ALREADY_RECORDING,
            message="PTT is already recording",
            suggestion="Wait for current recording to finish or cancel it before starting a new one.",
            context={}
        )

    def not_recording(self) -> PTTError:
        """Error: Not currently recording."""
        return PTTError(
            code=PTTErrorCode.NOT_RECORDING,
            message="PTT is not currently recording",
            suggestion="Start recording first by pressing the PTT key.",
            context={}
        )


# Global error message builder
_error_messages: Optional[PTTErrorMessages] = None


def get_error_messages() -> PTTErrorMessages:
    """
    Get global PTT error messages instance.

    Returns:
        PTTErrorMessages instance
    """
    global _error_messages

    if _error_messages is None:
        _error_messages = PTTErrorMessages()

    return _error_messages


def format_exception(exc: Exception) -> str:
    """
    Format exception with PTT-specific enhancements.

    Args:
        exc: Exception to format

    Returns:
        Formatted exception string
    """
    if isinstance(exc, PTTError):
        return exc.format_error()

    # Handle common exceptions
    error_msgs = get_error_messages()

    if isinstance(exc, ImportError):
        # Extract library name from error message
        msg = str(exc)
        if 'pynput' in msg:
            return error_msgs.library_missing('pynput').format_error()
        elif 'sounddevice' in msg:
            return error_msgs.library_missing('sounddevice').format_error()
        elif 'numpy' in msg:
            return error_msgs.library_missing('numpy').format_error()

    if isinstance(exc, PermissionError):
        return error_msgs.permissions_denied().format_error()

    # Default formatting
    return f"PTT Error: {exc}"


# Common error shortcuts
def raise_keyboard_init_failed(original_error: Exception):
    """Raise keyboard initialization error."""
    raise get_error_messages().keyboard_init_failed(original_error)


def raise_permissions_denied():
    """Raise permissions denied error."""
    raise get_error_messages().permissions_denied()


def raise_library_missing(library_name: str):
    """Raise library missing error."""
    raise get_error_messages().library_missing(library_name)


def raise_invalid_mode(mode: str):
    """Raise invalid mode error."""
    raise get_error_messages().invalid_mode(mode)


def raise_invalid_key_combo(key_combo: str, reason: Optional[str] = None):
    """Raise invalid key combination error."""
    raise get_error_messages().invalid_key_combo(key_combo, reason)


def raise_recording_failed(reason: str):
    """Raise recording failed error."""
    raise get_error_messages().recording_failed(reason)


def raise_timeout_exceeded(timeout: float):
    """Raise timeout exceeded error."""
    raise get_error_messages().timeout_exceeded(timeout)


def raise_audio_device_error(device_info: Optional[str] = None):
    """Raise audio device error."""
    raise get_error_messages().audio_device_error(device_info)


def raise_already_recording():
    """Raise already recording error."""
    raise get_error_messages().already_recording()


def raise_not_recording():
    """Raise not recording error."""
    raise get_error_messages().not_recording()
