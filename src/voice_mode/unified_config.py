#!/usr/bin/env python3
"""Unified Configuration System for CHATTA Voice Mode.

Provides hierarchical configuration management with:
- Multiple configuration sources (env, files, defaults)
- Schema validation
- Configuration migration
- Hot reloading
- Type safety
"""

import os
import json
import yaml
import toml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, TypeVar, Generic
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import hashlib
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConfigSource(Enum):
    """Configuration source types."""
    DEFAULT = "default"
    ENVIRONMENT = "environment"
    FILE = "file"
    OVERRIDE = "override"
    RUNTIME = "runtime"


class ConfigFormat(Enum):
    """Configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    ENV = "env"


@dataclass
class ConfigSchema:
    """Configuration schema definition."""
    name: str
    version: str
    fields: Dict[str, Dict[str, Any]]
    required: List[str] = field(default_factory=list)
    deprecated: List[str] = field(default_factory=list)
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema."""
        errors = []
        
        # Helper to get nested values
        def get_nested(dict_obj: dict, key: str, default=None):
            keys = key.split('.')
            value = dict_obj
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            return value
        
        # Check required fields
        for req_field in self.required:
            value = get_nested(config, req_field)
            if value is None:
                errors.append(f"Required field '{req_field}' missing")
        
        # Check field types
        for field_name, field_spec in self.fields.items():
            value = get_nested(config, field_name)
            if value is not None:
                expected_type = field_spec.get("type")
                if expected_type and not isinstance(value, expected_type):
                    errors.append(
                        f"Field '{field_name}' type mismatch: "
                        f"expected {expected_type}, got {type(value)}"
                    )
        
        # Warn about deprecated fields
        for dep_field in self.deprecated:
            if get_nested(config, dep_field) is not None:
                logger.warning(f"Deprecated field '{dep_field}' in use")
        
        return errors


@dataclass
class ConfigValue(Generic[T]):
    """Container for configuration value with metadata."""
    value: T
    source: ConfigSource
    timestamp: float = field(default_factory=time.time)
    override_count: int = 0
    
    def update(self, value: T, source: ConfigSource):
        """Update value with new source."""
        self.value = value
        self.source = source
        self.timestamp = time.time()
        if source == ConfigSource.OVERRIDE:
            self.override_count += 1


class ConfigLoader:
    """Loads configuration from various sources."""
    
    def __init__(self):
        self.parsers = {
            ConfigFormat.JSON: self._load_json,
            ConfigFormat.YAML: self._load_yaml,
            ConfigFormat.TOML: self._load_toml,
            ConfigFormat.ENV: self._load_env
        }
    
    def load_file(self, path: Path, format: Optional[ConfigFormat] = None) -> Dict[str, Any]:
        """Load configuration from file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        # Auto-detect format if not specified
        if format is None:
            suffix = path.suffix.lower()
            if suffix == '.json':
                format = ConfigFormat.JSON
            elif suffix in ['.yaml', '.yml']:
                format = ConfigFormat.YAML
            elif suffix == '.toml':
                format = ConfigFormat.TOML
            else:
                raise ValueError(f"Unknown config format: {suffix}")
        
        parser = self.parsers.get(format)
        if not parser:
            raise ValueError(f"Unsupported format: {format}")
        
        return parser(path)
    
    def load_env(self, prefix: str = "CHATTA_") -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert key to nested structure
                parts = key[len(prefix):].lower().split('_')
                self._set_nested(config, parts, self._parse_env_value(value))
        return config
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON configuration."""
        with open(path) as f:
            return json.load(f)
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration."""
        with open(path) as f:
            return yaml.safe_load(f)
    
    def _load_toml(self, path: Path) -> Dict[str, Any]:
        """Load TOML configuration."""
        with open(path) as f:
            return toml.load(f)
    
    def _load_env(self, path: Path) -> Dict[str, Any]:
        """Load .env file format."""
        config = {}
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    if key and value:
                        config[key.strip()] = self._parse_env_value(value.strip())
        return config
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value."""
        # Try to parse as JSON first
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # Check for boolean
        if value.lower() in ['true', 'yes', '1']:
            return True
        elif value.lower() in ['false', 'no', '0']:
            return False
        
        # Check for number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        return value
    
    def _set_nested(self, dict_obj: dict, keys: list, value: Any):
        """Set nested dictionary value."""
        for key in keys[:-1]:
            dict_obj = dict_obj.setdefault(key, {})
        dict_obj[keys[-1]] = value


