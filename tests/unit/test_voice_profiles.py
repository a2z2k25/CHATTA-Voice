#!/usr/bin/env python3
"""Test voice profile management."""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.voice_profiles import (
    VoiceCharacteristics,
    AudioPreferences,
    ConversationPreferences,
    VoiceProfile,
    VoiceProfileManager
)


def test_voice_characteristics():
    """Test voice characteristics."""
    print("\n=== Testing Voice Characteristics ===")
    
    from voice_mode.voice_profiles import VoiceGender, VoiceAge, VoiceStyle
    
    chars = VoiceCharacteristics(
        gender=VoiceGender.NEUTRAL,
        age=VoiceAge.MIDDLE,
        style=VoiceStyle.FRIENDLY,
        pitch=0.5,
        rate=1.2,
        volume=0.9,
        timbre="warm",
        accent="neutral",
        emotion="calm"
    )
    
    print(f"Gender: {chars.gender.value}")
    print(f"Pitch: {chars.pitch}")
    print(f"Rate: {chars.rate}")
    print(f"Volume: {chars.volume}")
    print(f"Emotion: {chars.emotion}")
    print(f"✓ Voice characteristics created")


def test_audio_preferences():
    """Test audio preferences."""
    print("\n=== Testing Audio Preferences ===")
    
    prefs = AudioPreferences(
        sample_rate=48000,
        noise_suppression=True,
        echo_cancellation=True,
        auto_gain_control=False,
        silence_threshold=0.05
    )
    
    print(f"Sample Rate: {prefs.sample_rate} Hz")
    print(f"Noise Suppression: {prefs.noise_suppression}")
    print(f"Echo Cancellation: {prefs.echo_cancellation}")
    print(f"AGC: {prefs.auto_gain_control}")
    print(f"Silence Threshold: {prefs.silence_threshold}")
    print(f"✓ Audio preferences created")


def test_conversation_preferences():
    """Test conversation preferences."""
    print("\n=== Testing Conversation Preferences ===")
    
    from voice_mode.voice_profiles import InteractionMode
    
    conv = ConversationPreferences(
        interaction_mode=InteractionMode.CONVERSATIONAL,
        response_length="medium",
        formality="casual",
        use_fillers=False,
        allow_interruptions=True,
        confirmation_style="brief",
        error_handling="friendly",
        patience_level=1.0,
        preferred_language="en"
    )
    
    print(f"Mode: {conv.interaction_mode.value}")
    print(f"Formality: {conv.formality}")
    print(f"Response Length: {conv.response_length}")
    print(f"Allow Interruptions: {conv.allow_interruptions}")
    print(f"✓ Conversation preferences created")


def test_profile_creation():
    """Test profile creation."""
    print("\n=== Testing Profile Creation ===")
    
    profile = VoiceProfile(
        profile_id="test-001",
        name="Test Profile",
        description="A test voice profile",
        voice_characteristics=VoiceCharacteristics(),
        audio_preferences=AudioPreferences(),
        conversation_preferences=ConversationPreferences(),
        is_active=True,
        tags=["test", "demo"]
    )
    
    print(f"Profile ID: {profile.profile_id}")
    print(f"Name: {profile.name}")
    print(f"Active: {profile.is_active}")
    print(f"Tags: {', '.join(profile.tags)}")
    print(f"Created: {profile.created_at}")
    print(f"✓ Profile created successfully")
    
    return profile


def test_profile_serialization():
    """Test profile serialization."""
    print("\n=== Testing Profile Serialization ===")
    
    profile = test_profile_creation()
    
    # Test to_dict
    data = profile.to_dict()
    assert isinstance(data, dict)
    assert data["profile_id"] == "test-001"
    assert data["name"] == "Test Profile"
    print("✓ to_dict successful")
    
    # Test from_dict
    restored = VoiceProfile.from_dict(data)
    assert restored.profile_id == profile.profile_id
    assert restored.name == profile.name
    assert restored.is_active == profile.is_active
    print("✓ from_dict successful")
    
    # Test JSON round-trip
    json_str = json.dumps(data)
    parsed = json.loads(json_str)
    final = VoiceProfile.from_dict(parsed)
    assert final.profile_id == profile.profile_id
    print("✓ JSON serialization successful")


def test_profile_manager():
    """Test profile manager."""
    print("\n=== Testing Profile Manager ===")
    
    # Use temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VoiceProfileManager(profile_dir=tmpdir)
        
        # Test empty manager
        assert len(manager.profiles) == 0
        print("✓ Manager initialized empty")
        
        # Create profiles
        profile1 = manager.create_profile(
            name="Developer",
            description="Profile for coding sessions"
        )
        print(f"✓ Created profile: {profile1.name}")
        
        profile2 = manager.create_profile(
            name="Casual",
            description="Profile for casual conversation"
        )
        print(f"✓ Created profile: {profile2.name}")
        
        # Test listing
        profiles = manager.list_profiles()
        assert len(profiles) == 2
        print(f"✓ Listed {len(profiles)} profiles")
        
        # Test get
        retrieved = manager.get_profile(profile1.profile_id)
        assert retrieved.name == "Developer"
        print("✓ Retrieved profile by ID")
        
        # Test update
        manager.update_profile(
            profile1.profile_id,
            description="Updated description"
        )
        updated = manager.get_profile(profile1.profile_id)
        assert updated.description == "Updated description"
        print("✓ Updated profile")
        
        # Test activation
        manager.set_active_profile(profile2.profile_id)
        active = manager.get_active_profile()
        assert active.profile_id == profile2.profile_id
        print("✓ Set active profile")
        
        # Test delete
        manager.delete_profile(profile1.profile_id)
        assert len(manager.profiles) == 1
        print("✓ Deleted profile")


