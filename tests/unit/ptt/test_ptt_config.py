"""
Unit tests for PTT configuration.
"""

import pytest
import os
from importlib import reload


class TestPTTConfiguration:
    """Test PTT configuration loading"""

    def test_default_ptt_config(self, monkeypatch):
        """Test default PTT configuration values"""
        # Clear any existing PTT environment variables
        for key in list(os.environ.keys()):
            if key.startswith("CHATTA_PTT_"):
                monkeypatch.delenv(key, raising=False)

        # Reload config module to pick up changes
        import voice_mode.config as config
        reload(config)

        # Test defaults
        assert config.PTT_ENABLED is False
        assert config.PTT_KEY_COMBO == "down+right"
        assert config.PTT_MODE == "hold"
        assert config.PTT_TIMEOUT == 120.0
        assert config.PTT_AUDIO_FEEDBACK is True
        assert config.PTT_VISUAL_FEEDBACK is True

    def test_ptt_env_override(self, monkeypatch):
        """Test PTT configuration from environment variables"""
        # Set environment variables
        monkeypatch.setenv("CHATTA_PTT_ENABLED", "true")
        monkeypatch.setenv("CHATTA_PTT_KEY_COMBO", "ctrl+space")
        monkeypatch.setenv("CHATTA_PTT_MODE", "toggle")
        monkeypatch.setenv("CHATTA_PTT_TIMEOUT", "60.0")

        # Reload config module
        import voice_mode.config as config
        reload(config)

        # Test overrides
        assert config.PTT_ENABLED is True
        assert config.PTT_KEY_COMBO == "ctrl+space"
        assert config.PTT_MODE == "toggle"
        assert config.PTT_TIMEOUT == 60.0

    def test_ptt_boolean_parsing(self, monkeypatch):
        """Test boolean environment variable parsing"""
        # Test various true values
        for true_val in ["true", "1", "yes", "on"]:
            monkeypatch.setenv("CHATTA_PTT_ENABLED", true_val)
            import voice_mode.config as config
            reload(config)
            assert config.PTT_ENABLED is True, f"Failed for value: {true_val}"

        # Test false values
        for false_val in ["false", "0", "no", "off", ""]:
            monkeypatch.setenv("CHATTA_PTT_ENABLED", false_val)
            reload(config)
            assert config.PTT_ENABLED is False, f"Failed for value: {false_val}"

    def test_ptt_numeric_config(self, monkeypatch):
        """Test numeric configuration values"""
        monkeypatch.setenv("CHATTA_PTT_TIMEOUT", "30.5")
        monkeypatch.setenv("CHATTA_PTT_RELEASE_DELAY", "0.2")
        monkeypatch.setenv("CHATTA_PTT_MIN_DURATION", "1.0")
        monkeypatch.setenv("CHATTA_PTT_FEEDBACK_VOLUME", "0.5")

        import voice_mode.config as config
        reload(config)

        assert config.PTT_TIMEOUT == 30.5
        assert config.PTT_RELEASE_DELAY == 0.2
        assert config.PTT_MIN_DURATION == 1.0
        assert config.PTT_FEEDBACK_VOLUME == 0.5

    def test_ptt_platform_settings(self, monkeypatch):
        """Test platform-specific settings"""
        monkeypatch.setenv("CHATTA_PTT_MACOS_ACCESSIBILITY_CHECK", "false")
        monkeypatch.setenv("CHATTA_PTT_WINDOWS_HOOK_TYPE", "high_level")
        monkeypatch.setenv("CHATTA_PTT_LINUX_INPUT_METHOD", "x11")

        import voice_mode.config as config
        reload(config)

        assert config.PTT_MACOS_ACCESSIBILITY_CHECK is False
        assert config.PTT_WINDOWS_HOOK_TYPE == "high_level"
        assert config.PTT_LINUX_INPUT_METHOD == "x11"

    def test_ptt_debug_settings(self, monkeypatch):
        """Test debug-related settings"""
        monkeypatch.setenv("CHATTA_PTT_DEBUG", "true")
        monkeypatch.setenv("CHATTA_PTT_LOG_KEYS", "true")
        monkeypatch.setenv("CHATTA_PTT_SIMULATE", "true")

        import voice_mode.config as config
        reload(config)

        assert config.PTT_DEBUG is True
        assert config.PTT_LOG_KEYS is True
        assert config.PTT_SIMULATE is True

    def test_ptt_cancel_key_config(self, monkeypatch):
        """Test cancel key configuration"""
        monkeypatch.setenv("CHATTA_PTT_CANCEL_KEY", "f12")

        import voice_mode.config as config
        reload(config)

        assert config.PTT_CANCEL_KEY == "f12"
