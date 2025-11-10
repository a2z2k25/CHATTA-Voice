"""
Unit tests for PTT keyboard handler.
"""

import pytest
from unittest.mock import Mock, patch
from voice_mode.ptt.keyboard import KeyboardHandler, check_keyboard_permissions


class TestKeyboardHandler:
    """Test keyboard event handling"""

    def test_initialization(self):
        """Test KeyboardHandler initialization"""
        handler = KeyboardHandler(key_combo="down+right")

        assert handler.key_combo == {"down", "right"}
        assert not handler.is_running()
        assert not handler.is_combo_active()
        assert len(handler.pressed_keys) == 0

    def test_key_combo_parsing(self):
        """Test parsing of various key combinations"""
        # Simple combo
        handler1 = KeyboardHandler("down+right")
        assert handler1.key_combo == {"down", "right"}

        # With modifiers
        handler2 = KeyboardHandler("ctrl+alt+space")
        assert handler2.key_combo == {"ctrl", "alt", "space"}

        # Single key
        handler3 = KeyboardHandler("f13")
        assert handler3.key_combo == {"f13"}

        # Normalize ctrl variants
        handler4 = KeyboardHandler("control+space")
        assert "ctrl" in handler4.key_combo

    def test_callback_registration(self):
        """Test callback functions are stored"""
        press_callback = Mock()
        release_callback = Mock()

        handler = KeyboardHandler(
            key_combo="space",
            on_press_callback=press_callback,
            on_release_callback=release_callback
        )

        assert handler.on_press_callback == press_callback
        assert handler.on_release_callback == release_callback

    @patch('voice_mode.ptt.keyboard.keyboard.Listener')
    def test_start_listener(self, mock_listener_class):
        """Test starting the keyboard listener"""
        mock_listener = Mock()
        mock_listener_class.return_value = mock_listener

        handler = KeyboardHandler()
        result = handler.start()

        assert result is True
        assert handler.is_running()
        mock_listener.start.assert_called_once()

    @patch('voice_mode.ptt.keyboard.keyboard.Listener')
    def test_stop_listener(self, mock_listener_class):
        """Test stopping the keyboard listener"""
        mock_listener = Mock()
        mock_listener_class.return_value = mock_listener

        handler = KeyboardHandler()
        handler.start()
        handler.stop()

        assert not handler.is_running()
        mock_listener.stop.assert_called_once()

    def test_key_name_normalization(self):
        """Test key name normalization"""
        handler = KeyboardHandler()

        # Test special keys
        mock_key_down = Mock()
        mock_key_down.name = "down"
        assert handler._get_key_name(mock_key_down) == "down"

        # Test character keys
        mock_key_char = Mock()
        mock_key_char.char = "a"
        del mock_key_char.name  # Character keys don't have .name
        assert handler._get_key_name(mock_key_char) == "a"


class TestPermissionCheck:
    """Test keyboard permission checking"""

    def test_check_keyboard_permissions(self):
        """Test permission checking returns valid tuple"""
        has_permission, message = check_keyboard_permissions()

        assert isinstance(has_permission, bool)
        assert isinstance(message, str)
        assert len(message) > 0

    @patch('voice_mode.ptt.keyboard.platform.system')
    def test_windows_permissions(self, mock_system):
        """Test Windows permission check"""
        mock_system.return_value = "Windows"

        has_permission, message = check_keyboard_permissions()

        assert has_permission is True
        assert "No special permissions" in message

    @patch('voice_mode.ptt.keyboard.platform.system')
    @patch('voice_mode.ptt.keyboard.keyboard.Listener')
    def test_macos_permissions_granted(self, mock_listener_class, mock_system):
        """Test macOS permission check when granted"""
        mock_system.return_value = "Darwin"
        mock_listener = Mock()
        mock_listener_class.return_value = mock_listener

        has_permission, message = check_keyboard_permissions()

        # Should attempt to create test listener
        mock_listener.start.assert_called()
        mock_listener.stop.assert_called()

    @patch('voice_mode.ptt.keyboard.platform.system')
    def test_unsupported_platform(self, mock_system):
        """Test unsupported platform handling"""
        mock_system.return_value = "FreeBSD"

        has_permission, message = check_keyboard_permissions()

        assert has_permission is False
        assert "Unsupported platform" in message
