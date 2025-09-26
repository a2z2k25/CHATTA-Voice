"""
Voice profile management for personalized interactions.

This module provides user voice profiles with preferences,
custom settings, and voice characteristics for personalized
conversation experiences.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import pickle

logger = logging.getLogger(__name__)


class VoiceGender(Enum):
    """Voice gender options."""
    MALE = auto()
    FEMALE = auto()
    NEUTRAL = auto()
    CUSTOM = auto()


class VoiceAge(Enum):
    """Voice age ranges."""
    CHILD = auto()
    YOUNG = auto()
    MIDDLE = auto()
    SENIOR = auto()


class VoiceStyle(Enum):
    """Voice speaking styles."""
    PROFESSIONAL = auto()
    CASUAL = auto()
    FRIENDLY = auto()
    SERIOUS = auto()
    ENTHUSIASTIC = auto()
    CALM = auto()
    ASSERTIVE = auto()
    WARM = auto()


class InteractionMode(Enum):
    """Interaction preferences."""
    CONVERSATIONAL = auto()
    CONCISE = auto()
    DETAILED = auto()
    TUTORIAL = auto()
    ASSISTANT = auto()


@dataclass
class VoiceCharacteristics:
    """Voice characteristic settings."""
    gender: VoiceGender = VoiceGender.NEUTRAL
    age: VoiceAge = VoiceAge.MIDDLE
    style: VoiceStyle = VoiceStyle.FRIENDLY
    pitch: float = 0.0  # -1.0 to 1.0
    rate: float = 1.0   # 0.5 to 2.0
    volume: float = 1.0  # 0.0 to 1.0
    timbre: str = "neutral"
    accent: Optional[str] = None
    emotion: Optional[str] = None


@dataclass
class AudioPreferences:
    """Audio processing preferences."""
    sample_rate: int = 16000
    noise_suppression: bool = True
    echo_cancellation: bool = True
    auto_gain_control: bool = True
    silence_threshold: float = 0.03
    silence_duration: float = 1.0
    vad_aggressiveness: int = 2  # 0-3
    preferred_format: str = "wav"
    streaming: bool = True
    buffer_size: int = 512


@dataclass
class ConversationPreferences:
    """Conversation style preferences."""
    interaction_mode: InteractionMode = InteractionMode.CONVERSATIONAL
    response_length: str = "medium"  # short, medium, long
    formality: str = "neutral"  # casual, neutral, formal
    use_fillers: bool = False  # um, uh, etc.
    allow_interruptions: bool = True
    confirmation_style: str = "brief"  # none, brief, detailed
    error_handling: str = "friendly"  # minimal, friendly, detailed
    patience_level: float = 1.0  # 0.5 to 2.0 (wait time multiplier)
    preferred_language: str = "en"
    auto_translate: bool = False


@dataclass
class VoiceProfile:
    """Complete voice profile for a user."""
    profile_id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    voice_characteristics: VoiceCharacteristics = field(default_factory=VoiceCharacteristics)
    audio_preferences: AudioPreferences = field(default_factory=AudioPreferences)
    conversation_preferences: ConversationPreferences = field(default_factory=ConversationPreferences)
    voice_id: Optional[str] = None  # Specific TTS voice ID
    model_variant: Optional[str] = None  # Specific STT model
    custom_vocabulary: List[str] = field(default_factory=list)
    blocked_words: List[str] = field(default_factory=list)
    voice_samples: List[str] = field(default_factory=list)  # Paths to voice samples
    usage_stats: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary.
        
        Returns:
            Dictionary representation
        """
        data = asdict(self)
        # Convert datetime objects
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        # Convert enums
        data['voice_characteristics']['gender'] = self.voice_characteristics.gender.name
        data['voice_characteristics']['age'] = self.voice_characteristics.age.name
        data['voice_characteristics']['style'] = self.voice_characteristics.style.name
        data['conversation_preferences']['interaction_mode'] = self.conversation_preferences.interaction_mode.name
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoiceProfile':
        """Create profile from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            Voice profile instance
        """
        # Convert datetime strings
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Convert voice characteristics
        if 'voice_characteristics' in data:
            vc = data['voice_characteristics']
            if isinstance(vc.get('gender'), str):
                vc['gender'] = VoiceGender[vc['gender']]
            if isinstance(vc.get('age'), str):
                vc['age'] = VoiceAge[vc['age']]
            if isinstance(vc.get('style'), str):
                vc['style'] = VoiceStyle[vc['style']]
            data['voice_characteristics'] = VoiceCharacteristics(**vc)
        
        # Convert audio preferences
        if 'audio_preferences' in data:
            data['audio_preferences'] = AudioPreferences(**data['audio_preferences'])
        
        # Convert conversation preferences
        if 'conversation_preferences' in data:
            cp = data['conversation_preferences']
            if isinstance(cp.get('interaction_mode'), str):
                cp['interaction_mode'] = InteractionMode[cp['interaction_mode']]
            data['conversation_preferences'] = ConversationPreferences(**cp)
        
        return cls(**data)


