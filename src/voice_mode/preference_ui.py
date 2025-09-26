"""
Preference UI components for voice mode configuration.

This module provides UI components for preference management including:
- Configuration panels and forms
- Setting editors and validators
- Profile management interface
- Import/export dialogs
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import logging

from .user_preferences import (
    UserPreferencesManager,
    UserPreferences,
    PreferenceCategory,
    AudioFormat,
    VoiceProvider,
    PreferenceValidator
)

logger = logging.getLogger(__name__)


class UIComponent:
    """Base class for preference UI components."""
    
    def __init__(self, id: str, label: str):
        """Initialize UI component.
        
        Args:
            id: Component identifier
            label: Display label
        """
        self.id = id
        self.label = label
        self.visible = True
        self.enabled = True
        self.change_callbacks: List[Callable] = []
    
    def on_change(self, callback: Callable):
        """Register change callback.
        
        Args:
            callback: Function to call on value change
        """
        self.change_callbacks.append(callback)
    
    def notify_change(self, old_value: Any, new_value: Any):
        """Notify registered callbacks of value change.
        
        Args:
            old_value: Previous value
            new_value: New value
        """
        for callback in self.change_callbacks:
            try:
                callback(self.id, old_value, new_value)
            except Exception as e:
                logger.error(f"UI change callback error: {e}")


@dataclass
class ValidationResult:
    """Result of form validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]


class SliderComponent(UIComponent):
    """Slider input component."""
    
    def __init__(self, id: str, label: str, min_val: float, max_val: float, 
                 step: float = 0.1, value: float = None):
        """Initialize slider.
        
        Args:
            id: Component ID
            label: Display label
            min_val: Minimum value
            max_val: Maximum value
            step: Step size
            value: Initial value
        """
        super().__init__(id, label)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.value = value if value is not None else min_val
    
    def set_value(self, value: float):
        """Set slider value.
        
        Args:
            value: New value
        """
        old_value = self.value
        self.value = max(self.min_val, min(self.max_val, value))
        self.notify_change(old_value, self.value)
    
    def get_display_text(self) -> str:
        """Get formatted display text.
        
        Returns:
            Formatted value text
        """
        if self.id.endswith("volume") or self.id.endswith("gain"):
            return f"{self.value:.1f}"
        elif self.id.endswith("speed") or self.id.endswith("rate"):
            return f"{self.value:.2f}x"
        elif self.id.endswith("threshold"):
            return f"{self.value:.1f} dB"
        else:
            return f"{self.value:.2f}"


class SelectComponent(UIComponent):
    """Select/dropdown component."""
    
    def __init__(self, id: str, label: str, options: List[tuple], value: str = None):
        """Initialize select component.
        
        Args:
            id: Component ID
            label: Display label
            options: List of (value, display_name) tuples
            value: Initial value
        """
        super().__init__(id, label)
        self.options = options
        self.value = value or (options[0][0] if options else None)
    
    def set_value(self, value: str):
        """Set selected value.
        
        Args:
            value: New value
        """
        old_value = self.value
        if any(opt[0] == value for opt in self.options):
            self.value = value
            self.notify_change(old_value, self.value)


class CheckboxComponent(UIComponent):
    """Checkbox component."""
    
    def __init__(self, id: str, label: str, value: bool = False):
        """Initialize checkbox.
        
        Args:
            id: Component ID
            label: Display label
            value: Initial checked state
        """
        super().__init__(id, label)
        self.value = value
    
    def set_value(self, value: bool):
        """Set checkbox state.
        
        Args:
            value: New checked state
        """
        old_value = self.value
        self.value = value
        self.notify_change(old_value, self.value)


class TextComponent(UIComponent):
    """Text input component."""
    
    def __init__(self, id: str, label: str, value: str = "", 
                 placeholder: str = "", multiline: bool = False):
        """Initialize text input.
        
        Args:
            id: Component ID
            label: Display label
            value: Initial value
            placeholder: Placeholder text
            multiline: Allow multiple lines
        """
        super().__init__(id, label)
        self.value = value
        self.placeholder = placeholder
        self.multiline = multiline
    
    def set_value(self, value: str):
        """Set text value.
        
        Args:
            value: New text value
        """
        old_value = self.value
        self.value = value
        self.notify_change(old_value, self.value)


