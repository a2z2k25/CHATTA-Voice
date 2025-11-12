"""
PTT setup wizard and helper.

Provides interactive setup and configuration assistance for first-time
PTT users.
"""

import os
import sys
from typing import Dict, Optional, List, Tuple

from voice_mode.ptt.logging import get_ptt_logger
from voice_mode.ptt.permissions import check_ptt_permissions
from voice_mode.ptt.config_validation import validate_ptt_config, get_config_from_env


class PTTSetupWizard:
    """
    PTT setup wizard.

    Guides users through PTT configuration and setup.
    """

    def __init__(self):
        """Initialize setup wizard."""
        self.logger = get_ptt_logger()

    def run_interactive_setup(self) -> Dict[str, str]:
        """
        Run interactive setup wizard.

        Returns:
            Dictionary of configuration settings
        """
        print("\n" + "=" * 60)
        print("PTT Setup Wizard")
        print("=" * 60)
        print("\nThis wizard will help you configure Push-to-Talk.\n")

        config = {}

        # Step 1: Choose mode
        print("Step 1: PTT Mode")
        print("-" * 60)
        print("Available modes:")
        print("  1. hold   - Hold key to record, release to stop")
        print("  2. toggle - Press to start, press again to stop")
        print("  3. hybrid - Hold to record, or toggle + auto-stop on silence")
        print()

        mode = self._prompt_choice(
            "Select mode (1-3)",
            choices=['1', '2', '3'],
            default='1'
        )

        mode_map = {'1': 'hold', '2': 'toggle', '3': 'hybrid'}
        config['CHATTA_PTT_MODE'] = mode_map[mode]

        # Step 2: Key combination
        print("\nStep 2: Key Combination")
        print("-" * 60)
        print("Choose the key(s) to activate PTT.")
        print("Examples:")
        print("  - down+right    (Arrow keys - recommended for macOS)")
        print("  - ctrl+space    (Modifier + key)")
        print("  - f12           (Single function key)")
        print()

        key_combo = self._prompt_text(
            "Enter key combination",
            default="down+right"
        )
        config['CHATTA_PTT_KEY_COMBO'] = key_combo

        # Step 3: Cancel key (optional)
        print("\nStep 3: Cancel Key (Optional)")
        print("-" * 60)
        print("Optional key to cancel recording immediately.")
        print("Leave empty to skip.")
        print()

        cancel_key = self._prompt_text(
            "Enter cancel key (or press Enter to skip)",
            default="",
            allow_empty=True
        )

        if cancel_key:
            config['CHATTA_PTT_CANCEL_KEY'] = cancel_key

        # Step 4: Timeout
        print("\nStep 4: Recording Timeout")
        print("-" * 60)
        print("Maximum recording duration (seconds).")
        print("Recommended: 120 seconds (2 minutes)")
        print()

        timeout = self._prompt_number(
            "Enter timeout in seconds",
            default=120.0,
            min_value=10.0,
            max_value=300.0
        )
        config['CHATTA_PTT_TIMEOUT'] = str(timeout)

        # Step 5: Visual style
        print("\nStep 5: Visual Feedback Style")
        print("-" * 60)
        print("Choose how PTT status is displayed:")
        print("  1. minimal  - Simple indicator (● Recording)")
        print("  2. compact  - Single line with details (recommended)")
        print("  3. detailed - Multi-line with full information")
        print()

        style = self._prompt_choice(
            "Select style (1-3)",
            choices=['1', '2', '3'],
            default='2'
        )

        style_map = {'1': 'minimal', '2': 'compact', '3': 'detailed'}
        config['CHATTA_PTT_VISUAL_STYLE'] = style_map[style]

        # Step 6: Audio feedback
        print("\nStep 6: Audio Feedback")
        print("-" * 60)
        print("Enable audio tones for PTT events?")
        print("(Start/stop/cancel sounds)")
        print()

        audio_enabled = self._prompt_yes_no(
            "Enable audio feedback?",
            default=True
        )
        config['CHATTA_PTT_AUDIO_FEEDBACK'] = 'true' if audio_enabled else 'false'

        if audio_enabled:
            volume = self._prompt_number(
                "Audio volume (0.0-1.0)",
                default=0.7,
                min_value=0.0,
                max_value=1.0
            )
            config['CHATTA_PTT_FEEDBACK_VOLUME'] = str(volume)

        # Complete
        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print("\nConfiguration:")
        for key, value in config.items():
            print(f"  {key}={value}")

        print("\nTo apply this configuration, add these to your environment:")
        print("  export " + " ".join(f"{k}={v}" for k, v in config.items()))

        return config

    def _prompt_text(
        self,
        prompt: str,
        default: str = "",
        allow_empty: bool = False
    ) -> str:
        """Prompt for text input."""
        while True:
            if default:
                response = input(f"{prompt} [{default}]: ").strip()
            else:
                response = input(f"{prompt}: ").strip()

            if not response and default:
                return default

            if not response and not allow_empty:
                print("  ⚠️  Value required. Please try again.")
                continue

            return response

    def _prompt_choice(
        self,
        prompt: str,
        choices: List[str],
        default: str
    ) -> str:
        """Prompt for choice from list."""
        while True:
            response = input(f"{prompt} [{default}]: ").strip()

            if not response:
                return default

            if response in choices:
                return response

            print(f"  ⚠️  Invalid choice. Options: {', '.join(choices)}")

    def _prompt_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Prompt for yes/no."""
        default_str = "Y/n" if default else "y/N"

        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()

            if not response:
                return default

            if response in ['y', 'yes']:
                return True

            if response in ['n', 'no']:
                return False

            print("  ⚠️  Please enter 'y' or 'n'")

    def _prompt_number(
        self,
        prompt: str,
        default: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> float:
        """Prompt for numeric input."""
        while True:
            response = input(f"{prompt} [{default}]: ").strip()

            if not response:
                return default

            try:
                value = float(response)

                if min_value is not None and value < min_value:
                    print(f"  ⚠️  Value must be >= {min_value}")
                    continue

                if max_value is not None and value > max_value:
                    print(f"  ⚠️  Value must be <= {max_value}")
                    continue

                return value

            except ValueError:
                print("  ⚠️  Please enter a valid number")

    def check_prerequisites(self) -> Tuple[bool, str]:
        """
        Check if prerequisites for PTT are met.

        Returns:
            Tuple of (all_met, report_message)
        """
        lines = [
            "PTT Prerequisites Check",
            "=" * 60,
            ""
        ]

        all_met = True

        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 8):
            lines.append(f"✅ Python {python_version.major}.{python_version.minor}")
        else:
            lines.append(f"❌ Python {python_version.major}.{python_version.minor} (need 3.8+)")
            all_met = False

        # Check pynput
        try:
            import pynput
            lines.append("✅ pynput library available")
        except ImportError:
            lines.append("❌ pynput library not installed")
            lines.append("   Install with: pip install pynput")
            all_met = False

        # Check sounddevice (for audio feedback)
        try:
            import sounddevice
            lines.append("✅ sounddevice library available (audio feedback)")
        except ImportError:
            lines.append("⚠️  sounddevice not installed (audio feedback unavailable)")
            lines.append("   Optional: pip install sounddevice")

        # Check numpy (for audio tones)
        try:
            import numpy
            lines.append("✅ numpy library available")
        except ImportError:
            lines.append("⚠️  numpy not installed (audio tones unavailable)")
            lines.append("   Optional: pip install numpy")

        # Check permissions
        lines.append("")
        lines.append("Permissions:")
        perm_status = check_ptt_permissions()
        lines.append(f"  Platform: {perm_status.platform}")
        lines.append(f"  Status: {'✅ OK' if perm_status.has_permission else '❌ Need permissions'}")

        if not perm_status.has_permission and perm_status.instructions:
            lines.append("")
            lines.append(perm_status.instructions)
            all_met = False

        lines.append("")
        lines.append("=" * 60)

        if all_met:
            lines.append("✅ All prerequisites met! PTT is ready to use.")
        else:
            lines.append("❌ Some prerequisites not met. See above for details.")

        return (all_met, "\n".join(lines))


def run_ptt_setup_wizard() -> Dict[str, str]:
    """
    Run interactive PTT setup wizard.

    Returns:
        Configuration dictionary
    """
    wizard = PTTSetupWizard()
    return wizard.run_interactive_setup()


def check_ptt_prerequisites() -> Tuple[bool, str]:
    """
    Check PTT prerequisites.

    Returns:
        Tuple of (all_met, report)
    """
    wizard = PTTSetupWizard()
    return wizard.check_prerequisites()


def diagnose_ptt_setup() -> str:
    """
    Run comprehensive PTT setup diagnostics.

    Returns:
        Diagnostic report string
    """
    lines = [
        "PTT Setup Diagnostics",
        "=" * 70,
        ""
    ]

    # Prerequisites check
    wizard = PTTSetupWizard()
    prereq_ok, prereq_report = wizard.check_prerequisites()
    lines.append(prereq_report)
    lines.append("")

    # Configuration validation
    lines.append("Configuration Validation")
    lines.append("=" * 70)
    lines.append("")

    config = get_config_from_env()
    is_valid, issues = validate_ptt_config(config)

    if is_valid:
        lines.append("✅ Configuration is valid")
    else:
        lines.append("❌ Configuration has issues:")
        lines.append("")

        from voice_mode.ptt.config_validation import PTTConfigValidator
        validator = PTTConfigValidator()
        validator.issues = issues
        lines.append(validator.format_issues())

    lines.append("")
    lines.append("=" * 70)

    # Overall status
    if prereq_ok and is_valid:
        lines.append("✅ PTT is ready to use!")
    else:
        lines.append("❌ PTT setup incomplete. See issues above.")

    return "\n".join(lines)


def print_quick_start_guide():
    """Print PTT quick start guide."""
    guide = """
