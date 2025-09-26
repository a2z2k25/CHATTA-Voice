#!/usr/bin/env python3
"""Test unified configuration system."""

import sys
import os
import json
import tempfile
from pathlib import Path
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.unified_config import (
    ConfigSource,
    ConfigFormat,
    ConfigSchema,
    ConfigValue,
    ConfigLoader,
    ConfigMigrator,
    ConfigWatcher,
    UnifiedConfig,
    create_unified_config
)


def test_config_schema():
    """Test configuration schema validation."""
    print("\n=== Testing Config Schema ===")
    
    schema = ConfigSchema(
        name="test",
        version="1.0.0",
        fields={
            "host": {"type": str},
            "port": {"type": int},
            "enabled": {"type": bool}
        },
        required=["host", "port"]
    )
    
    # Valid config
    valid_config = {"host": "localhost", "port": 8080, "enabled": True}
    errors = schema.validate(valid_config)
    assert len(errors) == 0
    print("✓ Valid config passes validation")
    
    # Missing required field
    invalid_config = {"host": "localhost"}
    errors = schema.validate(invalid_config)
    assert len(errors) == 1
    assert "Required field 'port' missing" in errors[0]
    print("✓ Missing required field detected")
    
    # Type mismatch
    type_mismatch = {"host": "localhost", "port": "8080"}
    errors = schema.validate(type_mismatch)
    assert len(errors) == 1
    assert "type mismatch" in errors[0]
    print("✓ Type mismatch detected")


def test_config_loader():
    """Test configuration loading from various sources."""
    print("\n=== Testing Config Loader ===")
    
    loader = ConfigLoader()
    
    # Test JSON loading
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"test": "value", "number": 42}, f)
        json_path = Path(f.name)
    
    try:
        config = loader.load_file(json_path)
        assert config["test"] == "value"
        assert config["number"] == 42
        print("✓ JSON loading working")
    finally:
        json_path.unlink()
    
    # Test environment loading
    os.environ["CHATTA_VOICE_ENABLED"] = "true"
    os.environ["CHATTA_VOICE_PROVIDER"] = "openai"
    os.environ["CHATTA_AUDIO_SAMPLE_RATE"] = "16000"
    
    env_config = loader.load_env("CHATTA_")
    assert env_config["voice"]["enabled"] == True
    assert env_config["voice"]["provider"] == "openai"
    assert env_config["audio"]["sample"]["rate"] == 16000
    print("✓ Environment loading working")
    
    # Test value parsing
    assert loader._parse_env_value("true") == True
    assert loader._parse_env_value("false") == False
    assert loader._parse_env_value("42") == 42
    assert loader._parse_env_value("3.14") == 3.14
    assert loader._parse_env_value("text") == "text"
    print("✓ Value parsing working")


def test_config_migrator():
    """Test configuration migration."""
    print("\n=== Testing Config Migrator ===")
    
    migrator = ConfigMigrator()
    
    # Register migrations
    def migrate_1_to_2(config):
        # Rename field
        if "old_field" in config:
            config["new_field"] = config.pop("old_field")
        config["version"] = "2.0.0"
        return config
    
    def migrate_2_to_3(config):
        # Add new field
        config["added_field"] = "default_value"
        config["version"] = "3.0.0"
        return config
    
    migrator.register_migration("1.0.0", "2.0.0", migrate_1_to_2)
    migrator.register_migration("2.0.0", "3.0.0", migrate_2_to_3)
    
    # Test single migration
    config_v1 = {"version": "1.0.0", "old_field": "value"}
    config_v2 = migrator.migrate(config_v1, "1.0.0", "2.0.0")
    assert "new_field" in config_v2
    assert "old_field" not in config_v2
    print("✓ Single migration working")
    
    # Test auto migration chain
    config_v3 = migrator.auto_migrate(config_v1, "3.0.0")
    assert config_v3["version"] == "3.0.0"
    assert "new_field" in config_v3
    assert "added_field" in config_v3
    print("✓ Auto migration chain working")


def test_config_watcher():
    """Test configuration file watching."""
    print("\n=== Testing Config Watcher ===")
    
    watcher = ConfigWatcher(check_interval=0.1)
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"version": 1}, f)
        test_path = Path(f.name)
    
    try:
        changes_detected = []
        
        def on_change(path):
            changes_detected.append(path)
        
        # Start watching
        watcher.watch(test_path, on_change)
        watcher.start()
        
        # Modify file
        time.sleep(0.2)
        with open(test_path, 'w') as f:
            json.dump({"version": 2}, f)
        
        # Wait for detection
        time.sleep(0.3)
        
        assert len(changes_detected) > 0
        print("✓ File change detection working")
        
        watcher.stop()
    finally:
        test_path.unlink()


