"""
PTT status display rendering.

Provides formatted status output for PTT operations with support for
different display styles (compact, detailed, minimal).
"""

import time
from typing import Optional, Dict, Any
from enum import Enum

from voice_mode.ptt.terminal_utils import (
    bold, green, red, yellow, cyan, bright_green, bright_cyan,
    format_duration, format_key_hint, truncate_text, get_terminal_width,
    supports_color
)


class DisplayStyle(Enum):
    """Visual display style options."""

    MINIMAL = "minimal"      # Just status changes
    COMPACT = "compact"      # Status + key info
    DETAILED = "detailed"    # Full information including duration


class PTTStatusDisplay:
    """
    Renders PTT status information for terminal display.

    Provides formatted, colorized status messages for PTT events
    with configurable display styles.
    """

    def __init__(self, style: DisplayStyle = DisplayStyle.COMPACT):
        """
        Initialize status display.

        Args:
            style: Display style to use
        """
        self.style = style
        self._recording_start_time: Optional[float] = None

    def format_waiting(self, key_combo: str, mode: str) -> str:
        """
        Format 'waiting for key' status.

        Args:
            key_combo: Active key combination
            mode: Current PTT mode (hold/toggle/hybrid)

        Returns:
            Formatted status message
        """
        if self.style == DisplayStyle.MINIMAL:
            return f"PTT ready"

        key_hint = format_key_hint(key_combo)
        mode_display = self._format_mode(mode)

        if self.style == DisplayStyle.COMPACT:
            return f"🎙️  PTT ready  [{cyan(key_hint)}]  {mode_display}"

        # Detailed
        terminal_width = get_terminal_width()
        separator = "─" * min(40, terminal_width - 10)

        return (
            f"\n{separator}\n"
            f"🎙️  {bold('PTT Ready')}\n"
            f"   Mode: {mode_display}\n"
            f"   Press: {cyan(key_hint)} to start recording\n"
            f"{separator}"
        )

    def format_recording_start(self, key_combo: str, mode: str) -> str:
        """
        Format 'recording started' status.

        Args:
            key_combo: Active key combination
            mode: Current PTT mode

        Returns:
            Formatted status message
        """
        self._recording_start_time = time.time()

        if self.style == DisplayStyle.MINIMAL:
            return bright_green("● Recording")

        key_hint = format_key_hint(key_combo)
        mode_display = self._format_mode(mode)

        if self.style == DisplayStyle.COMPACT:
            stop_hint = self._get_stop_hint(mode, key_combo)
            return f"🔴 {bright_green(bold('RECORDING'))}  {stop_hint}  {mode_display}"

        # Detailed
        terminal_width = get_terminal_width()
        separator = "─" * min(40, terminal_width - 10)
        stop_hint = self._get_stop_hint(mode, key_combo)

        return (
            f"\n{separator}\n"
            f"🔴 {bright_green(bold('RECORDING IN PROGRESS'))}\n"
            f"   Mode: {mode_display}\n"
            f"   {stop_hint}\n"
            f"{separator}"
        )

    def format_recording_duration(self, duration: Optional[float] = None) -> str:
        """
        Format live recording duration.

        Args:
            duration: Duration in seconds (if None, calculates from start time)

        Returns:
            Formatted duration display
        """
        if duration is None:
            if self._recording_start_time is None:
                return ""
            duration = time.time() - self._recording_start_time

        duration_str = format_duration(duration)

        if self.style == DisplayStyle.MINIMAL:
            return duration_str

        if self.style == DisplayStyle.COMPACT:
            return f"⏱️  {duration_str}"

        # Detailed
        return f"⏱️  Duration: {duration_str}"

    def format_recording_stop(self, duration: float, sample_count: int) -> str:
        """
        Format 'recording stopped' status.

        Args:
            duration: Recording duration in seconds
            sample_count: Number of audio samples recorded

        Returns:
            Formatted status message
        """
        self._recording_start_time = None

        duration_str = format_duration(duration)

        if self.style == DisplayStyle.MINIMAL:
            return green(f"✓ Stopped ({duration_str})")

        if self.style == DisplayStyle.COMPACT:
            return f"⏹️  {green('Recording stopped')}  ⏱️ {duration_str}  📊 {sample_count:,} samples"

        # Detailed
        terminal_width = get_terminal_width()
        separator = "─" * min(40, terminal_width - 10)

        return (
            f"\n{separator}\n"
            f"⏹️  {green(bold('Recording Stopped'))}\n"
            f"   Duration: {duration_str}\n"
            f"   Samples: {sample_count:,}\n"
            f"{separator}"
        )

    def format_recording_cancel(self, reason: str = "user") -> str:
        """
        Format 'recording cancelled' status.

        Args:
            reason: Cancellation reason (user, timeout, error)

        Returns:
            Formatted status message
        """
        self._recording_start_time = None

        if self.style == DisplayStyle.MINIMAL:
            return red("✗ Cancelled")

        reason_text = self._format_cancel_reason(reason)

        if self.style == DisplayStyle.COMPACT:
            return f"❌ {red('Recording cancelled')}  {reason_text}"

        # Detailed
        terminal_width = get_terminal_width()
        separator = "─" * min(40, terminal_width - 10)

        return (
            f"\n{separator}\n"
            f"❌ {red(bold('Recording Cancelled'))}\n"
            f"   Reason: {reason_text}\n"
            f"{separator}"
        )

    def format_error(self, error_message: str) -> str:
        """
        Format error message.

        Args:
            error_message: Error description

        Returns:
            Formatted error message
        """
        if self.style == DisplayStyle.MINIMAL:
            return red(f"✗ {truncate_text(error_message, 40)}")

        terminal_width = get_terminal_width()
        max_msg_length = terminal_width - 10

        if self.style == DisplayStyle.COMPACT:
            return f"❌ {red('Error')}: {truncate_text(error_message, max_msg_length)}"

        # Detailed
        separator = "─" * min(40, terminal_width - 10)

        # Wrap long error messages
        wrapped_msg = self._wrap_text(error_message, max_msg_length - 6)

        return (
            f"\n{separator}\n"
            f"❌ {red(bold('Error'))}\n"
            f"   {wrapped_msg}\n"
            f"{separator}"
        )

    def format_mode_indicator(self, mode: str) -> str:
        """
        Format mode indicator.

        Args:
            mode: PTT mode (hold/toggle/hybrid)

        Returns:
            Formatted mode indicator
        """
        return self._format_mode(mode)

    def format_key_hint(self, key_combo: str, purpose: str = "record") -> str:
        """
        Format key combination hint.

        Args:
            key_combo: Key combination
            purpose: Purpose description (record, cancel, etc.)

        Returns:
            Formatted key hint
        """
        key_hint = format_key_hint(key_combo)

        if self.style == DisplayStyle.MINIMAL:
            return key_hint

        if self.style == DisplayStyle.COMPACT:
            return f"[{cyan(key_hint)}] {purpose}"

        # Detailed
        return f"Press {cyan(key_hint)} to {purpose}"

    def _format_mode(self, mode: str) -> str:
        """Format PTT mode with color coding."""
        mode_lower = mode.lower()

        if mode_lower == "hold":
            return yellow("⚡ Hold")
        elif mode_lower == "toggle":
            return cyan("🔄 Toggle")
        elif mode_lower == "hybrid":
            return bright_cyan("🔀 Hybrid")
        else:
            return f"Mode: {mode}"

    def _get_stop_hint(self, mode: str, key_combo: str) -> str:
        """Get hint for how to stop recording based on mode."""
        mode_lower = mode.lower()
        key_hint = format_key_hint(key_combo)

        if mode_lower == "hold":
            return f"Release {cyan(key_hint)} to stop"
        elif mode_lower == "toggle":
            return f"Press {cyan(key_hint)} again to stop"
        elif mode_lower == "hybrid":
            return f"Release {cyan(key_hint)} or pause to stop"
        else:
            return "Release to stop"

    def _format_cancel_reason(self, reason: str) -> str:
        """Format cancellation reason."""
        reason_lower = reason.lower()

        if reason_lower == "user":
            return yellow("User cancelled")
        elif reason_lower == "timeout":
            return yellow("Timeout")
        elif reason_lower == "error":
            return red("Error occurred")
        else:
            return reason

    def _wrap_text(self, text: str, width: int) -> str:
        """
        Wrap text to specified width.

        Args:
            text: Text to wrap
            width: Maximum width

        Returns:
            Wrapped text with indentation
        """
        if len(text) <= width:
            return text

        lines = []
        words = text.split()
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)

            if current_length + word_length + len(current_line) <= width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length

        if current_line:
            lines.append(' '.join(current_line))

        return '\n   '.join(lines)


# Global instance for easy access
_default_display: Optional[PTTStatusDisplay] = None


def get_status_display(style: Optional[DisplayStyle] = None) -> PTTStatusDisplay:
    """
    Get or create global status display instance.

    Args:
        style: Display style (if None, uses default)

    Returns:
        PTTStatusDisplay instance
    """
    global _default_display

    if _default_display is None or style is not None:
        from voice_mode import config

        # Get style from config if not provided
        if style is None:
            style_str = getattr(config, 'PTT_VISUAL_STYLE', 'compact').lower()
            try:
                style = DisplayStyle(style_str)
            except ValueError:
                style = DisplayStyle.COMPACT

        _default_display = PTTStatusDisplay(style=style)

    return _default_display


def reset_status_display():
    """Reset global status display instance."""
    global _default_display
    _default_display = None
