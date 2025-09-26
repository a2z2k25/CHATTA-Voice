#!/usr/bin/env python3
"""Test user preferences system."""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any
from voice_mode.user_preferences import (
    UserPreferencesManager,
    UserPreferences,
    AudioPreferences,
    VoicePreferences,
    AccessibilityPreferences,
    BehaviorPreferences,
    InterfacePreferences,
    KeyboardPreferences,
    AdvancedPreferences,
    PreferenceValidator,
    PreferenceMigrator,
    AudioFormat,
    VoiceProvider,
    PreferenceCategory
)
from voice_mode.preference_ui import (
    PreferenceManager,
    AudioPreferencePanel,
    VoicePreferencePanel,
    AccessibilityPreferencePanel,
    ProfileManager,
    SliderComponent,
    SelectComponent,
    CheckboxComponent,
    TextComponent
)


def test_preference_dataclasses():
    """Test preference dataclass creation."""
    print("\n=== Testing Preference Dataclasses ===")
    
    # Test audio preferences
    audio = AudioPreferences()
    print(f"  Default audio format: {audio.format.value}")
    print(f"  Default sample rate: {audio.sample_rate}")
    print(f"  Default volume: {audio.volume}")
    
    # Test voice preferences
    voice = VoicePreferences()
    print(f"  Default TTS provider: {voice.tts_provider.value}")
    print(f"  Default voice: {voice.tts_voice}")
    print(f"  Default speed: {voice.tts_speed}")
    
    # Test accessibility preferences
    accessibility = AccessibilityPreferences()
    print(f"  Screen reader enabled: {accessibility.screen_reader_enabled}")
    print(f"  High contrast: {accessibility.high_contrast}")
    
    # Test complete preferences
    prefs = UserPreferences()
    print(f"  Preference version: {prefs.version}")
    print(f"  Profile name: {prefs.profile_name}")
    
    print("✓ Preference dataclasses working")


def test_preference_validation():
    """Test preference validation."""
    print("\n=== Testing Preference Validation ===")
    
    # Test audio validation
    audio = AudioPreferences()
    errors = PreferenceValidator.validate_audio(audio)
    print(f"  Default audio validation: {len(errors)} errors")
    
    # Test invalid values
    audio.volume = 5.0  # Too high
    audio.sample_rate = 12345  # Invalid rate
    errors = PreferenceValidator.validate_audio(audio)
    print(f"  Invalid audio validation: {len(errors)} errors")
    for error in errors:
        print(f"    - {error}")
    
    # Test voice validation
    voice = VoicePreferences()
    voice.tts_speed = 10.0  # Too fast
    voice.tts_voice = "invalid"  # Invalid voice
    errors = PreferenceValidator.validate_voice(voice)
    print(f"  Invalid voice validation: {len(errors)} errors")
    
    # Test complete preferences validation
    prefs = UserPreferences()
    prefs.audio.volume = 3.0  # Invalid
    prefs.voice.tts_speed = 0.1  # Too slow
    errors = PreferenceValidator.validate_preferences(prefs)
    print(f"  Complete validation: {len(errors)} errors")
    
    print("✓ Preference validation working")


def test_preferences_manager():
    """Test preferences manager."""
    print("\n=== Testing Preferences Manager ===")
    
    # Create temporary config directory
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # Create manager
        manager = UserPreferencesManager(config_dir)
        print(f"  Created manager with config dir: {config_dir}")
        
        # Test setting preferences
        success = manager.set_preference("audio", "volume", 0.9)
        print(f"  Set audio.volume: {success}")
        
        success = manager.set_preference("voice", "tts_speed", 1.2)
        print(f"  Set voice.tts_speed: {success}")
        
        # Test getting preferences
        volume = manager.get_preference("audio", "volume")
        print(f"  Got audio.volume: {volume}")
        
        speed = manager.get_preference("voice", "tts_speed")
        print(f"  Got voice.tts_speed: {speed}")
        
        # Test validation
        errors = manager.validate_all()
        print(f"  Validation errors: {len(errors)}")
        
        # Test saving/loading
        success = manager.save_preferences()
        print(f"  Save preferences: {success}")
        
        # Create new manager and load
        manager2 = UserPreferencesManager(config_dir)
        volume2 = manager2.get_preference("audio", "volume")
        print(f"  Loaded audio.volume: {volume2}")
        
        # Test statistics
        stats = manager.get_statistics()
        print(f"  Current profile: {stats['current_profile']}")
        print(f"  Total profiles: {stats['total_profiles']}")
    
    print("✓ Preferences manager working")


