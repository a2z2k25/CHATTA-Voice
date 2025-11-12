# PTT Configuration Design
Date: November 9, 2025
Sprint: 1.6

## Configuration Schema

### Environment Variables

```bash
# Core PTT Settings
CHATTA_PTT_ENABLED=false                    # Enable PTT globally
CHATTA_PTT_KEY_COMBO="down+right"          # Default key combination
CHATTA_PTT_MODE="hold"                     # hold | toggle | hybrid
CHATTA_PTT_TIMEOUT=120.0                   # Max recording duration (seconds)

# Behavior Settings
CHATTA_PTT_AUTO_ENABLE=false               # Auto-enable for local transport
CHATTA_PTT_REQUIRE_BOTH_KEYS=true          # Require all keys pressed together
CHATTA_PTT_RELEASE_DELAY=0.1               # Delay before stopping (debounce)
CHATTA_PTT_MIN_DURATION=0.5                # Minimum recording duration

# Audio Feedback
CHATTA_PTT_AUDIO_FEEDBACK=true             # Play PTT-specific sounds
CHATTA_PTT_FEEDBACK_VOLUME=0.7             # Volume for PTT sounds (0.0-1.0)
CHATTA_PTT_VISUAL_FEEDBACK=true            # Show visual indicators
CHATTA_PTT_HAPTIC_FEEDBACK=false           # Future: Haptic feedback

# Advanced Settings
CHATTA_PTT_CANCEL_KEY="escape"             # Key to cancel recording
CHATTA_PTT_BUFFER_PRE_RECORDING=false      # Buffer audio before key press
CHATTA_PTT_BUFFER_DURATION=0.5             # Pre-recording buffer duration
CHATTA_PTT_KEY_REPEAT_IGNORE=true          # Ignore key repeat events

# Platform-Specific
CHATTA_PTT_MACOS_ACCESSIBILITY_CHECK=true  # Check permissions on macOS
CHATTA_PTT_WINDOWS_HOOK_TYPE="low_level"   # low_level | high_level
CHATTA_PTT_LINUX_INPUT_METHOD="x11"        # x11 | wayland | auto

# Debug & Development
CHATTA_PTT_DEBUG=false                     # Enable debug logging
CHATTA_PTT_LOG_KEYS=false                  # Log key events (debug only)
CHATTA_PTT_SIMULATE=false                  # Simulate PTT without keyboard
```

### Configuration File Format

#### ~/.chatta/ptt.yaml
```yaml
# CHATTA Push-to-Talk Configuration
version: "1.0"

# Core settings
enabled: false
default_mode: hold

# Key bindings (multiple configs allowed)
key_bindings:
  default:
    keys: ["down", "right"]
    require_all: true

  alternate:
    keys: ["ctrl", "space"]
    require_all: true

  accessible:
    keys: ["f13"]  # Single key for accessibility
    require_all: false

# Mode configurations
modes:
  hold:
    description: "Record while keys are held"
    auto_stop_on_release: true
    max_duration: 120.0
    min_duration: 0.5

  toggle:
    description: "Press to start/stop recording"
    auto_stop_on_release: false
    max_duration: 300.0
    toggle_indicator: true

  hybrid:
    description: "Hold with automatic stop on silence"
    auto_stop_on_release: true
    silence_stop_enabled: true
    silence_threshold: 1.0

# Audio feedback profiles
audio_profiles:
  default:
    start_sound: "ptt_start.wav"
    end_sound: "ptt_end.wav"
    ready_sound: "ptt_ready.wav"
    volume: 0.7

  quiet:
    volume: 0.3

  silent:
    enabled: false

# Platform overrides
platforms:
  darwin:
    check_accessibility: true
    prompt_for_permissions: true

  win32:
    use_low_level_hooks: true

  linux:
    prefer_x11: true
    fallback_to_polling: false

# User preferences
preferences:
  show_tutorial_on_first_use: true
  remember_last_mode: true
  auto_switch_transport: true
  show_key_hints: true
```

### JSON Alternative