class ConfigMigrator:
    """Handles configuration migrations between versions."""
    
    def __init__(self):
        self.migrations = {}
    
    def register_migration(self, from_version: str, to_version: str, 
                          migration_func: callable):
        """Register a migration function."""
        key = (from_version, to_version)
        self.migrations[key] = migration_func
    
    def migrate(self, config: Dict[str, Any], from_version: str, 
                to_version: str) -> Dict[str, Any]:
        """Migrate configuration from one version to another."""
        key = (from_version, to_version)
        if key not in self.migrations:
            logger.warning(f"No migration path from {from_version} to {to_version}")
            return config
        
        migration_func = self.migrations[key]
        migrated = migration_func(config.copy())
        logger.info(f"Migrated config from {from_version} to {to_version}")
        return migrated
    
    def auto_migrate(self, config: Dict[str, Any], target_version: str) -> Dict[str, Any]:
        """Automatically migrate through version chain."""
        current_version = config.get('version', '1.0.0')
        
        if current_version == target_version:
            return config
        
        # Find migration path
        path = self._find_migration_path(current_version, target_version)
        if not path:
            logger.error(f"No migration path from {current_version} to {target_version}")
            return config
        
        # Apply migrations in sequence
        result = config
        for i in range(len(path) - 1):
            from_ver = path[i]
            to_ver = path[i + 1]
            result = self.migrate(result, from_ver, to_ver)
        
        result['version'] = target_version
        return result
    
    def _find_migration_path(self, from_version: str, to_version: str) -> Optional[List[str]]:
        """Find migration path between versions."""
        # Simple BFS to find path
        from collections import deque
        
        queue = deque([(from_version, [from_version])])
        visited = {from_version}
        
        while queue:
            current, path = queue.popleft()
            
            if current == to_version:
                return path
            
            # Find all possible next versions
            for (from_v, to_v) in self.migrations:
                if from_v == current and to_v not in visited:
                    visited.add(to_v)
                    queue.append((to_v, path + [to_v]))
        
        return None