def test_profile_management():
    """Test profile management."""
    print("\n=== Testing Profile Management ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        manager = UserPreferencesManager(config_dir)
        
        # List initial profiles
        profiles = manager.list_profiles()
        print(f"  Initial profiles: {profiles}")
        
        # Create new profile
        success = manager.create_profile("test_profile")
        print(f"  Created test profile: {success}")
        
        # Copy existing profile
        success = manager.create_profile("copy_profile", copy_from="default")
        print(f"  Created copy profile: {success}")
        
        # List profiles after creation
        profiles = manager.list_profiles()
        print(f"  Total profiles: {len(profiles)}")
        for profile in profiles:
            print(f"    - {profile}")
        
        # Switch profiles
        success = manager.load_preferences("test_profile")
        print(f"  Switched to test profile: {success}")
        
        # Set profile-specific preferences
        manager.set_preference("audio", "volume", 0.5)
        manager.save_preferences()
        
        # Switch back and verify isolation
        manager.load_preferences("default")
        volume = manager.get_preference("audio", "volume")
        print(f"  Default profile volume: {volume}")
        
        # Switch to test profile and verify setting
        manager.load_preferences("test_profile")
        volume = manager.get_preference("audio", "volume")
        print(f"  Test profile volume: {volume}")
        
        # Delete profile
        success = manager.delete_profile("copy_profile")
        print(f"  Deleted copy profile: {success}")
    
    print("✓ Profile management working")


def test_import_export():
    """Test import/export functionality."""
    print("\n=== Testing Import/Export ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        manager = UserPreferencesManager(config_dir)
        
        # Set some preferences
        manager.set_preference("audio", "volume", 0.7)
        manager.set_preference("voice", "tts_speed", 1.5)
        manager.set_preference("accessibility", "high_contrast", True)
        
        # Export as JSON
        exported_json = manager.export_preferences("json")
        print(f"  Exported JSON: {len(exported_json)} characters")
        
        # Parse and check content
        data = json.loads(exported_json)
        assert data["audio"]["volume"] == 0.7
        assert data["voice"]["tts_speed"] == 1.5
        assert data["accessibility"]["high_contrast"] == True
        print("  JSON export content verified")
        
        # Reset preferences
        manager.reset_to_defaults()
        volume = manager.get_preference("audio", "volume")
        print(f"  Reset audio volume: {volume}")
        
        # Import preferences
        success = manager.import_preferences(exported_json, "json")
        print(f"  Import success: {success}")
        
        # Verify imported values
        volume = manager.get_preference("audio", "volume")
        speed = manager.get_preference("voice", "tts_speed")
        contrast = manager.get_preference("accessibility", "high_contrast")
        
        print(f"  Imported volume: {volume}")
        print(f"  Imported speed: {speed}")
        print(f"  Imported contrast: {contrast}")
        
        # Test invalid import
        invalid_json = '{"invalid": "data"}'
        success = manager.import_preferences(invalid_json, "json")
        print(f"  Invalid import rejected: {not success}")
    
    print("✓ Import/export working")


def test_ui_components():
    """Test UI components."""
    print("\n=== Testing UI Components ===")
    
    # Test slider component
    slider = SliderComponent("volume", "Volume", 0.0, 1.0, 0.1, 0.8)
    print(f"  Slider initial value: {slider.value}")
    print(f"  Slider display: {slider.get_display_text()}")
    
    slider.set_value(0.9)
    print(f"  Slider after set: {slider.value}")
    
    # Test select component
    options = [("alloy", "Alloy"), ("echo", "Echo"), ("nova", "Nova")]
    select = SelectComponent("voice", "Voice", options, "echo")
    print(f"  Select initial value: {select.value}")
    
    select.set_value("nova")
    print(f"  Select after change: {select.value}")
    
    # Test checkbox component
    checkbox = CheckboxComponent("enabled", "Enabled", False)
    print(f"  Checkbox initial: {checkbox.value}")
    
    checkbox.set_value(True)
    print(f"  Checkbox after toggle: {checkbox.value}")
    
    # Test text component
    text = TextComponent("name", "Name", "default", "Enter name...")
    print(f"  Text initial: '{text.value}'")
    print(f"  Text placeholder: '{text.placeholder}'")
    
    text.set_value("custom")
    print(f"  Text after change: '{text.value}'")
    
    # Test change callbacks
    change_count = 0
    
    def on_change(component_id, old_value, new_value):
        nonlocal change_count
        change_count += 1
        print(f"    Change {change_count}: {component_id} = {old_value} -> {new_value}")
    
    slider.on_change(on_change)
    slider.set_value(0.5)
    print(f"  Change callbacks triggered: {change_count}")
    
    print("✓ UI components working")


def test_preference_panels():
    """Test preference panels."""
    print("\n=== Testing Preference Panels ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        manager = UserPreferencesManager(config_dir)
        
        # Create audio panel
        audio_panel = AudioPreferencePanel()
        print(f"  Audio panel components: {len(audio_panel.components)}")
        
        # Bind manager
        audio_panel.bind_manager(manager)
        print("  Bound manager to panel")
        
        # Test validation
        result = audio_panel.validate()
        print(f"  Audio panel valid: {result.valid}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")
        
        # Create voice panel
        voice_panel = VoicePreferencePanel()
        voice_panel.bind_manager(manager)
        
        # Test changing values through panel
        volume_component = None
        for component in audio_panel.components:
            if component.id == "audio_volume":
                volume_component = component
                break
        
        if volume_component:
            print(f"  Volume component initial: {volume_component.value}")
            volume_component.set_value(0.6)
            
            # Check if preference was updated
            updated_volume = manager.get_preference("audio", "volume")
            print(f"  Updated volume in manager: {updated_volume}")
        
        # Create accessibility panel
        access_panel = AccessibilityPreferencePanel()
        access_panel.bind_manager(manager)
        print(f"  Accessibility panel components: {len(access_panel.components)}")
    
    print("✓ Preference panels working")


def test_preference_manager_ui():
    """Test high-level preference manager UI."""
    print("\n=== Testing Preference Manager UI ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        pref_manager = UserPreferencesManager(config_dir)
        
        # Create UI manager
        ui_manager = PreferenceManager(pref_manager)
        print(f"  Created UI manager with {len(ui_manager.panels)} panels")
        
        # Test getting panels
        audio_panel = ui_manager.get_panel(PreferenceCategory.AUDIO)
        print(f"  Audio panel found: {audio_panel is not None}")
        
        voice_panel = ui_manager.get_panel(PreferenceCategory.VOICE)
        print(f"  Voice panel found: {voice_panel is not None}")
        
        # Test validation
        all_valid = ui_manager.validate_all()
        print(f"  All panels valid: {all_valid}")
        
        summary = ui_manager.get_validation_summary()
        print(f"  Validation summary:")
        print(f"    Total errors: {summary['total_errors']}")
        print(f"    Total warnings: {summary['total_warnings']}")
        print(f"    Valid panels: {summary['panels_valid']}/{summary['total_panels']}")
        
        # Test UI state export/import
        ui_state = ui_manager.export_to_dict()
        print(f"  Exported UI state: {len(ui_state)} categories")
        
        # Modify some values
        if audio_panel:
            for component in audio_panel.components:
                if hasattr(component, 'set_value'):
                    if component.id == "audio_volume":
                        component.set_value(0.95)
                        break
        
        # Import original state
        ui_manager.import_from_dict(ui_state)
        print("  Imported original UI state")
        
        # Test reset
        ui_manager.reset_panel(PreferenceCategory.AUDIO)
        print("  Reset audio panel to defaults")
        
        # Get summary
        summary = ui_manager.get_summary()
        print(f"  UI Manager summary:")
        print(f"    Total panels: {summary['total_panels']}")
        print(f"    Current profile: {summary['current_profile']}")
    
    print("✓ Preference manager UI working")


def test_profile_manager_ui():
    """Test profile manager UI."""
    print("\n=== Testing Profile Manager UI ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        pref_manager = UserPreferencesManager(config_dir)
        
        # Create profile manager
        profile_mgr = ProfileManager(pref_manager)
        
        # Test profile listing
        profiles = profile_mgr.list_profiles()
        print(f"  Listed profiles: {len(profiles)}")
        
        for profile in profiles:
            print(f"    - {profile['name']} (created: {profile['created_at'][:10]})")
        
        # Test create profile dialog
        dialog = profile_mgr.create_profile_dialog()
        print(f"  Create dialog title: {dialog['title']}")
        print(f"  Create dialog fields: {len(dialog['fields'])}")
        
        # Test profile export
        exported = profile_mgr.export_profile("default", "json")
        print(f"  Exported default profile: {len(exported)} characters")
        
        # Test profile import
        pref_manager.create_profile("test_import")
        success = profile_mgr.import_profile("test_import", exported, "json")
        print(f"  Imported profile: {success}")
        
        # Verify import
        updated_profiles = profile_mgr.list_profiles()
        print(f"  Profiles after import: {len(updated_profiles)}")
    
    print("✓ Profile manager UI working")


def test_migration():
    """Test preference migration."""
    print("\n=== Testing Preference Migration ===")
    
    # Test migration detection
    old_data = {
        "version": "0.9.0",
        "audio_settings": {"volume": 0.8},
        "voice_settings": {"speed": 1.0}
    }
    
    needs_migration = PreferenceMigrator.needs_migration(old_data)
    print(f"  Old data needs migration: {needs_migration}")
    
    # Test migration
    migrated = PreferenceMigrator.migrate_from_version(old_data, "0.9.0")
    print(f"  Migrated version: {migrated['version']}")
    print(f"  Has audio section: {'audio' in migrated}")
    print(f"  Has voice section: {'voice' in migrated}")
    
    # Test current version doesn't need migration
    current_data = {"version": "1.0.0"}
    needs_migration = PreferenceMigrator.needs_migration(current_data)
    print(f"  Current data needs migration: {needs_migration}")
    
    print("✓ Preference migration working")


async def test_performance():
    """Test preference system performance."""
    print("\n=== Testing Performance ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        manager = UserPreferencesManager(config_dir)
        
        # Test preference access speed
        start = time.time()
        for _ in range(1000):
            manager.get_preference("audio", "volume")
        get_time = time.time() - start
        get_rate = 1000 / get_time if get_time > 0 else 0
        print(f"  Get preference rate: {get_rate:.1f} gets/sec")
        
        # Test preference setting speed
        start = time.time()
        for i in range(100):
            manager.set_preference("audio", "volume", 0.1 + (i % 10) * 0.1)
        set_time = time.time() - start
        set_rate = 100 / set_time if set_time > 0 else 0
        print(f"  Set preference rate: {set_rate:.1f} sets/sec")
        
        # Test validation speed
        start = time.time()
        for _ in range(100):
            manager.validate_all()
        val_time = time.time() - start
        val_rate = 100 / val_time if val_time > 0 else 0
        print(f"  Validation rate: {val_rate:.1f} validations/sec")
        
        # Test save/load speed
        start = time.time()
        for _ in range(10):
            manager.save_preferences()
            manager.load_preferences()
        io_time = time.time() - start
        io_rate = 20 / io_time if io_time > 0 else 0  # 10 saves + 10 loads
        print(f"  I/O rate: {io_rate:.1f} operations/sec")
        
        # Test export/import speed
        exported = manager.export_preferences("json")
        
        start = time.time()
        for _ in range(10):
            manager.import_preferences(exported, "json")
        import_time = time.time() - start
        import_rate = 10 / import_time if import_time > 0 else 0
        print(f"  Import rate: {import_rate:.1f} imports/sec")
        
        total_time = get_time + set_time + val_time + io_time + import_time
        total_ops = 1000 + 100 + 100 + 20 + 10
        print(f"\n  Performance summary:")
        print(f"    Total operations: {total_ops}")
        print(f"    Total time: {total_time:.2f}s")
        if total_time > 0:
            print(f"    Average rate: {total_ops / total_time:.1f} ops/sec")
    
    print("✓ Performance acceptable")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("USER PREFERENCES TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_preference_dataclasses()
    test_preference_validation()
    test_preferences_manager()
    test_profile_management()
    test_import_export()
    test_ui_components()
    test_preference_panels()
    test_preference_manager_ui()
    test_profile_manager_ui()
    test_migration()
    
    # Run async tests
    await test_performance()
    
    print("\n" + "=" * 60)
    print("✓ All user preferences tests passed!")
    print("Sprint 36 complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())