"""
PTT permissions checker for keyboard access.

Checks and provides guidance for platform-specific permissions required
for PTT keyboard monitoring (especially macOS accessibility permissions).
"""

import sys
import os
import subprocess
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from voice_mode.ptt.logging import get_ptt_logger


@dataclass
class PermissionStatus:
    """Permission check result."""

    has_permission: bool
    platform: str
    message: str
    instructions: Optional[str] = None
    can_request: bool = False


class PTTPermissionsChecker:
    """
    PTT permissions checker.

    Checks platform-specific permissions required for keyboard monitoring.
    """

    def __init__(self):
        """Initialize permissions checker."""
        self.logger = get_ptt_logger()
        self.platform = sys.platform

    def check_keyboard_permissions(self) -> PermissionStatus:
        """
        Check if application has keyboard monitoring permissions.

        Returns:
            PermissionStatus with results
        """
        if self.platform == 'darwin':
            return self._check_macos_permissions()
        elif self.platform == 'linux':
            return self._check_linux_permissions()
        elif self.platform == 'win32':
            return self._check_windows_permissions()
        else:
            return PermissionStatus(
                has_permission=True,  # Assume yes for unknown platforms
                platform=self.platform,
                message=f"Unknown platform: {self.platform}. Cannot verify permissions.",
                instructions=None,
                can_request=False
            )

    def _check_macos_permissions(self) -> PermissionStatus:
        """Check macOS accessibility permissions."""
        try:
            # Try to detect if we have accessibility permissions
            # This is a heuristic - we can't directly query permission status from Python

            # Check if running in Terminal/iTerm that has permissions
            term_program = os.getenv('TERM_PROGRAM', '')

            # Common scenarios where permissions are likely granted
            if term_program in ['Apple_Terminal', 'iTerm.app', 'vscode']:
                return PermissionStatus(
                    has_permission=True,
                    platform='macOS',
                    message="Terminal appears to have accessibility permissions.",
                    instructions=None,
                    can_request=False
                )

            # If we can't determine, provide instructions
            instructions = """
macOS Accessibility Permissions Required
==========================================

PTT requires keyboard monitoring permissions on macOS.

To grant permissions:
1. Open System Settings (or System Preferences)
2. Go to Privacy & Security → Accessibility
3. Find your terminal application (Terminal.app, iTerm, VS Code, etc.)
4. Enable the checkbox next to it
5. Restart your terminal application

Common terminal applications:
- Terminal.app (macOS default)
- iTerm2
- VS Code integrated terminal
- Alacritty
- Kitty

After granting permissions, restart your terminal and try again.
"""

            return PermissionStatus(
                has_permission=False,
                platform='macOS',
                message="Cannot verify accessibility permissions. PTT may not work without them.",
                instructions=instructions.strip(),
                can_request=False
            )

        except Exception as e:
            self.logger.log_error(e, {'context': 'macos_permission_check'})

            return PermissionStatus(
                has_permission=False,
                platform='macOS',
                message=f"Error checking permissions: {e}",
                instructions="Please ensure your terminal has accessibility permissions.",
                can_request=False
            )

    def _check_linux_permissions(self) -> PermissionStatus:
        """Check Linux permissions."""
        try:
            # On Linux, keyboard monitoring typically requires:
            # - X11: XTEST extension (usually available)
            # - Wayland: May have restrictions

            # Check if running on Wayland
            session_type = os.getenv('XDG_SESSION_TYPE', '').lower()

            if session_type == 'wayland':
                instructions = """
Wayland Session Detected
========================

PTT keyboard monitoring on Wayland may have limitations.

Recommendations:
1. If PTT doesn't work, try running under X11 instead
2. Some Wayland compositors restrict keyboard monitoring for security
3. Check your compositor's documentation for keyboard grab policies

To use X11 instead (if available):
- Log out and select "GNOME on Xorg" or similar at login screen
- Or set environment: export GDK_BACKEND=x11

Tested compositors:
- GNOME/Mutter: Generally works with proper focus
- KDE/KWin: Generally works
- Sway: May require additional configuration
"""

                return PermissionStatus(
                    has_permission=True,  # Allow attempt
                    platform='Linux (Wayland)',
                    message="Running on Wayland. PTT may have limitations.",
                    instructions=instructions.strip(),
                    can_request=False
                )

            # X11 - typically works
            return PermissionStatus(
                has_permission=True,
                platform='Linux (X11)',
                message="Running on X11. Keyboard monitoring should work.",
                instructions=None,
                can_request=False
            )

        except Exception as e:
            self.logger.log_error(e, {'context': 'linux_permission_check'})

            return PermissionStatus(
                has_permission=True,  # Assume yes, let it try
                platform='Linux',
                message="Linux detected. Keyboard monitoring should work.",
                instructions=None,
                can_request=False
            )

    def _check_windows_permissions(self) -> PermissionStatus:
        """Check Windows permissions."""
        try:
            # On Windows, keyboard hooks generally work without special permissions
            # unless running in a restricted environment

            # Check if running as admin (not required, but good to know)
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

            if is_admin:
                message = "Running as Administrator. PTT should work."
            else:
                message = "Running as regular user. PTT should work."

            return PermissionStatus(
                has_permission=True,
                platform='Windows',
                message=message,
                instructions=None,
                can_request=False
            )

        except Exception as e:
            self.logger.log_error(e, {'context': 'windows_permission_check'})

            return PermissionStatus(
                has_permission=True,  # Assume yes
                platform='Windows',
                message="Windows detected. PTT should work.",
                instructions=None,
                can_request=False
            )

    def get_permission_instructions(self) -> str:
        """
        Get platform-specific permission instructions.

        Returns:
            Formatted instructions string
        """
        status = self.check_keyboard_permissions()

        if status.has_permission and not status.instructions:
            return f"✅ {status.message}"

        lines = [
            "PTT Keyboard Permissions Check",
            "=" * 50,
            "",
            f"Platform: {status.platform}",
            f"Status: {'✅ Granted' if status.has_permission else '❌ Not Verified'}",
            "",
            status.message,
        ]

        if status.instructions:
            lines.extend(["", status.instructions])

        return "\n".join(lines)


def check_ptt_permissions() -> PermissionStatus:
    """
    Check PTT permissions for current platform.

    Returns:
        PermissionStatus
    """
    checker = PTTPermissionsChecker()
    return checker.check_keyboard_permissions()


def print_permission_instructions():
    """Print permission instructions for current platform."""
    checker = PTTPermissionsChecker()
    print(checker.get_permission_instructions())


def verify_ptt_can_run() -> Tuple[bool, str]:
    """
    Verify PTT can run on current platform.

    Returns:
        Tuple of (can_run, message)
    """
    # Check permissions
    status = check_ptt_permissions()

    # Check pynput availability
    try:
        from pynput import keyboard
        pynput_available = True
    except ImportError:
        pynput_available = False

    if not pynput_available:
        return (False, "pynput library not available. Install with: pip install pynput")

    if not status.has_permission:
        message = f"{status.message}\n\n"
        if status.instructions:
            message += status.instructions
        return (False, message)

    return (True, "PTT can run on this platform")