class PreferencePanel:
    """Panel containing preference components."""
    
    def __init__(self, category: PreferenceCategory, title: str):
        """Initialize preference panel.
        
        Args:
            category: Preference category
            title: Panel title
        """
        self.category = category
        self.title = title
        self.components: List[UIComponent] = []
        self.manager: Optional[UserPreferencesManager] = None
        self.validation_errors: List[str] = []
    
    def add_component(self, component: UIComponent):
        """Add component to panel.
        
        Args:
            component: UI component to add
        """
        self.components.append(component)
        component.on_change(self._on_component_change)
    
    def _on_component_change(self, component_id: str, old_value: Any, new_value: Any):
        """Handle component value change.
        
        Args:
            component_id: ID of changed component
            old_value: Previous value
            new_value: New value
        """
        if self.manager:
            # Update preference
            key = component_id.replace(f"{self.category.value}_", "")
            self.manager.set_preference(self.category.value, key, new_value)
    
    def bind_manager(self, manager: UserPreferencesManager):
        """Bind preference manager.
        
        Args:
            manager: UserPreferencesManager instance
        """
        self.manager = manager
        self.load_from_preferences()
    
    def load_from_preferences(self):
        """Load component values from preferences."""
        if not self.manager:
            return
        
        category_prefs = getattr(self.manager.preferences, self.category.value)
        
        for component in self.components:
            key = component.id.replace(f"{self.category.value}_", "")
            if hasattr(category_prefs, key):
                value = getattr(category_prefs, key)
                
                # Handle enum values
                if hasattr(value, 'value'):
                    value = value.value
                
                component.set_value(value)
    
    def validate(self) -> ValidationResult:
        """Validate panel values.
        
        Returns:
            ValidationResult with errors and warnings
        """
        if not self.manager:
            return ValidationResult(True, [], [])
        
        # Get category-specific validation
        if self.category == PreferenceCategory.AUDIO:
            errors = PreferenceValidator.validate_audio(self.manager.preferences.audio)
        elif self.category == PreferenceCategory.VOICE:
            errors = PreferenceValidator.validate_voice(self.manager.preferences.voice)
        elif self.category == PreferenceCategory.ACCESSIBILITY:
            errors = PreferenceValidator.validate_accessibility(self.manager.preferences.accessibility)
        elif self.category == PreferenceCategory.BEHAVIOR:
            errors = PreferenceValidator.validate_behavior(self.manager.preferences.behavior)
        elif self.category == PreferenceCategory.ADVANCED:
            errors = PreferenceValidator.validate_advanced(self.manager.preferences.advanced)
        else:
            errors = []
        
        warnings = []
        
        # Check for potential issues
        if self.category == PreferenceCategory.AUDIO:
            audio = self.manager.preferences.audio
            if audio.volume > 1.5:
                warnings.append("High volume may cause audio distortion")
            if audio.microphone_gain > 3.0:
                warnings.append("High microphone gain may cause noise")
        
        self.validation_errors = errors
        return ValidationResult(len(errors) == 0, errors, warnings)


class AudioPreferencePanel(PreferencePanel):
    """Audio preferences panel."""
    
    def __init__(self):
        """Initialize audio panel."""
        super().__init__(PreferenceCategory.AUDIO, "Audio Settings")
        
        # Audio device selects
        self.add_component(SelectComponent(
            "audio_input_device",
            "Input Device",
            [("default", "Default"), ("mic1", "Microphone 1"), ("mic2", "Microphone 2")]
        ))
        
        self.add_component(SelectComponent(
            "audio_output_device",
            "Output Device",
            [("default", "Default"), ("speakers", "Speakers"), ("headphones", "Headphones")]
        ))
        
        # Audio format
        self.add_component(SelectComponent(
            "audio_format",
            "Audio Format",
            [(fmt.value, fmt.value.upper()) for fmt in AudioFormat]
        ))
        
        # Volume controls
        self.add_component(SliderComponent(
            "audio_volume",
            "Volume",
            0.0, 2.0, 0.1, 0.8
        ))
        
        self.add_component(SliderComponent(
            "audio_microphone_gain",
            "Microphone Gain",
            0.0, 5.0, 0.1, 1.0
        ))
        
        # Audio processing
        self.add_component(CheckboxComponent(
            "audio_noise_suppression",
            "Noise Suppression",
            True
        ))
        
        self.add_component(CheckboxComponent(
            "audio_echo_cancellation",
            "Echo Cancellation",
            True
        ))
        
        self.add_component(CheckboxComponent(
            "audio_auto_gain_control",
            "Automatic Gain Control",
            True
        ))
        
        self.add_component(CheckboxComponent(
            "audio_voice_activity_detection",
            "Voice Activity Detection",
            True
        ))
        
        # Advanced audio settings
        self.add_component(SliderComponent(
            "audio_silence_threshold",
            "Silence Threshold (dB)",
            -60.0, 0.0, 1.0, -30.0
        ))
        
        self.add_component(SliderComponent(
            "audio_silence_duration",
            "Silence Duration (seconds)",
            0.1, 10.0, 0.1, 2.0
        ))