#### ~/.chatta/ptt.json
```json
{
  "version": "1.0",
  "enabled": false,
  "keyBindings": {
    "default": {
      "keys": ["down", "right"],
      "requireAll": true
    }
  },
  "modes": {
    "current": "hold",
    "configurations": {
      "hold": {
        "autoStopOnRelease": true,
        "maxDuration": 120.0
      }
    }
  }
}
```

## Configuration Hierarchy

```python
class PTTConfigManager:
    """Manage PTT configuration with proper precedence"""

    def __init__(self):
        self.config_hierarchy = [
            # Highest priority (overrides everything)
            self.load_runtime_overrides,      # Programmatic overrides
            self.load_cli_arguments,          # Command-line args
            self.load_env_variables,          # Environment variables

            # User configuration
            self.load_project_config,         # ./.chatta/ptt.yaml
            self.load_user_config,           # ~/.chatta/ptt.yaml

            # System defaults (lowest priority)
            self.load_system_config,         # /etc/chatta/ptt.yaml
            self.load_defaults               # Hardcoded defaults
        ]

    def get_config(self, key: str, default=None):
        """Get config value with hierarchy"""
        for loader in self.config_hierarchy:
            value = loader(key)
            if value is not None:
                return value
        return default
```

### Priority Order (Highest to Lowest)
1. **Runtime Override** - Set programmatically
2. **CLI Arguments** - `--ptt-keys "ctrl+space"`
3. **Environment Variables** - `CHATTA_PTT_KEY_COMBO`
4. **Project Config** - `./.chatta/ptt.yaml`
5. **User Config** - `~/.chatta/ptt.yaml`
6. **System Config** - `/etc/chatta/ptt.yaml`
7. **Defaults** - Hardcoded in source

## Default Values

```python
# defaults.py
PTT_DEFAULTS = {
    # Core
    "enabled": False,
    "key_combo": "down+right",
    "mode": "hold",
    "timeout": 120.0,

    # Behavior
    "auto_enable": False,
    "require_both_keys": True,
    "release_delay": 0.1,
    "min_duration": 0.5,

    # Audio
    "audio_feedback": True,
    "feedback_volume": 0.7,
    "visual_feedback": True,

    # Keys
    "cancel_key": "escape",
    "modifier_keys": ["ctrl", "alt", "shift", "cmd"],

    # Platform
    "macos_check_accessibility": True,
    "windows_hook_type": "low_level",
    "linux_input_method": "auto"
}
```

## Key Combination Format

### Supported Formats
```python
KEY_COMBO_FORMATS = {
    # Standard format
    "down+right": ["down", "right"],
    "ctrl+space": ["ctrl", "space"],

    # With modifiers
    "cmd+shift+p": ["cmd", "shift", "p"],
    "ctrl+alt+delete": ["ctrl", "alt", "delete"],

    # Single key
    "f13": ["f13"],
    "space": ["space"],

    # Arrow keys
    "up+down": ["up", "down"],
    "left+right": ["left", "right"],

    # Function keys
    "f1": ["f1"],
    "shift+f10": ["shift", "f10"],

    # Special keys
    "escape": ["escape"],
    "enter": ["enter"],
    "tab": ["tab"]
}
```

### Key Validation
```python
def validate_key_combo(combo: str) -> tuple[bool, str]:
    """Validate key combination string"""

    # Parse combo
    keys = combo.lower().split("+")

    # Check for conflicts
    if "ctrl+c" in combo:
        return False, "Ctrl+C is reserved for interrupt"

    if "ctrl+z" in combo:
        return False, "Ctrl+Z is reserved for suspend"

    # Check for valid keys
    valid_keys = {
        "ctrl", "alt", "shift", "cmd", "meta", "super",
        "space", "enter", "tab", "escape",
        "up", "down", "left", "right",
        "a-z", "0-9", "f1-f24"
    }

    # Platform-specific validation
    if platform.system() == "Darwin" and "meta" in keys:
        return False, "Use 'cmd' instead of 'meta' on macOS"

    return True, "Valid"
```

## Migration from Existing Config

