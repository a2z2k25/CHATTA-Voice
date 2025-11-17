"""
PTT configuration validation and verification.

Validates PTT configuration settings to ensure they are correct and usable.
Provides helpful error messages and suggestions for fixing configuration issues.
"""

import os
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from voice_mode.ptt.logging import get_ptt_logger


class ValidationLevel(Enum):
    """Validation issue severity levels."""

    ERROR = "error"      # Configuration will not work
    WARNING = "warning"  # Configuration may cause issues
    INFO = "info"        # Informational message


@dataclass
class ValidationIssue:
    """A configuration validation issue."""

    level: ValidationLevel
    setting: str
    message: str
    suggestion: Optional[str] = None
    current_value: Optional[Any] = None


class PTTConfigValidator:
    """
    PTT configuration validator.

    Validates all PTT configuration settings and provides helpful
    error messages and suggestions for fixing issues.
    """

    # Valid PTT modes
    VALID_MODES = {'hold', 'toggle', 'hybrid'}

    # Valid display styles
    VALID_DISPLAY_STYLES = {'minimal', 'compact', 'detailed'}

    # Valid key names (common subset)
    VALID_KEYS = {
        # Modifiers
        'ctrl', 'control', 'alt', 'option', 'shift', 'cmd', 'command', 'super', 'win', 'windows',
        # Arrow keys
        'up', 'down', 'left', 'right',
        # Function keys
        'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
        # Special keys
        'space', 'spacebar', 'enter', 'return', 'tab', 'esc', 'escape',
        'backspace', 'delete', 'home', 'end', 'pageup', 'pagedown',
        # Letters
        *[chr(i) for i in range(ord('a'), ord('z') + 1)],
        # Numbers
        *[str(i) for i in range(10)],
    }

    def __init__(self):
        """Initialize validator."""
        self.logger = get_ptt_logger()
        self.issues: List[ValidationIssue] = []

    def validate_all(self, config: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate all PTT configuration settings.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, issues_list)
        """
        self.issues = []

        # Validate each configuration setting
        self._validate_mode(config.get('PTT_MODE'))
        self._validate_key_combo(config.get('PTT_KEY_COMBO'))
        self._validate_cancel_key(config.get('PTT_CANCEL_KEY'))
        self._validate_timeout(config.get('PTT_TIMEOUT'))
        self._validate_min_duration(config.get('PTT_MIN_DURATION'))
        self._validate_display_style(config.get('PTT_VISUAL_STYLE'))
        self._validate_volume(config.get('PTT_FEEDBACK_VOLUME'))
        self._validate_boolean(config.get('PTT_ENABLED'), 'PTT_ENABLED')
        self._validate_boolean(config.get('PTT_VISUAL_FEEDBACK'), 'PTT_VISUAL_FEEDBACK')
        self._validate_boolean(config.get('PTT_AUDIO_FEEDBACK'), 'PTT_AUDIO_FEEDBACK')
        self._validate_boolean(config.get('PTT_STATISTICS'), 'PTT_STATISTICS')

        # Check for errors
        has_errors = any(issue.level == ValidationLevel.ERROR for issue in self.issues)

        return (not has_errors, self.issues)

    def _validate_mode(self, mode: Optional[str]):
        """Validate PTT mode setting."""
        if mode is None:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_MODE',
                message='PTT mode is not set',
                suggestion='Set CHATTA_PTT_MODE to one of: hold, toggle, hybrid',
                current_value=None
            ))
            return

        if mode.lower() not in self.VALID_MODES:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_MODE',
                message=f'Invalid PTT mode: {mode}',
                suggestion=f'Valid modes are: {", ".join(sorted(self.VALID_MODES))}',
                current_value=mode
            ))

    def _validate_key_combo(self, key_combo: Optional[str]):
        """Validate key combination setting."""
        if key_combo is None:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_KEY_COMBO',
                message='PTT key combination is not set',
                suggestion='Set CHATTA_PTT_KEY_COMBO (e.g., "option_r", "ctrl+space")',
                current_value=None
            ))
            return

        # Parse key combination
        keys = [k.strip().lower() for k in key_combo.split('+')]

        if not keys or len(keys) == 0:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_KEY_COMBO',
                message='PTT key combination is empty',
                suggestion='Specify keys separated by + (e.g., "down+right")',
                current_value=key_combo
            ))
            return

        # Validate individual keys
        invalid_keys = [k for k in keys if k not in self.VALID_KEYS]

        if invalid_keys:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                setting='PTT_KEY_COMBO',
                message=f'Unrecognized keys in combination: {", ".join(invalid_keys)}',
                suggestion='Keys may not be supported on all platforms. Test carefully.',
                current_value=key_combo
            ))

        # Warn about modifier-only combinations
        modifiers = {'ctrl', 'control', 'alt', 'option', 'shift', 'cmd', 'command', 'super', 'win', 'windows'}
        if all(k in modifiers for k in keys):
            self.issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                setting='PTT_KEY_COMBO',
                message='Key combination contains only modifiers',
                suggestion='Consider adding a non-modifier key (e.g., "ctrl+space")',
                current_value=key_combo
            ))

    def _validate_cancel_key(self, cancel_key: Optional[str]):
        """Validate cancel key setting."""
        if cancel_key is None or cancel_key == '':
            # Cancel key is optional
            return

        # Validate cancel key
        key = cancel_key.strip().lower()

        if key not in self.VALID_KEYS:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                setting='PTT_CANCEL_KEY',
                message=f'Unrecognized cancel key: {cancel_key}',
                suggestion='Key may not be supported on all platforms',
                current_value=cancel_key
            ))

    def _validate_timeout(self, timeout: Optional[float]):
        """Validate timeout setting."""
        if timeout is None:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_TIMEOUT',
                message='PTT timeout is not set',
                suggestion='Set CHATTA_PTT_TIMEOUT to a positive number (seconds)',
                current_value=None
            ))
            return

        if not isinstance(timeout, (int, float)):
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_TIMEOUT',
                message=f'PTT timeout must be a number, got: {type(timeout).__name__}',
                suggestion='Set CHATTA_PTT_TIMEOUT to a positive number (e.g., 120)',
                current_value=timeout
            ))
            return

        if timeout <= 0:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_TIMEOUT',
                message=f'PTT timeout must be positive, got: {timeout}',
                suggestion='Set CHATTA_PTT_TIMEOUT to a positive number (e.g., 120)',
                current_value=timeout
            ))
        elif timeout < 10:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                setting='PTT_TIMEOUT',
                message=f'PTT timeout is very short: {timeout}s',
                suggestion='Consider increasing timeout for longer recordings (60-120s)',
                current_value=timeout
            ))
        elif timeout > 300:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                setting='PTT_TIMEOUT',
                message=f'PTT timeout is very long: {timeout}s',
                suggestion='Long timeouts may tie up resources. Consider 60-180s.',
                current_value=timeout
            ))

    def _validate_min_duration(self, min_duration: Optional[float]):
        """Validate minimum duration setting."""
        if min_duration is None:
            return  # Optional setting

        if not isinstance(min_duration, (int, float)):
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_MIN_DURATION',
                message=f'PTT min duration must be a number, got: {type(min_duration).__name__}',
                suggestion='Set CHATTA_PTT_MIN_DURATION to a positive number (e.g., 0.5)',
                current_value=min_duration
            ))
            return

        if min_duration < 0:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_MIN_DURATION',
                message=f'PTT min duration must be non-negative, got: {min_duration}',
                suggestion='Set CHATTA_PTT_MIN_DURATION to 0 or positive value',
                current_value=min_duration
            ))
        elif min_duration > 5:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                setting='PTT_MIN_DURATION',
                message=f'PTT min duration is very long: {min_duration}s',
                suggestion='Long minimum durations may discard short recordings. Consider 0.3-1.0s.',
                current_value=min_duration
            ))

    def _validate_silence_duration(self, silence_duration: Optional[float]):
        """Validate silence duration setting."""
        if silence_duration is None:
            return  # Optional setting

        if not isinstance(silence_duration, (int, float)):
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_SILENCE_DURATION',
                message=f'PTT silence duration must be a number, got: {type(silence_duration).__name__}',
                suggestion='Set CHATTA_PTT_SILENCE_DURATION to a positive number (e.g., 1.5)',
                current_value=silence_duration
            ))
            return

        if silence_duration <= 0:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_SILENCE_DURATION',
                message=f'PTT silence duration must be positive, got: {silence_duration}',
                suggestion='Set CHATTA_PTT_SILENCE_DURATION to a positive number (1.0-3.0s)',
                current_value=silence_duration
            ))
        elif silence_duration < 0.5:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                setting='PTT_SILENCE_DURATION',
                message=f'PTT silence duration is very short: {silence_duration}s',
                suggestion='May stop recording too early. Consider 1.0-2.0s.',
                current_value=silence_duration
            ))

    def _validate_display_style(self, style: Optional[str]):
        """Validate display style setting."""
        if style is None:
            return  # Optional setting

        if style.lower() not in self.VALID_DISPLAY_STYLES:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                setting='PTT_VISUAL_STYLE',
                message=f'Invalid display style: {style}',
                suggestion=f'Valid styles are: {", ".join(sorted(self.VALID_DISPLAY_STYLES))}. Will use default.',
                current_value=style
            ))

    def _validate_volume(self, volume: Optional[float]):
        """Validate volume setting."""
        if volume is None:
            return  # Optional setting

        if not isinstance(volume, (int, float)):
            self.issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                setting='PTT_FEEDBACK_VOLUME',
                message=f'PTT feedback volume must be a number, got: {type(volume).__name__}',
                suggestion='Set CHATTA_PTT_FEEDBACK_VOLUME to a number between 0.0 and 1.0',
                current_value=volume
            ))
            return

        if volume < 0 or volume > 1:
            self.issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                setting='PTT_FEEDBACK_VOLUME',
                message=f'PTT feedback volume should be 0.0-1.0, got: {volume}',
                suggestion='Volume will be clamped to valid range. Set to 0.0-1.0.',
                current_value=volume
            ))

    def _validate_boolean(self, value: Optional[bool], setting_name: str):
        """Validate boolean setting."""
        if value is None:
            return  # Optional setting

        if not isinstance(value, bool):
            self.issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                setting=setting_name,
                message=f'{setting_name} should be true/false, got: {value}',
                suggestion=f'Set CHATTA_{setting_name} to true or false',
                current_value=value
            ))

    def format_issues(self, issues: Optional[List[ValidationIssue]] = None) -> str:
        """
        Format validation issues as human-readable string.

        Args:
            issues: Issues to format (uses self.issues if None)

        Returns:
            Formatted string
        """
        if issues is None:
            issues = self.issues

        if not issues:
            return "✅ Configuration is valid"

        lines = ["PTT Configuration Validation Results", "=" * 50, ""]

        # Group by level
        errors = [i for i in issues if i.level == ValidationLevel.ERROR]
        warnings = [i for i in issues if i.level == ValidationLevel.WARNING]
        info = [i for i in issues if i.level == ValidationLevel.INFO]

        if errors:
            lines.append(f"❌ ERRORS ({len(errors)}):")
            for issue in errors:
                lines.append(f"\n  Setting: {issue.setting}")
                lines.append(f"  Problem: {issue.message}")
                if issue.current_value is not None:
                    lines.append(f"  Current: {issue.current_value}")
                if issue.suggestion:
                    lines.append(f"  Fix: {issue.suggestion}")
            lines.append("")

        if warnings:
            lines.append(f"⚠️  WARNINGS ({len(warnings)}):")
            for issue in warnings:
                lines.append(f"\n  Setting: {issue.setting}")
                lines.append(f"  Issue: {issue.message}")
                if issue.current_value is not None:
                    lines.append(f"  Current: {issue.current_value}")
                if issue.suggestion:
                    lines.append(f"  Suggestion: {issue.suggestion}")
            lines.append("")

        if info:
            lines.append(f"ℹ️  INFO ({len(info)}):")
            for issue in info:
                lines.append(f"\n  Setting: {issue.setting}")
                lines.append(f"  Note: {issue.message}")
                if issue.suggestion:
                    lines.append(f"  {issue.suggestion}")
            lines.append("")

        return "\n".join(lines)


def validate_ptt_config(config: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
    """
    Validate PTT configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (is_valid, issues_list)
    """
    validator = PTTConfigValidator()
    return validator.validate_all(config)


def get_config_from_env() -> Dict[str, Any]:
    """
    Get PTT configuration from environment variables.

    Returns:
        Configuration dictionary
    """
    from voice_mode.config import (
        PTT_MODE, PTT_KEY_COMBO, PTT_CANCEL_KEY, PTT_TIMEOUT,
        PTT_MIN_DURATION, PTT_VISUAL_STYLE,
        PTT_FEEDBACK_VOLUME, PTT_ENABLED, PTT_VISUAL_FEEDBACK,
        PTT_AUDIO_FEEDBACK, PTT_STATISTICS
    )

    return {
        'PTT_MODE': PTT_MODE,
        'PTT_KEY_COMBO': PTT_KEY_COMBO,
        'PTT_CANCEL_KEY': PTT_CANCEL_KEY,
        'PTT_TIMEOUT': PTT_TIMEOUT,
        'PTT_MIN_DURATION': PTT_MIN_DURATION,
        'PTT_VISUAL_STYLE': PTT_VISUAL_STYLE,
        'PTT_FEEDBACK_VOLUME': PTT_FEEDBACK_VOLUME,
        'PTT_ENABLED': PTT_ENABLED,
        'PTT_VISUAL_FEEDBACK': PTT_VISUAL_FEEDBACK,
        'PTT_AUDIO_FEEDBACK': PTT_AUDIO_FEEDBACK,
        'PTT_STATISTICS': PTT_STATISTICS,
    }


def validate_current_config() -> Tuple[bool, str]:
    """
    Validate current PTT configuration from environment.

    Returns:
        Tuple of (is_valid, formatted_report)
    """
    config = get_config_from_env()
    validator = PTTConfigValidator()
    is_valid, issues = validator.validate_all(config)
    report = validator.format_issues(issues)

    return (is_valid, report)