def test_profile_persistence():
    """Test profile persistence."""
    print("\n=== Testing Profile Persistence ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create and save
        manager1 = VoiceProfileManager(profile_dir=tmpdir)
        profile = manager1.create_profile(
            name="Persistent",
            description="Test persistence"
        )
        profile_id = profile.profile_id
        manager1.save_profiles()
        print("✓ Saved profiles")
        
        # Load in new manager
        manager2 = VoiceProfileManager(profile_dir=tmpdir)
        manager2.load_profiles()
        
        # Verify
        loaded = manager2.get_profile(profile_id)
        assert loaded.name == "Persistent"
        assert loaded.description == "Test persistence"
        print("✓ Loaded profiles successfully")


def test_profile_search():
    """Test profile search."""
    print("\n=== Testing Profile Search ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VoiceProfileManager(profile_dir=tmpdir)
        
        # Create test profiles
        manager.create_profile(
            name="Work",
            tags=["professional", "formal"]
        )
        manager.create_profile(
            name="Gaming",
            tags=["casual", "fun"]
        )
        manager.create_profile(
            name="Study",
            tags=["focused", "quiet"]
        )
        
        # Search by name
        results = manager.search_profiles(name_contains="work")
        assert len(results) == 1
        assert results[0].name == "Work"
        print("✓ Search by name")
        
        # Search by tag
        results = manager.search_profiles(tags=["casual"])
        assert len(results) == 1
        assert results[0].name == "Gaming"
        print("✓ Search by tag")
        
        # Search active only
        manager.set_active_profile(manager.profiles["Study"].profile_id)
        results = manager.search_profiles(active_only=True)
        assert len(results) == 1
        assert results[0].name == "Study"
        print("✓ Search active only")


def test_profile_export_import():
    """Test profile export/import."""
    print("\n=== Testing Profile Export/Import ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VoiceProfileManager(profile_dir=tmpdir)
        
        # Create profile
        original = manager.create_profile(
            name="Exportable",
            description="Test export/import",
            tags=["export", "test"]
        )
        
        # Export
        export_file = Path(tmpdir) / "export.json"
        manager.export_profile(original.profile_id, str(export_file))
        assert export_file.exists()
        print("✓ Exported profile")
        
        # Delete original
        manager.delete_profile(original.profile_id)
        
        # Import
        imported = manager.import_profile(str(export_file))
        assert imported.name == "Exportable"
        assert imported.description == "Test export/import"
        assert "export" in imported.tags
        print("✓ Imported profile")


def test_profile_defaults():
    """Test default profile creation."""
    print("\n=== Testing Default Profiles ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VoiceProfileManager(profile_dir=tmpdir)
        
        # Create defaults
        manager.create_default_profiles()
        
        # Check they exist
        profiles = manager.list_profiles()
        names = [p.name for p in profiles]
        
        assert "Default" in names
        assert "Professional" in names
        assert "Casual" in names
        assert "Technical" in names
        
        print(f"✓ Created {len(profiles)} default profiles")
        
        # Verify characteristics
        prof = next(p for p in profiles if p.name == "Professional")
        assert prof.conversation_preferences.formality_level == "formal"
        print("✓ Default profiles configured correctly")


def test_profile_validation():
    """Test profile validation."""
    print("\n=== Testing Profile Validation ===")
    
    # Test invalid pitch
    try:
        VoiceCharacteristics(pitch=2.0)  # > 1.5
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ Invalid pitch rejected")
    
    # Test invalid speed
    try:
        VoiceCharacteristics(speed=0.2)  # < 0.25
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ Invalid speed rejected")
    
    # Test invalid volume
    try:
        VoiceCharacteristics(volume=1.5)  # > 1.0
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ Invalid volume rejected")
    
    # Test invalid sample rate
    try:
        AudioPreferences(sample_rate=5000)  # Not in valid rates
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ Invalid sample rate rejected")


def main():
    """Run all tests."""
    print("=" * 60)
    print("VOICE PROFILE TESTS")
    print("=" * 60)
    
    test_voice_characteristics()
    test_audio_preferences()
    test_conversation_preferences()
    test_profile_creation()
    test_profile_serialization()
    test_profile_manager()
    test_profile_persistence()
    test_profile_search()
    test_profile_export_import()
    test_profile_defaults()
    test_profile_validation()
    
    print("\n" + "=" * 60)
    print("✓ All voice profile tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()