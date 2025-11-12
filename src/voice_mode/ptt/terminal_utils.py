"""
Terminal utilities for PTT visual feedback.

Provides cross-platform terminal control for colors, cursor movement,
and text formatting with graceful fallback for unsupported terminals.
"""

import os
import sys
from typing import Optional
from enum import Enum


class Color(Enum):
    """ANSI color codes for terminal output."""

    # Basic colors
    BLACK = "30"
    RED = "31"
    GREEN = "32"
    YELLOW = "33"
    BLUE = "34"
    MAGENTA = "35"
    CYAN = "36"
    WHITE = "37"

    # Bright colors
    BRIGHT_BLACK = "90"
    BRIGHT_RED = "91"
    BRIGHT_GREEN = "92"
    BRIGHT_YELLOW = "93"
    BRIGHT_BLUE = "94"
    BRIGHT_MAGENTA = "95"
    BRIGHT_CYAN = "96"
    BRIGHT_WHITE = "97"

    # Reset
    RESET = "0"


class Style(Enum):
    """ANSI style codes for terminal output."""

    BOLD = "1"
    DIM = "2"
    ITALIC = "3"
    UNDERLINE = "4"
    BLINK = "5"
    REVERSE = "7"
    HIDDEN = "8"
    RESET = "0"


def supports_color() -> bool:
    """
    Check if the terminal supports ANSI color codes.

    Returns:
        True if colors are supported, False otherwise
    """
    # Check if stdout is a TTY
    if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
        return False

    # Check TERM environment variable
    term = os.getenv('TERM', '').lower()
    if term in ('dumb', ''):
        return False

    # Check for color support
    if 'color' in term or 'ansi' in term or 'xterm' in term:
        return True

    # Check COLORTERM
    if os.getenv('COLORTERM'):
        return True

    # Windows: Check for Windows Terminal or modern console
    if sys.platform == 'win32':
        # Windows 10+ with ANSI support
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Enable ANSI escape sequences
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except:
            return False

    return True


def colorize(text: str, color: Optional[Color] = None, style: Optional[Style] = None) -> str:
    """
    Colorize text with ANSI escape codes.

    Args:
        text: Text to colorize
        color: Color to apply
        style: Style to apply

    Returns:
        Colorized text if terminal supports colors, plain text otherwise
    """
    if not supports_color():
        return text

    codes = []
    if style:
        codes.append(style.value)
    if color:
        codes.append(color.value)

    if not codes:
        return text

    return f"\033[{';'.join(codes)}m{text}\033[{Color.RESET.value}m"


def bold(text: str) -> str:
    """Make text bold."""
    return colorize(text, style=Style.BOLD)


def dim(text: str) -> str:
    """Make text dim."""
    return colorize(text, style=Style.DIM)


def underline(text: str) -> str:
    """Underline text."""
    return colorize(text, style=Style.UNDERLINE)


def green(text: str) -> str:
    """Color text green."""
    return colorize(text, color=Color.GREEN)


def red(text: str) -> str:
    """Color text red."""
    return colorize(text, color=Color.RED)


def yellow(text: str) -> str:
    """Color text yellow."""
    return colorize(text, color=Color.YELLOW)


def blue(text: str) -> str:
    """Color text blue."""
    return colorize(text, color=Color.BLUE)


def cyan(text: str) -> str:
    """Color text cyan."""
    return colorize(text, color=Color.CYAN)


def magenta(text: str) -> str:
    """Color text magenta."""
    return colorize(text, color=Color.MAGENTA)


def bright_green(text: str) -> str:
    """Color text bright green."""
    return colorize(text, color=Color.BRIGHT_GREEN)


def bright_red(text: str) -> str:
    """Color text bright red."""
    return colorize(text, color=Color.BRIGHT_RED)


def bright_yellow(text: str) -> str:
    """Color text bright yellow."""
    return colorize(text, color=Color.BRIGHT_YELLOW)


def bright_cyan(text: str) -> str:
    """Color text bright cyan."""
    return colorize(text, color=Color.BRIGHT_CYAN)


