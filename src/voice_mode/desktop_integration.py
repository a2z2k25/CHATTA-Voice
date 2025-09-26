#!/usr/bin/env python3
"""Claude Desktop Integration Refinement

This module provides refined integration with Claude Desktop, ensuring
seamless voice interaction capabilities and feature parity between
desktop and code environments.
"""

import os
import sys
import json
import time
import asyncio
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class IntegrationMode(Enum):
    """Integration modes for Claude Desktop."""
    STANDALONE = "standalone"           # Independent operation
    HYBRID = "hybrid"                  # Coordinated with desktop
    EMBEDDED = "embedded"              # Fully embedded in desktop
    BRIDGE = "bridge"                  # Bridge mode for compatibility


class ProtocolVersion(Enum):
    """MCP protocol versions supported."""
    MCP_1_0 = "1.0"
    MCP_1_1 = "1.1"
    MCP_2_0 = "2.0"
    AUTO = "auto"                      # Auto-detect best version


class SessionState(Enum):
    """Voice session states."""
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class IntegrationConfig:
    """Configuration for Claude Desktop integration."""
    mode: IntegrationMode = IntegrationMode.HYBRID
    protocol_version: ProtocolVersion = ProtocolVersion.AUTO
    desktop_app_path: Optional[str] = None
    config_path: Optional[str] = None
    auto_start: bool = True
    sync_preferences: bool = True
    voice_priority: bool = True
    fallback_mode: IntegrationMode = IntegrationMode.STANDALONE
    
    # Connection settings
    connection_timeout: float = 5.0
    retry_attempts: int = 3
    heartbeat_interval: float = 30.0
    
    # Feature flags
    enable_context_sharing: bool = True
    enable_session_sync: bool = True
    enable_preference_sync: bool = True
    enable_voice_handoff: bool = True