class VoiceProfileManager:
    """Manages voice profiles."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize profile manager.
        
        Args:
            storage_dir: Directory for profile storage
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".chatta" / "profiles"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.profiles: Dict[str, VoiceProfile] = {}
        self.active_profile: Optional[VoiceProfile] = None
        self.default_profile_id: Optional[str] = None
        
        # Load existing profiles
        self._load_profiles()
    
    def _load_profiles(self):
        """Load profiles from storage."""
        profile_files = self.storage_dir.glob("*.json")
        
        for file_path in profile_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    profile = VoiceProfile.from_dict(data)
                    self.profiles[profile.profile_id] = profile
                    logger.info(f"Loaded profile: {profile.name}")
            except Exception as e:
                logger.error(f"Failed to load profile {file_path}: {e}")
        
        # Load default profile ID
        default_file = self.storage_dir / ".default"
        if default_file.exists():
            self.default_profile_id = default_file.read_text().strip()
    
    def _save_profile(self, profile: VoiceProfile):
        """Save profile to storage.
        
        Args:
            profile: Profile to save
        """
        file_path = self.storage_dir / f"{profile.profile_id}.json"
        
        try:
            with open(file_path, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)
            logger.info(f"Saved profile: {profile.name}")
        except Exception as e:
            logger.error(f"Failed to save profile {profile.name}: {e}")
    
    def _generate_profile_id(self, name: str) -> str:
        """Generate unique profile ID.
        
        Args:
            name: Profile name
            
        Returns:
            Profile ID
        """
        timestamp = datetime.now().isoformat()
        data = f"{name}_{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def create_profile(
        self,
        name: str,
        voice_characteristics: Optional[VoiceCharacteristics] = None,
        audio_preferences: Optional[AudioPreferences] = None,
        conversation_preferences: Optional[ConversationPreferences] = None,
        **kwargs
    ) -> VoiceProfile:
        """Create new voice profile.
        
        Args:
            name: Profile name
            voice_characteristics: Voice settings
            audio_preferences: Audio settings
            conversation_preferences: Conversation settings
            **kwargs: Additional profile attributes
            
        Returns:
            Created profile
        """
        profile_id = self._generate_profile_id(name)
        
        profile = VoiceProfile(
            profile_id=profile_id,
            name=name,
            voice_characteristics=voice_characteristics or VoiceCharacteristics(),
            audio_preferences=audio_preferences or AudioPreferences(),
            conversation_preferences=conversation_preferences or ConversationPreferences(),
            **kwargs
        )
        
        self.profiles[profile_id] = profile
        self._save_profile(profile)
        
        logger.info(f"Created profile: {name} ({profile_id})")
        return profile
    
    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """Get profile by ID.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            Profile or None
        """
        return self.profiles.get(profile_id)
    
    def get_profile_by_name(self, name: str) -> Optional[VoiceProfile]:
        """Get profile by name.
        
        Args:
            name: Profile name
            
        Returns:
            Profile or None
        """
        for profile in self.profiles.values():
            if profile.name == name:
                return profile
        return None
    
    def update_profile(
        self,
        profile_id: str,
        **updates
    ) -> Optional[VoiceProfile]:
        """Update profile attributes.
        
        Args:
            profile_id: Profile ID
            **updates: Attributes to update
            
        Returns:
            Updated profile or None
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        
        # Update nested attributes
        if 'voice_characteristics' in updates:
            for key, value in updates['voice_characteristics'].items():
                setattr(profile.voice_characteristics, key, value)
            del updates['voice_characteristics']
        
        if 'audio_preferences' in updates:
            for key, value in updates['audio_preferences'].items():
                setattr(profile.audio_preferences, key, value)
            del updates['audio_preferences']
        
        if 'conversation_preferences' in updates:
            for key, value in updates['conversation_preferences'].items():
                setattr(profile.conversation_preferences, key, value)
            del updates['conversation_preferences']
        
        # Update top-level attributes
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now()
        self._save_profile(profile)
        
        logger.info(f"Updated profile: {profile.name}")
        return profile
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete profile.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            True if deleted
        """
        if profile_id not in self.profiles:
            return False
        
        profile = self.profiles[profile_id]
        
        # Remove from memory
        del self.profiles[profile_id]
        
        # Remove from storage
        file_path = self.storage_dir / f"{profile_id}.json"
        if file_path.exists():
            file_path.unlink()
        
        # Clear active profile if needed
        if self.active_profile and self.active_profile.profile_id == profile_id:
            self.active_profile = None
        
        # Clear default if needed
        if self.default_profile_id == profile_id:
            self.default_profile_id = None
            default_file = self.storage_dir / ".default"
            if default_file.exists():
                default_file.unlink()
        
        logger.info(f"Deleted profile: {profile.name}")
        return True
    
    def set_active_profile(self, profile_id: str) -> bool:
        """Set active profile.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            True if set
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return False
        
        self.active_profile = profile
        logger.info(f"Active profile: {profile.name}")
        return True
    
    def set_default_profile(self, profile_id: str) -> bool:
        """Set default profile.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            True if set
        """
        if profile_id not in self.profiles:
            return False
        
        self.default_profile_id = profile_id
        
        # Save default
        default_file = self.storage_dir / ".default"
        default_file.write_text(profile_id)
        
        logger.info(f"Default profile: {self.profiles[profile_id].name}")
        return True
    
    def list_profiles(self) -> List[VoiceProfile]:
        """List all profiles.
        
        Returns:
            List of profiles
        """
        return list(self.profiles.values())
    
    def search_profiles(
        self,
        tags: Optional[List[str]] = None,
        voice_gender: Optional[VoiceGender] = None,
        voice_style: Optional[VoiceStyle] = None,
        language: Optional[str] = None
    ) -> List[VoiceProfile]:
        """Search profiles by criteria.
        
        Args:
            tags: Tags to match
            voice_gender: Gender to match
            voice_style: Style to match
            language: Language to match
            
        Returns:
            Matching profiles
        """
        results = []
        
        for profile in self.profiles.values():
            # Check tags
            if tags and not any(tag in profile.tags for tag in tags):
                continue
            
            # Check voice gender
            if voice_gender and profile.voice_characteristics.gender != voice_gender:
                continue
            
            # Check voice style
            if voice_style and profile.voice_characteristics.style != voice_style:
                continue
            
            # Check language
            if language and profile.conversation_preferences.preferred_language != language:
                continue
            
            results.append(profile)
        
        return results
    
    def export_profile(self, profile_id: str, file_path: Path) -> bool:
        """Export profile to file.
        
        Args:
            profile_id: Profile ID
            file_path: Export path
            
        Returns:
            True if exported
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return False
        
        try:
            with open(file_path, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)
            logger.info(f"Exported profile to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export profile: {e}")
            return False
    
    def import_profile(self, file_path: Path) -> Optional[VoiceProfile]:
        """Import profile from file.
        
        Args:
            file_path: Import path
            
        Returns:
            Imported profile or None
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Generate new ID to avoid conflicts
            old_id = data.get('profile_id')
            data['profile_id'] = self._generate_profile_id(data['name'])
            
            profile = VoiceProfile.from_dict(data)
            self.profiles[profile.profile_id] = profile
            self._save_profile(profile)
            
            logger.info(f"Imported profile: {profile.name}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to import profile: {e}")
            return None
    
    def get_active_config(self) -> Dict[str, Any]:
        """Get active profile configuration.
        
        Returns:
            Configuration dictionary
        """
        profile = self.active_profile
        if not profile:
            # Use default profile
            if self.default_profile_id:
                profile = self.get_profile(self.default_profile_id)
        
        if not profile:
            # Return default configuration
            return {
                'voice_id': 'alloy',
                'sample_rate': 16000,
                'language': 'en',
                'style': 'friendly'
            }
        
        # Build configuration from profile
        return {
            'voice_id': profile.voice_id or 'alloy',
            'model_variant': profile.model_variant,
            'sample_rate': profile.audio_preferences.sample_rate,
            'language': profile.conversation_preferences.preferred_language,
            'pitch': profile.voice_characteristics.pitch,
            'rate': profile.voice_characteristics.rate,
            'volume': profile.voice_characteristics.volume,
            'style': profile.voice_characteristics.style.name.lower(),
            'interaction_mode': profile.conversation_preferences.interaction_mode.name.lower(),
            'noise_suppression': profile.audio_preferences.noise_suppression,
            'echo_cancellation': profile.audio_preferences.echo_cancellation,
            'custom_vocabulary': profile.custom_vocabulary,
            'blocked_words': profile.blocked_words
        }