class VoicePreferencePanel(PreferencePanel):
    """Voice preferences panel."""
    
    def __init__(self):
        """Initialize voice panel."""
        super().__init__(PreferenceCategory.VOICE, "Voice Settings")
        
        # Voice providers
        self.add_component(SelectComponent(
            "voice_tts_provider",
            "Text-to-Speech Provider",
            [(provider.value, provider.value.title()) for provider in VoiceProvider]
        ))
        
        self.add_component(SelectComponent(
            "voice_stt_provider",
            "Speech-to-Text Provider",
            [(provider.value, provider.value.title()) for provider in VoiceProvider]
        ))
        
        # Voice settings
        self.add_component(SelectComponent(
            "voice_tts_voice",
            "Voice",
            [("alloy", "Alloy"), ("echo", "Echo"), ("fable", "Fable"),
             ("onyx", "Onyx"), ("nova", "Nova"), ("shimmer", "Shimmer")]
        ))
        
        self.add_component(SliderComponent(
            "voice_tts_speed",
            "Speech Speed",
            0.25, 4.0, 0.05, 1.0
        ))
        
        self.add_component(SelectComponent(
            "voice_language",
            "Language",
            [("en", "English"), ("es", "Spanish"), ("fr", "French"),
             ("de", "German"), ("it", "Italian"), ("pt", "Portuguese")]
        ))
        
        # Voice features
        self.add_component(CheckboxComponent(
            "voice_streaming_enabled",
            "Enable Streaming",
            True
        ))
        
        self.add_component(CheckboxComponent(
            "voice_auto_start_recording",
            "Auto-start Recording",
            True
        ))
        
        self.add_component(CheckboxComponent(
            "voice_push_to_talk",
            "Push-to-Talk",
            False
        ))
        
        self.add_component(TextComponent(
            "voice_push_to_talk_key",
            "Push-to-Talk Key",
            "space"
        ))


class AccessibilityPreferencePanel(PreferencePanel):
    """Accessibility preferences panel."""
    
    def __init__(self):
        """Initialize accessibility panel."""
        super().__init__(PreferenceCategory.ACCESSIBILITY, "Accessibility")
        
        # Screen reader support
        self.add_component(CheckboxComponent(
            "accessibility_screen_reader_enabled",
            "Screen Reader Support",
            False
        ))
        
        self.add_component(CheckboxComponent(
            "accessibility_keyboard_navigation",
            "Keyboard Navigation",
            False
        ))
        
        self.add_component(CheckboxComponent(
            "accessibility_high_contrast",
            "High Contrast Mode",
            False
        ))
        
        # Visual accessibility
        self.add_component(SliderComponent(
            "accessibility_font_size_multiplier",
            "Font Size",
            0.5, 3.0, 0.1, 1.0
        ))
        
        self.add_component(CheckboxComponent(
            "accessibility_focus_indicators",
            "Focus Indicators",
            True
        ))
        
        self.add_component(CheckboxComponent(
            "accessibility_animation_reduced",
            "Reduce Animations",
            False
        ))
        
        self.add_component(CheckboxComponent(
            "accessibility_color_blind_friendly",
            "Color-blind Friendly",
            False
        ))
        
        # Voice accessibility
        self.add_component(CheckboxComponent(
            "accessibility_voice_announcements",
            "Voice Announcements",
            False
        ))
        
        self.add_component(CheckboxComponent(
            "accessibility_narrator_enabled",
            "Narrator",
            False
        ))
        
        self.add_component(SliderComponent(
            "accessibility_announcement_rate",
            "Announcement Speed",
            0.5, 3.0, 0.1, 1.0
        ))