class ConfigWatcher:
    """Watches configuration files for changes."""
    
    def __init__(self, check_interval: float = 1.0):
        self.check_interval = check_interval
        self.watched_files = {}
        self.callbacks = []
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
    
    def watch(self, path: Path, callback: callable = None):
        """Watch a configuration file."""
        with self._lock:
            if path not in self.watched_files:
                self.watched_files[path] = {
                    'mtime': path.stat().st_mtime if path.exists() else 0,
                    'hash': self._get_file_hash(path) if path.exists() else None
                }
            
            if callback:
                self.callbacks.append(callback)
    
    def unwatch(self, path: Path):
        """Stop watching a file."""
        with self._lock:
            self.watched_files.pop(path, None)
    
    def start(self):
        """Start watching files."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop watching files."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
    
    def _watch_loop(self):
        """Main watch loop."""
        while self._running:
            with self._lock:
                for path, info in list(self.watched_files.items()):
                    if self._check_file_changed(path, info):
                        logger.info(f"Config file changed: {path}")
                        for callback in self.callbacks:
                            try:
                                callback(path)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_file_changed(self, path: Path, info: dict) -> bool:
        """Check if file has changed."""
        if not path.exists():
            return False
        
        current_mtime = path.stat().st_mtime
        current_hash = self._get_file_hash(path)
        
        if current_mtime != info['mtime'] or current_hash != info['hash']:
            info['mtime'] = current_mtime
            info['hash'] = current_hash
            return True
        
        return False
    
    def _get_file_hash(self, path: Path) -> str:
        """Get file content hash."""
        if not path.exists():
            return None
        
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()


class UnifiedConfig:
    """Unified configuration manager."""
    
    def __init__(self, app_name: str = "chatta", version: str = "1.0.0"):
        self.app_name = app_name
        self.version = version
        self.loader = ConfigLoader()
        self.migrator = ConfigMigrator()
        self.watcher = ConfigWatcher()
        self.schema = None
        
        # Configuration layers (priority order)
        self.layers = {
            ConfigSource.DEFAULT: {},
            ConfigSource.FILE: {},
            ConfigSource.ENVIRONMENT: {},
            ConfigSource.OVERRIDE: {},
            ConfigSource.RUNTIME: {}
        }
        
        # Merged configuration cache
        self._merged_cache = {}
        self._cache_valid = False
        self._lock = threading.RLock()
        
        # Configuration paths
        self.config_paths = self._get_config_paths()
    
    def _get_config_paths(self) -> List[Path]:
        """Get configuration file search paths."""
        paths = []
        
        # Current directory
        paths.append(Path.cwd() / f"{self.app_name}.config.json")
        
        # User config directory
        if os.name == 'posix':
            config_home = Path.home() / f".config/{self.app_name}"
        else:
            config_home = Path.home() / f".{self.app_name}"
        paths.append(config_home / "config.json")
        
        # System config directory
        if os.name == 'posix':
            paths.append(Path(f"/etc/{self.app_name}/config.json"))
        
        return paths
    
    def load_defaults(self, defaults: Dict[str, Any]):
        """Load default configuration."""
        with self._lock:
            self.layers[ConfigSource.DEFAULT] = defaults
            self._invalidate_cache()
    
    def load_file(self, path: Optional[Path] = None, watch: bool = False):
        """Load configuration from file."""
        if path is None:
            # Search for config file
            for config_path in self.config_paths:
                if config_path.exists():
                    path = config_path
                    break
        
        if path and path.exists():
            config = self.loader.load_file(path)
            
            # Apply migration if needed
            if self.schema and 'version' in config:
                config = self.migrator.auto_migrate(config, self.version)
            
            with self._lock:
                self.layers[ConfigSource.FILE] = config
                self._invalidate_cache()
            
            if watch:
                self.watcher.watch(path, lambda p: self.reload_file(p))
                self.watcher.start()
            
            logger.info(f"Loaded config from: {path}")
    
    def load_environment(self, prefix: str = "CHATTA_"):
        """Load configuration from environment variables."""
        config = self.loader.load_env(prefix)
        with self._lock:
            self.layers[ConfigSource.ENVIRONMENT] = config
            self._invalidate_cache()
    
    def set_override(self, key: str, value: Any):
        """Set configuration override."""
        with self._lock:
            self._set_nested_value(self.layers[ConfigSource.OVERRIDE], key, value)
            self._invalidate_cache()
    
    def set_runtime(self, key: str, value: Any):
        """Set runtime configuration."""
        with self._lock:
            self._set_nested_value(self.layers[ConfigSource.RUNTIME], key, value)
            self._invalidate_cache()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        with self._lock:
            merged = self._get_merged_config()
            return self._get_nested_value(merged, key, default)
    
    def get_with_source(self, key: str) -> Optional[ConfigValue]:
        """Get configuration value with source information."""
        with self._lock:
            # Check layers in priority order
            for source in reversed(list(ConfigSource)):
                layer = self.layers.get(source, {})
                value = self._get_nested_value(layer, key, None)
                if value is not None:
                    return ConfigValue(value=value, source=source)
            return None
    
    def reload_file(self, path: Path):
        """Reload configuration file."""
        logger.info(f"Reloading config file: {path}")
        self.load_file(path, watch=False)
    
    def validate(self, schema: Optional[ConfigSchema] = None) -> List[str]:
        """Validate configuration against schema."""
        if schema:
            self.schema = schema
        
        if not self.schema:
            return []
        
        with self._lock:
            merged = self._get_merged_config()
            return self.schema.validate(merged)
    
    def export(self, format: ConfigFormat = ConfigFormat.JSON) -> str:
        """Export merged configuration."""
        with self._lock:
            merged = self._get_merged_config()
            
            if format == ConfigFormat.JSON:
                return json.dumps(merged, indent=2)
            elif format == ConfigFormat.YAML:
                return yaml.dump(merged, default_flow_style=False)
            elif format == ConfigFormat.TOML:
                return toml.dumps(merged)
            else:
                raise ValueError(f"Unsupported export format: {format}")
    
    def _get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration from all layers."""
        if self._cache_valid:
            return self._merged_cache
        
        merged = {}
        
        # Merge layers in priority order (lowest to highest)
        priority_order = [
            ConfigSource.DEFAULT,
            ConfigSource.FILE,
            ConfigSource.ENVIRONMENT,
            ConfigSource.OVERRIDE,
            ConfigSource.RUNTIME
        ]
        
        for source in priority_order:
            layer = self.layers.get(source, {})
            if layer:
                merged = self._deep_merge(merged, layer)
        
        self._merged_cache = merged
        self._cache_valid = True
        return merged
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _get_nested_value(self, dict_obj: dict, key: str, default: Any = None) -> Any:
        """Get nested dictionary value using dot notation."""
        keys = key.split('.')
        value = dict_obj
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def _set_nested_value(self, dict_obj: dict, key: str, value: Any):
        """Set nested dictionary value using dot notation."""
        keys = key.split('.')
        
        for k in keys[:-1]:
            dict_obj = dict_obj.setdefault(k, {})
        
        dict_obj[keys[-1]] = value
    
    def _invalidate_cache(self):
        """Invalidate merged configuration cache."""
        self._cache_valid = False
        self._merged_cache = {}
    
    def cleanup(self):
        """Cleanup resources."""
        self.watcher.stop()


# Convenience functions
def create_unified_config(app_name: str = "chatta") -> UnifiedConfig:
    """Create and initialize unified configuration."""
    config = UnifiedConfig(app_name)
    
    # Load defaults
    config.load_defaults({
        "voice": {
            "enabled": True,
            "provider": "openai",
            "language": "en-US",
            "sample_rate": 16000
        },
        "audio": {
            "format": "pcm",
            "channels": 1,
            "bit_depth": 16
        },
        "optimization": {
            "compression": "auto",
            "batching": "adaptive",
            "cache_size": 100
        }
    })
    
    # Load from file and environment
    config.load_file(watch=True)
    config.load_environment()
    
    return config


# Global configuration instance
_global_config = None


def get_config() -> UnifiedConfig:
    """Get global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = create_unified_config()
    return _global_config