"""
User preferences system for voice mode configuration.

This module provides comprehensive user preference management including:
- Audio, voice, accessibility, and behavior settings
- Persistent storage with JSON format
- Schema validation and migration
- Import/export functionality
- Profile management and defaults
"""

import json
import os
import threading
import time
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PreferenceCategory(Enum):
    """Categories of user preferences."""
    AUDIO = "audio"
    VOICE = "voice"
    ACCESSIBILITY = "accessibility"
    BEHAVIOR = "behavior"
    INTERFACE = "interface"
    KEYBOARD = "keyboard"
    ADVANCED = "advanced"


class AudioFormat(Enum):
    """Supported audio formats."""
    PCM = "pcm"
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    AAC = "aac"
    OPUS = "opus"


class VoiceProvider(Enum):
    """Voice service providers."""
    OPENAI = "openai"
    KOKORO = "kokoro"
    LIVEKIT = "livekit"
    WHISPER = "whisper"


@dataclass
class AudioPreferences:
    """Audio-related preferences."""
    input_device: Optional[str] = None
    output_device: Optional[str] = None
    sample_rate: int = 16000
    channels: int = 1
    format: AudioFormat = AudioFormat.PCM
    volume: float = 0.8
    microphone_gain: float = 1.0
    noise_suppression: bool = True
    echo_cancellation: bool = True
    auto_gain_control: bool = True
    voice_activity_detection: bool = True
    silence_threshold: float = -30.0
    silence_duration: float = 2.0


@dataclass
class VoicePreferences:
    """Voice service preferences."""
    tts_provider: VoiceProvider = VoiceProvider.OPENAI
    stt_provider: VoiceProvider = VoiceProvider.OPENAI
    tts_voice: str = "alloy"
    tts_speed: float = 1.0
    tts_model: str = "tts-1"
    stt_model: str = "whisper-1"
    language: str = "en"
    streaming_enabled: bool = True
    auto_start_recording: bool = True
    push_to_talk: bool = False
    push_to_talk_key: str = "space"


@dataclass
class AccessibilityPreferences:
    """Accessibility preferences."""
    screen_reader_enabled: bool = False
    keyboard_navigation: bool = False
    high_contrast: bool = False
    voice_announcements: bool = False
    focus_indicators: bool = True
    font_size_multiplier: float = 1.0
    animation_reduced: bool = False
    color_blind_friendly: bool = False
    narrator_enabled: bool = False
    announcement_rate: float = 1.0


@dataclass
class BehaviorPreferences:
    """Behavior and interaction preferences."""
    auto_save_conversations: bool = True
    conversation_history_limit: int = 1000
    auto_export_format: str = "json"
    notification_enabled: bool = True
    sound_effects: bool = True
    visual_feedback: bool = True
    interrupt_handling: bool = True
    context_awareness: bool = True
    learning_mode: bool = False
    debug_mode: bool = False


@dataclass
class InterfacePreferences:
    """Interface and display preferences."""
    theme: str = "dark"
    transcript_enabled: bool = True
    timestamp_format: str = "%H:%M:%S"
    show_confidence_scores: bool = False
    show_processing_indicators: bool = True
    compact_mode: bool = False
    window_position: Optional[str] = None
    window_size: Optional[str] = None
    always_on_top: bool = False
    minimize_to_tray: bool = True


@dataclass
class KeyboardPreferences:
    """Keyboard shortcuts and commands."""
    shortcuts_enabled: bool = True
    custom_bindings: Dict[str, str] = field(default_factory=dict)
    command_palette_key: str = "Ctrl+Shift+P"
    global_shortcuts: bool = False
    vim_mode: bool = False
    emacs_mode: bool = False