def test_unified_config():
    """Test unified configuration manager."""
    print("\n=== Testing Unified Config ===")
    
    config = UnifiedConfig("test", "1.0.0")
    
    # Load defaults
    config.load_defaults({
        "server": {
            "host": "localhost",
            "port": 8080
        },
        "debug": False
    })
    
    assert config.get("server.host") == "localhost"
    assert config.get("server.port") == 8080
    assert config.get("debug") == False
    print("✓ Default loading working")
    
    # Test override
    config.set_override("server.port", 9090)
    assert config.get("server.port") == 9090
    print("✓ Override working")
    
    # Test runtime
    config.set_runtime("debug", True)
    assert config.get("debug") == True
    print("✓ Runtime config working")
    
    # Test get with source
    value_info = config.get_with_source("server.host")
    assert value_info.value == "localhost"
    assert value_info.source == ConfigSource.DEFAULT
    print("✓ Get with source working")
    
    # Test export
    exported = config.export(ConfigFormat.JSON)
    exported_dict = json.loads(exported)
    assert exported_dict["server"]["port"] == 9090
    print("✓ Export working")


def test_layer_priority():
    """Test configuration layer priority."""
    print("\n=== Testing Layer Priority ===")
    
    config = UnifiedConfig("test")
    
    # Set same key in different layers
    config.layers[ConfigSource.DEFAULT] = {"key": "default"}
    config.layers[ConfigSource.FILE] = {"key": "file"}
    config.layers[ConfigSource.ENVIRONMENT] = {"key": "env"}
    config.layers[ConfigSource.OVERRIDE] = {"key": "override"}
    config.layers[ConfigSource.RUNTIME] = {"key": "runtime"}
    
    # Runtime should win
    assert config.get("key") == "runtime"
    print("✓ Runtime has highest priority")
    
    # Remove runtime, override should win
    del config.layers[ConfigSource.RUNTIME]["key"]
    config._invalidate_cache()
    assert config.get("key") == "override"
    print("✓ Override has second priority")
    
    # Remove override, environment should win
    del config.layers[ConfigSource.OVERRIDE]["key"]
    config._invalidate_cache()
    assert config.get("key") == "env"
    print("✓ Environment has third priority")


def test_deep_merge():
    """Test deep merging of configurations."""
    print("\n=== Testing Deep Merge ===")
    
    config = UnifiedConfig("test")
    
    config.layers[ConfigSource.DEFAULT] = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "options": {
                "ssl": False,
                "timeout": 30
            }
        }
    }
    
    config.layers[ConfigSource.FILE] = {
        "database": {
            "port": 3306,
            "options": {
                "ssl": True
            }
        }
    }
    
    merged = config._get_merged_config()
    assert merged["database"]["host"] == "localhost"  # From default
    assert merged["database"]["port"] == 3306  # Overridden by file
    assert merged["database"]["options"]["ssl"] == True  # Overridden
    assert merged["database"]["options"]["timeout"] == 30  # From default
    print("✓ Deep merge preserves nested values")


def test_schema_validation():
    """Test schema validation with unified config."""
    print("\n=== Testing Schema Validation ===")
    
    schema = ConfigSchema(
        name="voice",
        version="1.0.0",
        fields={
            "voice.provider": {"type": str},
            "voice.enabled": {"type": bool},
            "audio.sample_rate": {"type": int}
        },
        required=["voice.provider"]
    )
    
    config = UnifiedConfig("test")
    config.load_defaults({
        "voice": {
            "provider": "openai",
            "enabled": True
        },
        "audio": {
            "sample_rate": 16000
        }
    })
    
    errors = config.validate(schema)
    assert len(errors) == 0
    print("✓ Valid configuration passes schema")
    
    # Test with missing required
    config2 = UnifiedConfig("test")
    config2.load_defaults({"voice": {"enabled": True}})
    errors2 = config2.validate(schema)
    assert len(errors2) > 0
    print("✓ Invalid configuration detected")


def test_convenience_functions():
    """Test convenience functions."""
    print("\n=== Testing Convenience Functions ===")
    
    config = create_unified_config("test")
    
    # Should have defaults loaded
    assert config.get("voice.enabled") == True
    assert config.get("audio.channels") == 1
    print("✓ create_unified_config working")
    
    # Cleanup
    config.cleanup()
    print("✓ Cleanup working")


def main():
    """Run all tests."""
    print("=" * 60)
    print("UNIFIED CONFIGURATION TESTS")
    print("=" * 60)
    
    test_config_schema()
    test_config_loader()
    test_config_migrator()
    test_config_watcher()
    test_unified_config()
    test_layer_priority()
    test_deep_merge()
    test_schema_validation()
    test_convenience_functions()
    
    print("\n" + "=" * 60)
    print("✓ All unified configuration tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()