class PreferenceManager:
    """High-level preference management interface."""
    
    def __init__(self, manager: UserPreferencesManager):
        """Initialize preference manager UI.
        
        Args:
            manager: UserPreferencesManager instance
        """
        self.manager = manager
        self.panels: List[PreferencePanel] = []
        self.current_panel = 0
        self.validation_results: Dict[str, ValidationResult] = {}
        
        # Create panels
        self._create_panels()
        
        # Bind manager to all panels
        for panel in self.panels:
            panel.bind_manager(self.manager)
    
    def _create_panels(self):
        """Create preference panels."""
        self.panels = [
            AudioPreferencePanel(),
            VoicePreferencePanel(),
            AccessibilityPreferencePanel(),
            # Could add more panels here
        ]
    
    def get_panel(self, category: PreferenceCategory) -> Optional[PreferencePanel]:
        """Get panel for category.
        
        Args:
            category: Preference category
            
        Returns:
            PreferencePanel or None
        """
        for panel in self.panels:
            if panel.category == category:
                return panel
        return None
    
    def validate_all(self) -> bool:
        """Validate all panels.
        
        Returns:
            True if all panels are valid
        """
        all_valid = True
        self.validation_results.clear()
        
        for panel in self.panels:
            result = panel.validate()
            self.validation_results[panel.category.value] = result
            if not result.valid:
                all_valid = False
        
        return all_valid
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation summary.
        
        Returns:
            Summary of validation results
        """
        total_errors = sum(len(r.errors) for r in self.validation_results.values())
        total_warnings = sum(len(r.warnings) for r in self.validation_results.values())
        
        return {
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'panels_valid': sum(1 for r in self.validation_results.values() if r.valid),
            'total_panels': len(self.validation_results),
            'details': self.validation_results
        }
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export UI state to dictionary.
        
        Returns:
            UI state dictionary
        """
        ui_state = {}
        
        for panel in self.panels:
            panel_state = {}
            for component in panel.components:
                panel_state[component.id] = {
                    'value': component.value,
                    'enabled': component.enabled,
                    'visible': component.visible
                }
            ui_state[panel.category.value] = panel_state
        
        return ui_state
    
    def import_from_dict(self, ui_state: Dict[str, Any]):
        """Import UI state from dictionary.
        
        Args:
            ui_state: UI state dictionary
        """
        for panel in self.panels:
            panel_state = ui_state.get(panel.category.value, {})
            
            for component in panel.components:
                component_state = panel_state.get(component.id, {})
                
                if 'value' in component_state:
                    component.set_value(component_state['value'])
                if 'enabled' in component_state:
                    component.enabled = component_state['enabled']
                if 'visible' in component_state:
                    component.visible = component_state['visible']
    
    def reset_panel(self, category: PreferenceCategory):
        """Reset panel to defaults.
        
        Args:
            category: Category to reset
        """
        self.manager.reset_to_defaults(category.value)
        
        panel = self.get_panel(category)
        if panel:
            panel.load_from_preferences()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get preference manager summary.
        
        Returns:
            Summary dictionary
        """
        return {
            'total_panels': len(self.panels),
            'current_profile': self.manager.current_profile,
            'validation_summary': self.get_validation_summary(),
            'preferences_summary': self.manager.get_statistics()
        }


class ProfileManager:
    """Profile management interface."""
    
    def __init__(self, manager: UserPreferencesManager):
        """Initialize profile manager.
        
        Args:
            manager: UserPreferencesManager instance
        """
        self.manager = manager
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """List available profiles with metadata.
        
        Returns:
            List of profile info dictionaries
        """
        profiles = []
        
        for profile_name in self.manager.list_profiles():
            # Load profile to get metadata
            current = self.manager.current_profile
            if self.manager.load_preferences(profile_name):
                prefs = self.manager.preferences
                profiles.append({
                    'name': profile_name,
                    'created_at': prefs.created_at.isoformat(),
                    'updated_at': prefs.updated_at.isoformat(),
                    'version': prefs.version,
                    'is_current': profile_name == current
                })
            
            # Restore original profile
            self.manager.load_preferences(current)
        
        return profiles
    
    def create_profile_dialog(self) -> Dict[str, Any]:
        """Get create profile dialog data.
        
        Returns:
            Dialog configuration
        """
        return {
            'title': 'Create New Profile',
            'fields': [
                {
                    'id': 'name',
                    'label': 'Profile Name',
                    'type': 'text',
                    'required': True,
                    'validation': r'^[a-zA-Z0-9_-]+$'
                },
                {
                    'id': 'copy_from',
                    'label': 'Copy From',
                    'type': 'select',
                    'options': [('', 'Use Defaults')] + [(p, p) for p in self.manager.list_profiles()],
                    'required': False
                },
                {
                    'id': 'description',
                    'label': 'Description',
                    'type': 'textarea',
                    'required': False
                }
            ],
            'actions': ['Create', 'Cancel']
        }
    
    def export_profile(self, profile_name: str, format: str = "json") -> str:
        """Export profile in specified format.
        
        Args:
            profile_name: Profile to export
            format: Export format
            
        Returns:
            Exported profile data
        """
        current = self.manager.current_profile
        
        try:
            # For default profile, just export current preferences if it's already loaded
            if profile_name == "default" and current == "default":
                return self.manager.export_preferences(format)
            elif self.manager.load_preferences(profile_name):
                exported = self.manager.export_preferences(format)
                return exported
            else:
                raise ValueError(f"Profile not found: {profile_name}")
        finally:
            if current != profile_name:
                self.manager.load_preferences(current)
    
    def import_profile(self, name: str, data: str, format: str = "json") -> bool:
        """Import profile from data.
        
        Args:
            name: Profile name
            data: Profile data
            format: Data format
            
        Returns:
            True if imported successfully
        """
        current = self.manager.current_profile
        
        try:
            # Import into temporary preferences
            if self.manager.import_preferences(data, format):
                # Save as new profile
                self.manager.save_preferences(name)
                return True
            return False
        finally:
            self.manager.load_preferences(current)


# Console interface for preference management
class ConsolePreferenceInterface:
    """Console-based preference interface."""
    
    def __init__(self, manager: UserPreferencesManager):
        """Initialize console interface.
        
        Args:
            manager: UserPreferencesManager instance
        """
        self.manager = manager
        self.pref_manager = PreferenceManager(manager)
    
    def show_menu(self):
        """Show main menu."""
        print("\n" + "=" * 50)
        print("VOICE MODE PREFERENCES")
        print("=" * 50)
        print("1. Audio Settings")
        print("2. Voice Settings")
        print("3. Accessibility Settings")
        print("4. Profile Management")
        print("5. Import/Export")
        print("6. Validate Settings")
        print("7. Reset to Defaults")
        print("8. Show Statistics")
        print("0. Exit")
        print("=" * 50)
    
    def show_audio_panel(self):
        """Show audio preferences panel."""
        panel = self.pref_manager.get_panel(PreferenceCategory.AUDIO)
        if not panel:
            return
        
        print(f"\n=== {panel.title} ===")
        
        for i, component in enumerate(panel.components, 1):
            print(f"{i:2d}. {component.label}: {component.value}")
        
        print(f"{len(panel.components)+1:2d}. Back to main menu")
    
    def run_interactive(self):
        """Run interactive console interface."""
        while True:
            self.show_menu()
            
            try:
                choice = input("\nSelect option (0-8): ").strip()
                
                if choice == "0":
                    break
                elif choice == "1":
                    self.show_audio_panel()
                elif choice == "6":
                    self.validate_and_show()
                elif choice == "8":
                    self.show_statistics()
                else:
                    print("Option not implemented yet")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def validate_and_show(self):
        """Validate and show results."""
        print("\n=== Validation Results ===")
        
        is_valid = self.pref_manager.validate_all()
        summary = self.pref_manager.get_validation_summary()
        
        print(f"Overall Status: {'✓ Valid' if is_valid else '✗ Invalid'}")
        print(f"Total Errors: {summary['total_errors']}")
        print(f"Total Warnings: {summary['total_warnings']}")
        print(f"Valid Panels: {summary['panels_valid']}/{summary['total_panels']}")
        
        for category, result in summary['details'].items():
            if result.errors:
                print(f"\n{category.title()} Errors:")
                for error in result.errors:
                    print(f"  • {error}")
            
            if result.warnings:
                print(f"\n{category.title()} Warnings:")
                for warning in result.warnings:
                    print(f"  • {warning}")
    
    def show_statistics(self):
        """Show preference statistics."""
        print("\n=== Preference Statistics ===")
        
        stats = self.manager.get_statistics()
        
        print(f"Current Profile: {stats['current_profile']}")
        print(f"Total Profiles: {stats['total_profiles']}")
        print(f"Auto-save: {stats['auto_save']}")
        print(f"Config Directory: {stats['config_directory']}")
        print(f"Last Updated: {stats['last_updated']}")
        print(f"Version: {stats['version']}")
        print(f"Validation Errors: {stats['validation_errors']}")


# Example usage
if __name__ == "__main__":
    from .user_preferences import get_preferences_manager
    
    # Create console interface
    manager = get_preferences_manager()
    interface = ConsolePreferenceInterface(manager)
    
    # Run interactive interface
    interface.run_interactive()