def clear_line() -> str:
    """
    Get ANSI code to clear current line.

    Returns:
        ANSI escape sequence or empty string if not supported
    """
    if not supports_color():
        return ""
    return "\033[2K"


def move_cursor_up(lines: int = 1) -> str:
    """
    Get ANSI code to move cursor up.

    Args:
        lines: Number of lines to move up

    Returns:
        ANSI escape sequence or empty string if not supported
    """
    if not supports_color() or lines <= 0:
        return ""
    return f"\033[{lines}A"


def move_cursor_down(lines: int = 1) -> str:
    """
    Get ANSI code to move cursor down.

    Args:
        lines: Number of lines to move down

    Returns:
        ANSI escape sequence or empty string if not supported
    """
    if not supports_color() or lines <= 0:
        return ""
    return f"\033[{lines}B"


def move_cursor_to_column(column: int = 0) -> str:
    """
    Get ANSI code to move cursor to specific column.

    Args:
        column: Column number (0-indexed)

    Returns:
        ANSI escape sequence or empty string if not supported
    """
    if not supports_color():
        return ""
    return f"\033[{column}G"


def hide_cursor() -> str:
    """
    Get ANSI code to hide cursor.

    Returns:
        ANSI escape sequence or empty string if not supported
    """
    if not supports_color():
        return ""
    return "\033[?25l"


def show_cursor() -> str:
    """
    Get ANSI code to show cursor.

    Returns:
        ANSI escape sequence or empty string if not supported
    """
    if not supports_color():
        return ""
    return "\033[?25h"


def get_terminal_width() -> int:
    """
    Get terminal width in characters.

    Returns:
        Terminal width or 80 if cannot be determined
    """
    try:
        import shutil
        columns = shutil.get_terminal_size().columns
        return max(columns, 40)  # Minimum 40 characters
    except:
        return 80  # Default fallback


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1:23" for 1 minute 23 seconds)
    """
    if seconds < 0:
        return "0:00"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes > 0:
        return f"{minutes}:{secs:02d}"
    else:
        return f"0:{secs:02d}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    suffix_len = len(suffix)
    if max_length <= suffix_len:
        return suffix[:max_length]

    return text[:max_length - suffix_len] + suffix


def create_progress_bar(percentage: float, width: int = 20, filled_char: str = "█", empty_char: str = "░") -> str:
    """
    Create a text-based progress bar.

    Args:
        percentage: Completion percentage (0-100)
        width: Width of progress bar in characters
        filled_char: Character for filled portion
        empty_char: Character for empty portion

    Returns:
        Progress bar string
    """
    percentage = max(0, min(100, percentage))
    filled_width = int((percentage / 100) * width)
    empty_width = width - filled_width

    return f"{filled_char * filled_width}{empty_char * empty_width}"


def format_key_hint(key_combo: str) -> str:
    """
    Format key combination for display.

    Args:
        key_combo: Key combination (e.g., "ctrl+space")

    Returns:
        Formatted key hint
    """
    # Capitalize first letter of each key
    parts = key_combo.split('+')
    formatted_parts = []

    for part in parts:
        # Special formatting for certain keys
        if part.lower() == 'ctrl':
            formatted_parts.append('Ctrl')
        elif part.lower() == 'alt':
            formatted_parts.append('Alt')
        elif part.lower() == 'shift':
            formatted_parts.append('Shift')
        elif part.lower() == 'cmd':
            formatted_parts.append('Cmd')
        elif part.lower() == 'escape' or part.lower() == 'esc':
            formatted_parts.append('Esc')
        elif part.lower() == 'space':
            formatted_parts.append('Space')
        elif part.lower() == 'enter':
            formatted_parts.append('Enter')
        elif part.lower() == 'down':
            formatted_parts.append('↓')
        elif part.lower() == 'up':
            formatted_parts.append('↑')
        elif part.lower() == 'left':
            formatted_parts.append('←')
        elif part.lower() == 'right':
            formatted_parts.append('→')
        else:
            formatted_parts.append(part.capitalize())

    return '+'.join(formatted_parts)
