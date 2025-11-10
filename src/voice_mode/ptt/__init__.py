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

# Public API (will be populated as we implement components)
__all__ = []