```python
class ConfigMigrator:
    """Migrate from old config format"""

    def migrate_v0_to_v1(self, old_config: dict) -> dict:
        """Migrate from initial format to v1.0"""

        new_config = {
            "version": "1.0",
            "enabled": old_config.get("ptt_enabled", False)
        }

        # Map old keys to new format
        if "ptt_keys" in old_config:
            new_config["keyBindings"] = {
                "default": {
                    "keys": old_config["ptt_keys"].split("+")
                }
            }

        return new_config

    def check_and_migrate(self, config_path: str):
        """Check config version and migrate if needed"""

        with open(config_path) as f:
            config = yaml.safe_load(f)

        version = config.get("version", "0")

        if version < "1.0":
            new_config = self.migrate_v0_to_v1(config)

            # Backup old config
            shutil.copy(config_path, f"{config_path}.backup")

            # Write new config
            with open(config_path, "w") as f:
                yaml.dump(new_config, f)

            print(f"✅ Config migrated to v1.0 (backup: {config_path}.backup)")
```

## Configuration Presets

```python
PTT_PRESETS = {
    "walkie_talkie": {
        "mode": "hold",
        "key_combo": "space",
        "audio_feedback": True,
        "visual_feedback": True,
        "min_duration": 0.1
    },

    "dictation": {
        "mode": "toggle",
        "key_combo": "f13",
        "audio_feedback": False,
        "visual_feedback": True,
        "timeout": 300.0
    },

    "gaming": {
        "mode": "hold",
        "key_combo": "caps_lock",
        "audio_feedback": False,
        "visual_feedback": False,
        "release_delay": 0.0
    },

    "accessibility": {
        "mode": "toggle",
        "key_combo": "f15",
        "audio_feedback": True,
        "visual_feedback": True,
        "haptic_feedback": True
    }
}

def apply_preset(preset_name: str):
    """Apply a configuration preset"""
    if preset_name not in PTT_PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}")

    preset = PTT_PRESETS[preset_name]

    # Update environment variables
    for key, value in preset.items():
        env_key = f"CHATTA_PTT_{key.upper()}"
        os.environ[env_key] = str(value)

    print(f"✅ Applied preset: {preset_name}")
```

## Runtime Configuration API

```python
class PTTConfig:
    """Runtime configuration API"""

    def __init__(self):
        self.manager = PTTConfigManager()
        self._overrides = {}

    def set(self, key: str, value: any) -> None:
        """Set runtime override"""
        self._overrides[key] = value

    def get(self, key: str, default=None) -> any:
        """Get config value"""
        # Check overrides first
        if key in self._overrides:
            return self._overrides[key]

        # Fall back to hierarchy
        return self.manager.get_config(key, default)

    def reset(self, key: str = None) -> None:
        """Reset override(s)"""
        if key:
            self._overrides.pop(key, None)
        else:
            self._overrides.clear()

    def export(self, format: str = "yaml") -> str:
        """Export current configuration"""
        config = {
            k: self.get(k) for k in PTT_DEFAULTS.keys()
        }

        if format == "yaml":
            return yaml.dump(config)
        elif format == "json":
            return json.dumps(config, indent=2)
        elif format == "env":
            return "\n".join([
                f"CHATTA_PTT_{k.upper()}={v}"
                for k, v in config.items()
            ])
```

## Configuration Validation

```python
def validate_config(config: dict) -> list[str]:
    """Validate PTT configuration"""

    errors = []

    # Check version
    if "version" not in config:
        errors.append("Missing version field")

    # Validate key combo
    if "key_combo" in config:
        valid, msg = validate_key_combo(config["key_combo"])
        if not valid:
            errors.append(f"Invalid key combo: {msg}")

    # Validate mode
    if config.get("mode") not in ["hold", "toggle", "hybrid"]:
        errors.append(f"Invalid mode: {config.get('mode')}")

    # Validate numeric ranges
    if not 0.0 <= config.get("feedback_volume", 0.7) <= 1.0:
        errors.append("feedback_volume must be between 0.0 and 1.0")

    if config.get("timeout", 120) < 1:
        errors.append("timeout must be at least 1 second")

    return errors
```