@dataclass
class SessionMetrics:
    """Metrics for desktop integration session."""
    session_id: str
    start_time: float
    total_interactions: int = 0
    successful_handoffs: int = 0
    failed_handoffs: int = 0
    context_shares: int = 0
    preference_syncs: int = 0
    average_latency_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class DesktopBridge:
    """Bridge for communication with Claude Desktop application."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.is_connected = False
        self.desktop_process = None
        self.session_id = str(uuid.uuid4())
        self.protocol_version = None
        self._lock = threading.Lock()
        self._callbacks = {}
        
    def connect(self) -> bool:
        """Connect to Claude Desktop application."""
        with self._lock:
            try:
                if self._discover_desktop():
                    self._negotiate_protocol()
                    self._establish_connection()
                    self.is_connected = True
                    logger.info(f"Connected to Claude Desktop (protocol {self.protocol_version})")
                    return True
            except Exception as e:
                logger.error(f"Failed to connect to desktop: {e}")
                self.is_connected = False
        return False
    
    def disconnect(self):
        """Disconnect from Claude Desktop."""
        with self._lock:
            if self.is_connected:
                try:
                    self._send_message({"type": "disconnect", "session_id": self.session_id})
                except:
                    pass
                self.is_connected = False
                logger.info("Disconnected from Claude Desktop")
    
    def send_voice_data(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        """Send voice data to desktop application."""
        if not self.is_connected:
            return False
            
        message = {
            "type": "voice_data",
            "session_id": self.session_id,
            "data": audio_data.hex(),
            "metadata": metadata,
            "timestamp": time.time()
        }
        return self._send_message(message)
    
    def request_handoff(self, context: Dict[str, Any]) -> bool:
        """Request handoff of conversation to desktop."""
        if not self.is_connected:
            return False
            
        message = {
            "type": "handoff_request",
            "session_id": self.session_id,
            "context": context,
            "timestamp": time.time()
        }
        return self._send_message(message)
    
    def sync_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Sync voice preferences with desktop."""
        if not self.is_connected:
            return False
            
        message = {
            "type": "preference_sync",
            "session_id": self.session_id,
            "preferences": preferences,
            "timestamp": time.time()
        }
        return self._send_message(message)
    
    def _discover_desktop(self) -> bool:
        """Discover running Claude Desktop instance."""
        # Platform-specific discovery logic
        if sys.platform == "darwin":  # macOS
            return self._discover_macos()
        elif sys.platform == "win32":  # Windows
            return self._discover_windows()
        else:  # Linux and others
            return self._discover_linux()
    
    def _discover_macos(self) -> bool:
        """Discover Claude Desktop on macOS."""
        try:
            import subprocess
            # Check if Claude Desktop is running
            result = subprocess.run(
                ["pgrep", "-f", "Claude"], 
                capture_output=True, 
                text=True
            )
            # For testing purposes, always return False unless actually found
            return result.returncode == 0 and "Claude" in result.stdout
        except:
            return False
    
    def _discover_windows(self) -> bool:
        """Discover Claude Desktop on Windows."""
        try:
            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Claude.exe"],
                capture_output=True,
                text=True
            )
            return "Claude.exe" in result.stdout
        except:
            return False
    
    def _discover_linux(self) -> bool:
        """Discover Claude Desktop on Linux."""
        try:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-f", "claude"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _negotiate_protocol(self):
        """Negotiate MCP protocol version."""
        if self.config.protocol_version == ProtocolVersion.AUTO:
            # Auto-detect best supported version
            self.protocol_version = ProtocolVersion.MCP_1_1.value
        else:
            self.protocol_version = self.config.protocol_version.value
    
    def _establish_connection(self):
        """Establish connection with desktop."""
        # Simulate connection establishment
        time.sleep(0.1)
        return True
    
    def _send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to desktop application."""
        try:
            # In real implementation, this would use IPC mechanism
            logger.debug(f"Sending message to desktop: {message['type']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False


class PreferenceSync:
    """Synchronization of preferences between environments."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.local_preferences = {}
        self.remote_preferences = {}
        self.sync_timestamp = 0
        self._lock = threading.Lock()
    
    def load_local_preferences(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Load local voice preferences."""
        with self._lock:
            try:
                if not path:
                    path = self._get_default_preferences_path()
                
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        self.local_preferences = json.load(f)
                else:
                    self.local_preferences = self._get_default_preferences()
                
                return self.local_preferences.copy()
            except Exception as e:
                logger.error(f"Failed to load local preferences: {e}")
                return self._get_default_preferences()
    
    def save_local_preferences(self, preferences: Dict[str, Any], path: Optional[str] = None):
        """Save local voice preferences."""
        with self._lock:
            try:
                if not path:
                    path = self._get_default_preferences_path()
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                with open(path, 'w') as f:
                    json.dump(preferences, f, indent=2)
                
                self.local_preferences = preferences.copy()
                self.sync_timestamp = time.time()
                
            except Exception as e:
                logger.error(f"Failed to save local preferences: {e}")
    
    def sync_with_remote(self, bridge: DesktopBridge) -> bool:
        """Sync preferences with remote desktop."""
        if not self.config.sync_preferences or not bridge.is_connected:
            return False
        
        try:
            # Send local preferences to desktop
            success = bridge.sync_preferences(self.local_preferences)
            if success:
                self.sync_timestamp = time.time()
            return success
        except Exception as e:
            logger.error(f"Failed to sync preferences: {e}")
            return False
    
    def merge_preferences(self, remote_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge local and remote preferences."""
        with self._lock:
            merged = self.local_preferences.copy()
            
            # Merge with priority rules - deep merge for nested dicts
            for key, value in remote_prefs.items():
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, dict) and isinstance(merged[key], dict):
                    # Deep merge for nested dictionaries
                    for subkey, subvalue in value.items():
                        if subkey not in merged[key] or self._should_use_remote(subkey, subvalue):
                            merged[key][subkey] = subvalue
                elif self._should_use_remote(key, value):
                    merged[key] = value
            
            return merged
    
    def _get_default_preferences_path(self) -> str:
        """Get default preferences file path."""
        home = Path.home()
        return str(home / ".claude" / "voice_preferences.json")
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default voice preferences."""
        return {
            "voice": {
                "tts_provider": "auto",
                "stt_provider": "auto",
                "voice_id": "shimmer",
                "speed": 1.0,
                "enable_vad": True,
                "vad_aggressiveness": 1
            },
            "ui": {
                "show_transcripts": True,
                "show_audio_indicators": True,
                "theme": "auto"
            },
            "integration": {
                "auto_handoff": False,
                "sync_context": True,
                "voice_priority": True
            }
        }
    
    def _should_use_remote(self, key: str, remote_value: Any) -> bool:
        """Determine if remote preference should override local."""
        # Priority rules for different preference types
        priority_keys = {"voice_id", "tts_provider", "stt_provider"}
        if key in priority_keys:
            return False  # Keep local voice preferences
        return True  # Use remote for UI and other settings


class ContextManager:
    """Manager for conversation context sharing."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.current_context = {}
        self.context_history = []
        self.max_history = 10
        self._lock = threading.Lock()
    
    def update_context(self, context: Dict[str, Any]):
        """Update current conversation context."""
        with self._lock:
            # Archive current context
            if self.current_context:
                self.context_history.append({
                    "context": self.current_context.copy(),
                    "timestamp": time.time()
                })
                
                # Trim history
                if len(self.context_history) > self.max_history:
                    self.context_history.pop(0)
            
            self.current_context = context.copy()
    
    def get_shareable_context(self) -> Dict[str, Any]:
        """Get context suitable for sharing with desktop."""
        if not self.config.enable_context_sharing:
            return {}
        
        with self._lock:
            # Filter sensitive information
            shareable = {}
            for key, value in self.current_context.items():
                if not self._is_sensitive(key):
                    shareable[key] = value
            
            return shareable
    
    def merge_remote_context(self, remote_context: Dict[str, Any]):
        """Merge context received from desktop."""
        with self._lock:
            # Merge non-conflicting context
            for key, value in remote_context.items():
                if key not in self.current_context or self._should_merge(key):
                    self.current_context[key] = value
    
    def _is_sensitive(self, key: str) -> bool:
        """Check if context key contains sensitive information."""
        sensitive_keys = {"api_key", "token", "password", "secret", "private"}
        return any(s in key.lower() for s in sensitive_keys)
    
    def _should_merge(self, key: str) -> bool:
        """Determine if remote context should be merged."""
        # Avoid overriding local conversation state
        protected_keys = {"conversation_id", "session_id", "user_id"}
        return key not in protected_keys


