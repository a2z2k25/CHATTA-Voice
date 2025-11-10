"""
Keyboard event handling for Push-to-Talk functionality.

This module provides cross-platform keyboard monitoring using pynput,
managing key combination detection and event processing.
"""

import logging
import platform
from typing import Set, Optional, Callable
from pynput import keyboard
from threading import Lock

logger = logging.getLogger(__name__)


class KeyboardHandler:
    """
    Cross-platform keyboard event handler for PTT.

    Monitors keyboard input for specific key combinations and triggers
    callbacks when the PTT keys are pressed or released.

    Attributes:
        key_combo: Set of key names that must be pressed together
        pressed_keys: Set of currently pressed keys
        listener: pynput keyboard listener
        on_press_callback: Called when PTT keys are pressed
        on_release_callback: Called when PTT keys are released
    """

    def __init__(
        self,
        key_combo: str = "down+right",
        on_press_callback: Optional[Callable] = None,
        on_release_callback: Optional[Callable] = None,
        debounce_ms: int = 50
    ):
        """
        Initialize keyboard handler.

        Args:
            key_combo: Key combination string (e.g., "down+right", "ctrl+space")
            on_press_callback: Function to call when keys pressed
            on_release_callback: Function to call when keys released
            debounce_ms: Debounce time in milliseconds
        """
        self.key_combo = self._parse_key_combo(key_combo)
        self.pressed_keys: Set[str] = set()
        self.listener: Optional[keyboard.Listener] = None
        self.on_press_callback = on_press_callback
        self.on_release_callback = on_release_callback
        self.debounce_ms = debounce_ms
        self._lock = Lock()
        self._combo_active = False
        self._is_running = False

        logger.info(f"KeyboardHandler initialized for {platform.system()}")
        logger.debug(f"Monitoring key combo: {self.key_combo}")

    def _parse_key_combo(self, combo_str: str) -> Set[str]:
        """
        Parse key combination string into set of key names.

        Args:
            combo_str: String like "down+right" or "ctrl+alt+space"

        Returns:
            Set of normalized key names
        """
        keys = combo_str.lower().split("+")
        normalized = set()

        for key in keys:
            key = key.strip()
            # Normalize key names
            if key in ["ctrl", "control"]:
                normalized.add("ctrl")
            elif key in ["alt", "option"]:
                normalized.add("alt")
            elif key in ["shift"]:
                normalized.add("shift")
            elif key in ["cmd", "command", "meta", "super"]:
                normalized.add("cmd")
            else:
                normalized.add(key)

        return normalized

    def _get_key_name(self, key) -> Optional[str]:
        """
        Get normalized key name from pynput key object.

        Args:
            key: pynput Key or KeyCode object

        Returns:
            Normalized key name string or None
        """
        try:
            # Handle special keys
            if hasattr(key, 'name'):
                return key.name.lower()
            # Handle character keys
            elif hasattr(key, 'char') and key.char:
                return key.char.lower()
            # Handle other keys
            else:
                return str(key).lower()
        except Exception as e:
            logger.warning(f"Failed to get key name: {e}")
            return None

    def _on_press(self, key):
        """
        Internal handler for key press events.

        Args:
            key: pynput key object
        """
        key_name = self._get_key_name(key)
        if not key_name:
            return

        with self._lock:
            self.pressed_keys.add(key_name)

            # Check if combo is now complete
            if not self._combo_active and self.key_combo.issubset(self.pressed_keys):
                self._combo_active = True
                logger.debug(f"PTT combo activated: {self.key_combo}")

                if self.on_press_callback:
                    try:
                        self.on_press_callback()
                    except Exception as e:
                        logger.error(f"Error in on_press_callback: {e}")

    def _on_release(self, key):
        """
        Internal handler for key release events.

        Args:
            key: pynput key object
        """
        key_name = self._get_key_name(key)
        if not key_name:
            return

        with self._lock:
            self.pressed_keys.discard(key_name)

            # Check if combo is no longer active
            if self._combo_active and not self.key_combo.issubset(self.pressed_keys):
                self._combo_active = False
                logger.debug(f"PTT combo deactivated")

                if self.on_release_callback:
                    try:
                        self.on_release_callback()
                    except Exception as e:
                        logger.error(f"Error in on_release_callback: {e}")

    def start(self) -> bool:
        """
        Start listening for keyboard events.

        Returns:
            True if started successfully, False otherwise
        """
        if self._is_running:
            logger.warning("KeyboardHandler already running")
            return True

        try:
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.listener.start()
            self._is_running = True
            logger.info("Keyboard listener started")
            return True

        except Exception as e:
            logger.error(f"Failed to start keyboard listener: {e}")
            return False

    def stop(self):
        """Stop listening for keyboard events."""
        if not self._is_running:
            return

        if self.listener:
            self.listener.stop()
            self.listener = None

        self._is_running = False
        self.pressed_keys.clear()
        self._combo_active = False
        logger.info("Keyboard listener stopped")

    def is_combo_active(self) -> bool:
        """
        Check if the PTT key combination is currently active.

        Returns:
            True if all combo keys are pressed, False otherwise
        """
        with self._lock:
            return self._combo_active

    def is_running(self) -> bool:
        """
        Check if the keyboard listener is running.

        Returns:
            True if running, False otherwise
        """
        return self._is_running

    @property
    def combo_pressed(self) -> bool:
        """Alias for is_combo_active() for backward compatibility."""
        return self.is_combo_active()


def check_keyboard_permissions() -> tuple[bool, str]:
    """
    Check if we have necessary permissions for keyboard monitoring.

    Returns:
        Tuple of (has_permission, message)
    """
    system = platform.system()

    if system == "Darwin":
        # macOS - check accessibility permissions
        try:
            # Try to create a test listener
            test_listener = keyboard.Listener(on_press=lambda k: None)
            test_listener.start()
            test_listener.stop()
            return True, "Accessibility permissions granted"
        except Exception as e:
            return False, f"Accessibility permissions required: {e}"

    elif system == "Windows":
        # Windows - should work without elevation
        return True, "No special permissions required on Windows"

    elif system == "Linux":
        # Linux - check display server
        import os
        display_server = os.environ.get('XDG_SESSION_TYPE', 'x11')

        if display_server == 'wayland':
            return False, "Wayland may have limited keyboard monitoring support"

        return True, "X11 keyboard monitoring available"

    else:
        return False, f"Unsupported platform: {system}"