@dataclass
class AdvancedPreferences:
    """Advanced technical preferences."""
    api_timeout: float = 30.0
    retry_attempts: int = 3
    cache_enabled: bool = True
    cache_size_mb: int = 100
    log_level: str = "INFO"
    telemetry_enabled: bool = True
    experimental_features: bool = False
    custom_endpoints: Dict[str, str] = field(default_factory=dict)
    env_overrides: Dict[str, str] = field(default_factory=dict)


@dataclass
class UserPreferences:
    """Complete user preferences container."""
    audio: AudioPreferences = field(default_factory=AudioPreferences)
    voice: VoicePreferences = field(default_factory=VoicePreferences)
    accessibility: AccessibilityPreferences = field(default_factory=AccessibilityPreferences)
    behavior: BehaviorPreferences = field(default_factory=BehaviorPreferences)
    interface: InterfacePreferences = field(default_factory=InterfacePreferences)
    keyboard: KeyboardPreferences = field(default_factory=KeyboardPreferences)
    advanced: AdvancedPreferences = field(default_factory=AdvancedPreferences)
    
    # Metadata
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    profile_name: str = "default"


class PreferenceValidator:
    """Validates preference values and schemas."""
    
    @staticmethod
    def validate_audio(audio: AudioPreferences) -> List[str]:
        """Validate audio preferences.
        
        Args:
            audio: Audio preferences to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if audio.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            errors.append(f"Invalid sample rate: {audio.sample_rate}")
        
        if audio.channels not in [1, 2]:
            errors.append(f"Invalid channel count: {audio.channels}")
        
        if not 0.0 <= audio.volume <= 2.0:
            errors.append(f"Volume must be 0.0-2.0: {audio.volume}")
        
        if not 0.0 <= audio.microphone_gain <= 5.0:
            errors.append(f"Microphone gain must be 0.0-5.0: {audio.microphone_gain}")
        
        if not -60.0 <= audio.silence_threshold <= 0.0:
            errors.append(f"Silence threshold must be -60.0 to 0.0: {audio.silence_threshold}")
        
        if not 0.1 <= audio.silence_duration <= 10.0:
            errors.append(f"Silence duration must be 0.1-10.0: {audio.silence_duration}")
        
        return errors
    
    @staticmethod
    def validate_voice(voice: VoicePreferences) -> List[str]:
        """Validate voice preferences.
        
        Args:
            voice: Voice preferences to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not 0.25 <= voice.tts_speed <= 4.0:
            errors.append(f"TTS speed must be 0.25-4.0: {voice.tts_speed}")
        
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice.tts_voice not in valid_voices:
            errors.append(f"Invalid TTS voice: {voice.tts_voice}")
        
        valid_languages = ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]
        if voice.language not in valid_languages:
            errors.append(f"Invalid language: {voice.language}")
        
        return errors
    
    @staticmethod
    def validate_accessibility(accessibility: AccessibilityPreferences) -> List[str]:
        """Validate accessibility preferences.
        
        Args:
            accessibility: Accessibility preferences to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not 0.5 <= accessibility.font_size_multiplier <= 3.0:
            errors.append(f"Font size multiplier must be 0.5-3.0: {accessibility.font_size_multiplier}")
        
        if not 0.5 <= accessibility.announcement_rate <= 3.0:
            errors.append(f"Announcement rate must be 0.5-3.0: {accessibility.announcement_rate}")
        
        return errors
    
    @staticmethod
    def validate_behavior(behavior: BehaviorPreferences) -> List[str]:
        """Validate behavior preferences.
        
        Args:
            behavior: Behavior preferences to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not 10 <= behavior.conversation_history_limit <= 10000:
            errors.append(f"History limit must be 10-10000: {behavior.conversation_history_limit}")
        
        valid_formats = ["json", "plain", "markdown", "html"]
        if behavior.auto_export_format not in valid_formats:
            errors.append(f"Invalid export format: {behavior.auto_export_format}")
        
        return errors
    
    @staticmethod
    def validate_advanced(advanced: AdvancedPreferences) -> List[str]:
        """Validate advanced preferences.
        
        Args:
            advanced: Advanced preferences to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not 1.0 <= advanced.api_timeout <= 300.0:
            errors.append(f"API timeout must be 1.0-300.0: {advanced.api_timeout}")
        
        if not 1 <= advanced.retry_attempts <= 10:
            errors.append(f"Retry attempts must be 1-10: {advanced.retry_attempts}")
        
        if not 10 <= advanced.cache_size_mb <= 1000:
            errors.append(f"Cache size must be 10-1000 MB: {advanced.cache_size_mb}")
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if advanced.log_level not in valid_log_levels:
            errors.append(f"Invalid log level: {advanced.log_level}")
        
        return errors
    
    @classmethod
    def validate_preferences(cls, preferences: UserPreferences) -> List[str]:
        """Validate complete preferences object.
        
        Args:
            preferences: Preferences to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        errors.extend(cls.validate_audio(preferences.audio))
        errors.extend(cls.validate_voice(preferences.voice))
        errors.extend(cls.validate_accessibility(preferences.accessibility))
        errors.extend(cls.validate_behavior(preferences.behavior))
        errors.extend(cls.validate_advanced(preferences.advanced))
        
        return errors


