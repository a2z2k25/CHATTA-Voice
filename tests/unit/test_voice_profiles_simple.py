#!/usr/bin/env python3
"""Simple test for voice profile management."""

import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.voice_profiles import (
    VoiceCharacteristics,
    AudioPreferences, 
    ConversationPreferences,
    VoiceProfile,
    VoiceProfileManager,
    VoiceGender,
    VoiceAge,
    VoiceStyle,
    InteractionMode
)


def test_basic_profile():
    """Test basic profile creation."""
    print("\n=== Testing Basic Profile Creation ===")
    
    # Create characteristics
    voice = VoiceCharacteristics(
        gender=VoiceGender.NEUTRAL,
        age=VoiceAge.MIDDLE,
        style=VoiceStyle.FRIENDLY
    )
    
    # Create audio prefs
    audio = AudioPreferences(
        sample_rate=16000,
        noise_suppression=True
    )
    
    # Create conversation prefs
    conv = ConversationPreferences(
        interaction_mode=InteractionMode.CONVERSATIONAL,
        formality="casual"
    )
    
    # Create profile
    import uuid
    profile = VoiceProfile(
        profile_id=str(uuid.uuid4()),
        name="Test Profile",
        voice_characteristics=voice,
        audio_preferences=audio,
        conversation_preferences=conv
    )
    
    print(f"Profile: {profile.name}")
    print(f"ID: {profile.profile_id}")
    print(f"Created: {profile.created_at}")
    print(f"✓ Profile created successfully")
    
    return profile


def test_profile_manager():
    """Test profile manager operations."""
    print("\n=== Testing Profile Manager ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create manager
        manager = VoiceProfileManager(storage_dir=tmpdir)
        
        # Create profile
        profile = manager.create_profile(
            name="Developer"
        )
        print(f"✓ Created: {profile.name}")
        
        # List profiles
        profiles = manager.list_profiles()
        print(f"✓ Listed {len(profiles)} profiles")
        
        # Get profile
        retrieved = manager.get_profile(profile.profile_id)
        assert retrieved.name == "Developer"
        print(f"✓ Retrieved: {retrieved.name}")
        
        # Update profile
        updated = manager.update_profile(
            profile.profile_id,
            name="Developer Updated"
        )
        assert updated.name == "Developer Updated"
        print("✓ Updated profile")
        
        # Set active
        result = manager.set_active_profile(profile.profile_id)
        assert result == True
        print("✓ Set active profile")
        
        # Delete
        manager.delete_profile(profile.profile_id)
        profiles = manager.list_profiles()
        assert len(profiles) == 0
        print("✓ Deleted profile")


def test_profile_persistence():
    """Test saving and loading profiles."""
    print("\n=== Testing Profile Persistence ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create profile (auto-saves)
        manager1 = VoiceProfileManager(storage_dir=tmpdir)
        profile = manager1.create_profile(name="Persistent")
        profile_id = profile.profile_id
        print("✓ Created and saved profile")
        
        # Load in new manager
        manager2 = VoiceProfileManager(storage_dir=tmpdir)
        
        # Verify it's there
        loaded = manager2.get_profile(profile_id)
        assert loaded.name == "Persistent"
        print("✓ Loaded profile successfully")


def test_default_profiles():
    """Test creating multiple profiles."""
    print("\n=== Testing Multiple Profiles ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VoiceProfileManager(storage_dir=tmpdir)
        
        # Create multiple profiles
        profile_names = ["Default", "Professional", "Casual", "Technical"]
        for name in profile_names:
            manager.create_profile(name=name)
        
        # Check they exist
        profiles = manager.list_profiles()
        names = [p.name for p in profiles]
        
        print(f"✓ Created {len(profiles)} profiles:")
        for name in names:
            print(f"  - {name}")


def test_profile_export_import():
    """Test export and import."""
    print("\n=== Testing Export/Import ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VoiceProfileManager(storage_dir=tmpdir)
        
        # Create profile
        original = manager.create_profile(
            name="Exportable"
        )
        
        # Export
        export_file = Path(tmpdir) / "export.json"
        manager.export_profile(original.profile_id, str(export_file))
        print("✓ Exported profile")
        
        # Delete original
        manager.delete_profile(original.profile_id)
        
        # Import
        imported = manager.import_profile(str(export_file))
        assert imported.name == "Exportable"
        print("✓ Imported profile")


def main():
    """Run all tests."""
    print("=" * 60)
    print("VOICE PROFILE SIMPLE TESTS")
    print("=" * 60)
    
    try:
        test_basic_profile()
        test_profile_manager()
        test_profile_persistence()
        test_default_profiles()
        test_profile_export_import()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())