# Global manager instance
_manager: Optional[VoiceProfileManager] = None


def get_manager() -> VoiceProfileManager:
    """Get global profile manager.
    
    Returns:
        Profile manager instance
    """
    global _manager
    if _manager is None:
        _manager = VoiceProfileManager()
    return _manager


# Example usage
def example_usage():
    """Example of using voice profiles."""
    
    manager = get_manager()
    
    # Create profiles
    professional = manager.create_profile(
        "Professional",
        voice_characteristics=VoiceCharacteristics(
            gender=VoiceGender.NEUTRAL,
            style=VoiceStyle.PROFESSIONAL,
            pitch=0.0,
            rate=0.95
        ),
        conversation_preferences=ConversationPreferences(
            interaction_mode=InteractionMode.CONCISE,
            formality="formal",
            response_length="short"
        ),
        tags=["work", "meetings"]
    )
    
    casual = manager.create_profile(
        "Casual",
        voice_characteristics=VoiceCharacteristics(
            gender=VoiceGender.NEUTRAL,
            style=VoiceStyle.FRIENDLY,
            pitch=0.2,
            rate=1.1
        ),
        conversation_preferences=ConversationPreferences(
            interaction_mode=InteractionMode.CONVERSATIONAL,
            formality="casual",
            use_fillers=True
        ),
        tags=["personal", "relaxed"]
    )
    
    # Set active profile
    manager.set_active_profile(professional.profile_id)
    
    # Get configuration
    config = manager.get_active_config()
    print(f"Active config: {config}")
    
    # Search profiles
    work_profiles = manager.search_profiles(tags=["work"])
    print(f"Work profiles: {[p.name for p in work_profiles]}")


if __name__ == "__main__":
    example_usage()