class PreferenceMigrator:
    """Handles preference schema migration."""
    
    @staticmethod
    def migrate_from_version(data: Dict[str, Any], from_version: str) -> Dict[str, Any]:
        """Migrate preferences from older version.
        
        Args:
            data: Preference data to migrate
            from_version: Source version
            
        Returns:
            Migrated preference data
        """
        if from_version == "0.9.0":
            # Example migration from 0.9.0 to 1.0.0
            if "audio_settings" in data:
                data["audio"] = data.pop("audio_settings")
            
            if "voice_settings" in data:
                data["voice"] = data.pop("voice_settings")
        
        # Add current version and timestamps
        data["version"] = "1.0.0"
        data["updated_at"] = datetime.now().isoformat()
        
        return data
    
    @classmethod
    def needs_migration(cls, data: Dict[str, Any]) -> bool:
        """Check if data needs migration.
        
        Args:
            data: Preference data to check
            
        Returns:
            True if migration is needed
        """
        current_version = "1.0.0"
        data_version = data.get("version", "0.0.0")
        return data_version != current_version


class UserPreferencesManager:
    """Manages user preferences with persistence and validation."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize preferences manager.
        
        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = config_dir or Path.home() / ".voice_mode"
        self.config_dir.mkdir(exist_ok=True)
        
        self.preferences_file = self.config_dir / "preferences.json"
        self.profiles_dir = self.config_dir / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)
        
        # Current preferences
        self.preferences = UserPreferences()
        self.current_profile = "default"
        
        # Change tracking
        self.change_callbacks: List[Callable[[str, Any, Any], None]] = []
        self.auto_save = True
        self.save_lock = threading.Lock()
        
        # Load preferences
        self.load_preferences()
    
    def load_preferences(self, profile: str = "default") -> bool:
        """Load preferences from file.
        
        Args:
            profile: Profile name to load
            
        Returns:
            True if loaded successfully
        """
        try:
            profile_file = self.profiles_dir / f"{profile}.json"
            
            # Try profile-specific file first
            if profile_file.exists():
                config_file = profile_file
            else:
                config_file = self.preferences_file
            
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                # Handle migration if needed
                if PreferenceMigrator.needs_migration(data):
                    old_version = data.get("version", "0.0.0")
                    data = PreferenceMigrator.migrate_from_version(data, old_version)
                    logger.info(f"Migrated preferences from {old_version} to {data['version']}")
                
                # Convert datetime strings back to objects
                if "created_at" in data:
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                if "updated_at" in data:
                    data["updated_at"] = datetime.fromisoformat(data["updated_at"])
                
                # Create preferences object from data
                self.preferences = self._dict_to_preferences(data)
                self.current_profile = profile
                
                logger.info(f"Loaded preferences for profile: {profile}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to load preferences: {e}")
        
        # Use defaults if loading failed
        self.preferences = UserPreferences()
        self.current_profile = profile
        return False
    
    def save_preferences(self, profile: Optional[str] = None) -> bool:
        """Save preferences to file.
        
        Args:
            profile: Profile name to save (defaults to current)
            
        Returns:
            True if saved successfully
        """
        if not self.auto_save and profile is None:
            return True
        
        profile = profile or self.current_profile
        
        try:
            with self.save_lock:
                # Update timestamps
                self.preferences.updated_at = datetime.now()
                self.preferences.profile_name = profile
                
                # Convert to dict for JSON serialization
                data = self._preferences_to_dict(self.preferences)
                
                # Determine save location
                if profile == "default":
                    config_file = self.preferences_file
                else:
                    config_file = self.profiles_dir / f"{profile}.json"
                
                # Create backup of existing file
                if config_file.exists():
                    backup_file = config_file.with_suffix('.json.backup')
                    config_file.rename(backup_file)
                
                # Write new preferences
                with open(config_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                logger.info(f"Saved preferences for profile: {profile}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            return False
    
    def _dict_to_preferences(self, data: Dict[str, Any]) -> UserPreferences:
        """Convert dictionary to preferences object.
        
        Args:
            data: Dictionary data
            
        Returns:
            UserPreferences object
        """
        # Handle nested dataclasses
        prefs_data = data.copy()
        
        # Convert enums and nested objects
        if "audio" in prefs_data:
            audio_data = prefs_data["audio"].copy()
            if "format" in audio_data:
                if isinstance(audio_data["format"], str):
                    audio_data["format"] = AudioFormat(audio_data["format"])
            prefs_data["audio"] = AudioPreferences(**audio_data)
        
        if "voice" in prefs_data:
            voice_data = prefs_data["voice"].copy()
            if "tts_provider" in voice_data:
                if isinstance(voice_data["tts_provider"], str):
                    voice_data["tts_provider"] = VoiceProvider(voice_data["tts_provider"])
            if "stt_provider" in voice_data:
                if isinstance(voice_data["stt_provider"], str):
                    voice_data["stt_provider"] = VoiceProvider(voice_data["stt_provider"])
            prefs_data["voice"] = VoicePreferences(**voice_data)
        
        if "accessibility" in prefs_data:
            prefs_data["accessibility"] = AccessibilityPreferences(**prefs_data["accessibility"])
        
        if "behavior" in prefs_data:
            prefs_data["behavior"] = BehaviorPreferences(**prefs_data["behavior"])
        
        if "interface" in prefs_data:
            prefs_data["interface"] = InterfacePreferences(**prefs_data["interface"])
        
        if "keyboard" in prefs_data:
            prefs_data["keyboard"] = KeyboardPreferences(**prefs_data["keyboard"])
        
        if "advanced" in prefs_data:
            prefs_data["advanced"] = AdvancedPreferences(**prefs_data["advanced"])
        
        return UserPreferences(**prefs_data)
    
    def _preferences_to_dict(self, preferences: UserPreferences) -> Dict[str, Any]:
        """Convert preferences object to dictionary.
        
        Args:
            preferences: UserPreferences object
            
        Returns:
            Dictionary representation
        """
        data = asdict(preferences)
        
        # Convert enums to strings
        if "audio" in data and "format" in data["audio"]:
            fmt = data["audio"]["format"]
            data["audio"]["format"] = fmt.value if hasattr(fmt, 'value') else fmt
        
        if "voice" in data:
            if "tts_provider" in data["voice"]:
                provider = data["voice"]["tts_provider"]
                data["voice"]["tts_provider"] = provider.value if hasattr(provider, 'value') else provider
            if "stt_provider" in data["voice"]:
                provider = data["voice"]["stt_provider"]
                data["voice"]["stt_provider"] = provider.value if hasattr(provider, 'value') else provider
        
        return data
    
    def get_preference(self, category: str, key: str) -> Any:
        """Get specific preference value.
        
        Args:
            category: Preference category (audio, voice, etc.)
            key: Preference key
            
        Returns:
            Preference value
        """
        category_obj = getattr(self.preferences, category, None)
        if category_obj is None:
            raise ValueError(f"Invalid preference category: {category}")
        
        return getattr(category_obj, key, None)
    
    def set_preference(self, category: str, key: str, value: Any) -> bool:
        """Set specific preference value.
        
        Args:
            category: Preference category
            key: Preference key
            value: New value
            
        Returns:
            True if set successfully
        """
        try:
            category_obj = getattr(self.preferences, category, None)
            if category_obj is None:
                raise ValueError(f"Invalid preference category: {category}")
            
            old_value = getattr(category_obj, key, None)
            setattr(category_obj, key, value)
            
            # Validate change
            if category == "audio":
                errors = PreferenceValidator.validate_audio(self.preferences.audio)
            elif category == "voice":
                errors = PreferenceValidator.validate_voice(self.preferences.voice)
            elif category == "accessibility":
                errors = PreferenceValidator.validate_accessibility(self.preferences.accessibility)
            elif category == "behavior":
                errors = PreferenceValidator.validate_behavior(self.preferences.behavior)
            elif category == "advanced":
                errors = PreferenceValidator.validate_advanced(self.preferences.advanced)
            else:
                errors = []
            
            if errors:
                # Revert change
                setattr(category_obj, key, old_value)
                logger.error(f"Invalid preference value: {errors}")
                return False
            
            # Notify callbacks
            for callback in self.change_callbacks:
                try:
                    callback(f"{category}.{key}", old_value, value)
                except Exception as e:
                    logger.error(f"Preference change callback error: {e}")
            
            # Auto-save if enabled
            if self.auto_save:
                self.save_preferences()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set preference {category}.{key}: {e}")
            return False
    
    def register_change_callback(self, callback: Callable[[str, Any, Any], None]):
        """Register callback for preference changes.
        
        Args:
            callback: Function to call on preference changes
        """
        self.change_callbacks.append(callback)
    
    def validate_all(self) -> List[str]:
        """Validate all current preferences.
        
        Returns:
            List of validation errors
        """
        return PreferenceValidator.validate_preferences(self.preferences)
    
    def reset_to_defaults(self, category: Optional[str] = None):
        """Reset preferences to defaults.
        
        Args:
            category: Category to reset (None for all)
        """
        if category is None:
            self.preferences = UserPreferences()
        else:
            if category == "audio":
                self.preferences.audio = AudioPreferences()
            elif category == "voice":
                self.preferences.voice = VoicePreferences()
            elif category == "accessibility":
                self.preferences.accessibility = AccessibilityPreferences()
            elif category == "behavior":
                self.preferences.behavior = BehaviorPreferences()
            elif category == "interface":
                self.preferences.interface = InterfacePreferences()
            elif category == "keyboard":
                self.preferences.keyboard = KeyboardPreferences()
            elif category == "advanced":
                self.preferences.advanced = AdvancedPreferences()
        
        if self.auto_save:
            self.save_preferences()
    
    def export_preferences(self, format: str = "json") -> str:
        """Export preferences in specified format.
        
        Args:
            format: Export format (json, yaml, toml)
            
        Returns:
            Exported preferences string
        """
        data = self._preferences_to_dict(self.preferences)
        
        if format == "json":
            return json.dumps(data, indent=2, default=str)
        elif format == "yaml":
            try:
                import yaml
                return yaml.dump(data, default_flow_style=False)
            except ImportError:
                raise ValueError("PyYAML not installed")
        elif format == "toml":
            try:
                import toml
                return toml.dumps(data)
            except ImportError:
                raise ValueError("toml not installed")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_preferences(self, data: str, format: str = "json") -> bool:
        """Import preferences from string.
        
        Args:
            data: Preferences data string
            format: Data format (json, yaml, toml)
            
        Returns:
            True if imported successfully
        """
        try:
            if format == "json":
                parsed_data = json.loads(data)
            elif format == "yaml":
                import yaml
                parsed_data = yaml.safe_load(data)
            elif format == "toml":
                import toml
                parsed_data = toml.loads(data)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Validate imported data
            temp_preferences = self._dict_to_preferences(parsed_data)
            errors = PreferenceValidator.validate_preferences(temp_preferences)
            
            if errors:
                logger.error(f"Invalid imported preferences: {errors}")
                return False
            
            # Apply imported preferences
            self.preferences = temp_preferences
            
            if self.auto_save:
                self.save_preferences()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to import preferences: {e}")
            return False
    
    def list_profiles(self) -> List[str]:
        """List available preference profiles.
        
        Returns:
            List of profile names
        """
        profiles = ["default"]
        
        for profile_file in self.profiles_dir.glob("*.json"):
            if profile_file.stem != "default":
                profiles.append(profile_file.stem)
        
        return profiles
    
    def create_profile(self, name: str, copy_from: Optional[str] = None) -> bool:
        """Create new preference profile.
        
        Args:
            name: Profile name
            copy_from: Source profile to copy from
            
        Returns:
            True if created successfully
        """
        try:
            if copy_from:
                # Load source profile
                old_profile = self.current_profile
                if self.load_preferences(copy_from):
                    self.save_preferences(name)
                    self.load_preferences(old_profile)  # Restore original
                    return True
                else:
                    return False
            else:
                # Create with defaults
                old_preferences = self.preferences
                self.preferences = UserPreferences()
                self.save_preferences(name)
                self.preferences = old_preferences
                return True
                
        except Exception as e:
            logger.error(f"Failed to create profile {name}: {e}")
            return False
    
    def delete_profile(self, name: str) -> bool:
        """Delete preference profile.
        
        Args:
            name: Profile name to delete
            
        Returns:
            True if deleted successfully
        """
        if name == "default":
            return False  # Cannot delete default profile
        
        try:
            profile_file = self.profiles_dir / f"{name}.json"
            if profile_file.exists():
                profile_file.unlink()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete profile {name}: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get preference manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'current_profile': self.current_profile,
            'total_profiles': len(self.list_profiles()),
            'auto_save': self.auto_save,
            'config_directory': str(self.config_dir),
            'last_updated': self.preferences.updated_at.isoformat(),
            'version': self.preferences.version,
            'validation_errors': len(self.validate_all())
        }


def get_preferences_manager() -> UserPreferencesManager:
    """Get global preferences manager instance.
    
    Returns:
        UserPreferencesManager instance
    """
    global _preferences_manager
    if '_preferences_manager' not in globals():
        _preferences_manager = UserPreferencesManager()
    return _preferences_manager


# Example usage
if __name__ == "__main__":
    # Create preferences manager
    manager = UserPreferencesManager()
    
    # Set some preferences
    manager.set_preference("audio", "volume", 0.9)
    manager.set_preference("voice", "tts_speed", 1.2)
    manager.set_preference("accessibility", "high_contrast", True)
    
    # Register change callback
    def on_preference_change(key: str, old_value: Any, new_value: Any):
        print(f"Preference changed: {key} = {old_value} -> {new_value}")
    
    manager.register_change_callback(on_preference_change)
    
    # Test validation
    errors = manager.validate_all()
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("All preferences valid")
    
    # Export preferences
    exported = manager.export_preferences("json")
    print(f"Exported preferences: {len(exported)} characters")
    
    # Show statistics
    stats = manager.get_statistics()
    print(f"Statistics: {stats}")