PTT Quick Start Guide
=====================

1. Basic Usage
   - Enable PTT with your configured key combination
   - Hold (or press) key to record
   - Release (or press again) to stop and transcribe

2. Configuration
   - Set environment variables (CHATTA_PTT_*)
   - Or use setup wizard: python -m voice_mode.ptt.setup_helper

3. Key Settings
   - CHATTA_PTT_MODE: hold, toggle, or hybrid
   - CHATTA_PTT_KEY_COMBO: your key combination (e.g., "down+right")
   - CHATTA_PTT_TIMEOUT: max recording seconds

4. Common Issues
   - macOS: Grant accessibility permissions to terminal
   - Linux Wayland: Some compositors may restrict keyboard access
   - Windows: Should work without special permissions

5. Getting Help
   - Run diagnostics: python -m voice_mode.ptt.setup_helper --diagnose
   - Check prerequisites: python -m voice_mode.ptt.setup_helper --check
   - Interactive setup: python -m voice_mode.ptt.setup_helper --setup

For more information, see the PTT documentation.
"""
    print(guide)


if __name__ == '__main__':
    # CLI interface
    import argparse

    parser = argparse.ArgumentParser(description='PTT Setup Helper')
    parser.add_argument('--setup', action='store_true', help='Run interactive setup wizard')
    parser.add_argument('--check', action='store_true', help='Check prerequisites')
    parser.add_argument('--diagnose', action='store_true', help='Run diagnostics')
    parser.add_argument('--guide', action='store_true', help='Show quick start guide')

    args = parser.parse_args()

    if args.setup:
        run_ptt_setup_wizard()
    elif args.check:
        all_met, report = check_ptt_prerequisites()
        print(report)
        sys.exit(0 if all_met else 1)
    elif args.diagnose:
        print(diagnose_ptt_setup())
    elif args.guide:
        print_quick_start_guide()
    else:
        # Default: run setup wizard
        run_ptt_setup_wizard()