class VoiceSessionManager:
    """Manager for voice session coordination."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.state = SessionState.INACTIVE
        self.current_session = None
        self.handoff_pending = False
        self.metrics = None
        self._lock = threading.Lock()
        self._callbacks = {}
    
    def start_session(self) -> str:
        """Start a new voice session."""
        with self._lock:
            session_id = str(uuid.uuid4())
            self.current_session = session_id
            self.state = SessionState.INITIALIZING
            self.metrics = SessionMetrics(session_id=session_id, start_time=time.time())
            
            # Transition to active
            self.state = SessionState.ACTIVE
            self._notify_callbacks("session_started", {"session_id": session_id})
            
            return session_id
    
    def end_session(self, session_id: str):
        """End voice session."""
        with self._lock:
            if self.current_session == session_id:
                self.state = SessionState.INACTIVE
                self.current_session = None
                if self.metrics:
                    self.metrics.timestamp = time.time()
                self._notify_callbacks("session_ended", {"session_id": session_id})
    
    def request_handoff(self, context: Dict[str, Any], bridge: DesktopBridge) -> bool:
        """Request handoff to desktop environment."""
        if not bridge.is_connected or self.state != SessionState.ACTIVE:
            return False
        
        with self._lock:
            self.handoff_pending = True
            success = bridge.request_handoff(context)
            
            if success and self.metrics:
                self.metrics.successful_handoffs += 1
            elif self.metrics:
                self.metrics.failed_handoffs += 1
                
            return success
    
    def handle_handoff_response(self, accepted: bool, desktop_session_id: Optional[str] = None):
        """Handle handoff response from desktop."""
        with self._lock:
            self.handoff_pending = False
            if accepted and desktop_session_id:
                self.state = SessionState.PAUSED
                self._notify_callbacks("handoff_accepted", {
                    "desktop_session_id": desktop_session_id
                })
            else:
                self._notify_callbacks("handoff_rejected", {})
    
    def register_callback(self, event: str, callback: Callable):
        """Register callback for session events."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def _notify_callbacks(self, event: str, data: Dict[str, Any]):
        """Notify registered callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")


class DesktopIntegrationManager:
    """Main manager for Claude Desktop integration."""
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        self.config = config or IntegrationConfig()
        self.bridge = DesktopBridge(self.config)
        self.preference_sync = PreferenceSync(self.config)
        self.context_manager = ContextManager(self.config)
        self.session_manager = VoiceSessionManager(self.config)
        self.is_initialized = False
        self._background_task = None
        self._shutdown = False
    
    def initialize(self) -> bool:
        """Initialize desktop integration."""
        try:
            # Load local preferences
            self.preference_sync.load_local_preferences()
            
            # Attempt connection if not standalone
            if self.config.mode != IntegrationMode.STANDALONE:
                connected = self.bridge.connect()
                if not connected and self.config.fallback_mode:
                    logger.info(f"Falling back to {self.config.fallback_mode.value} mode")
                    self.config.mode = self.config.fallback_mode
            
            # Start background tasks
            self._start_background_tasks()
            
            self.is_initialized = True
            logger.info(f"Desktop integration initialized in {self.config.mode.value} mode")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize desktop integration: {e}")
            return False
    
    def shutdown(self):
        """Shutdown desktop integration."""
        self._shutdown = True
        
        if self._background_task:
            self._background_task.join(timeout=1.0)
        
        if self.bridge.is_connected:
            self.bridge.disconnect()
        
        logger.info("Desktop integration shutdown complete")
    
    def handle_voice_input(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        """Handle voice input with potential desktop forwarding."""
        if not self.is_initialized:
            return False
        
        # Update metrics
        session = self.session_manager.current_session
        if session and self.session_manager.metrics:
            self.session_manager.metrics.total_interactions += 1
        
        # Forward to desktop if connected and configured
        if (self.config.enable_voice_handoff and 
            self.bridge.is_connected and 
            self.config.voice_priority):
            return self.bridge.send_voice_data(audio_data, metadata)
        
        return True
    
    def sync_conversation_context(self, context: Dict[str, Any]):
        """Sync conversation context with desktop."""
        self.context_manager.update_context(context)
        
        if (self.config.enable_context_sharing and 
            self.bridge.is_connected):
            shareable_context = self.context_manager.get_shareable_context()
            # In real implementation, would send via bridge
            logger.debug("Context synced with desktop")
    
    def get_metrics(self) -> Optional[SessionMetrics]:
        """Get current session metrics."""
        return self.session_manager.metrics
    
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        if not self.config.sync_preferences:
            return
        
        def background_worker():
            while not self._shutdown:
                try:
                    # Periodic preference sync
                    if self.bridge.is_connected:
                        self.preference_sync.sync_with_remote(self.bridge)
                    time.sleep(self.config.heartbeat_interval)
                except Exception as e:
                    logger.error(f"Background task error: {e}")
                    time.sleep(5.0)
        
        self._background_task = threading.Thread(target=background_worker, daemon=True)
        self._background_task.start()


# Global instance
_integration_manager = None
_manager_lock = threading.Lock()


def get_integration_manager(config: Optional[IntegrationConfig] = None) -> DesktopIntegrationManager:
    """Get global desktop integration manager."""
    global _integration_manager
    with _manager_lock:
        if _integration_manager is None:
            _integration_manager = DesktopIntegrationManager(config)
        return _integration_manager


def create_manager(config: IntegrationConfig) -> DesktopIntegrationManager:
    """Create new desktop integration manager."""
    return DesktopIntegrationManager(config)


# Convenience functions
def initialize_integration(mode: IntegrationMode = IntegrationMode.HYBRID) -> bool:
    """Initialize desktop integration with specified mode."""
    config = IntegrationConfig(mode=mode)
    manager = get_integration_manager(config)
    return manager.initialize()


def get_desktop_preferences() -> Dict[str, Any]:
    """Get current desktop preferences."""
    manager = get_integration_manager()
    return manager.preference_sync.local_preferences.copy()


def sync_preferences(preferences: Dict[str, Any]) -> bool:
    """Sync preferences with desktop."""
    manager = get_integration_manager()
    manager.preference_sync.save_local_preferences(preferences)
    return manager.preference_sync.sync_with_remote(manager.bridge)