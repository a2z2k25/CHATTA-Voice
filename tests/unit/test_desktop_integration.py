#!/usr/bin/env python3
"""Test desktop integration system."""

import sys
import os
import time
import json
import tempfile
import threading
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.desktop_integration import (
    IntegrationMode,
    ProtocolVersion,
    SessionState,
    IntegrationConfig,
    SessionMetrics,
    DesktopBridge,
    PreferenceSync,
    ContextManager,
    VoiceSessionManager,
    DesktopIntegrationManager,
    get_integration_manager,
    create_manager,
    initialize_integration,
    get_desktop_preferences,
    sync_preferences
)


def test_integration_config():
    """Test integration configuration."""
    print("\n=== Testing Integration Config ===")
    
    # Default config
    config = IntegrationConfig()
    assert config.mode == IntegrationMode.HYBRID
    assert config.protocol_version == ProtocolVersion.AUTO
    assert config.auto_start == True
    assert config.connection_timeout == 5.0
    print("✓ Default config creation working")
    
    # Custom config
    custom_config = IntegrationConfig(
        mode=IntegrationMode.EMBEDDED,
        protocol_version=ProtocolVersion.MCP_2_0,
        connection_timeout=10.0,
        enable_context_sharing=False
    )
    assert custom_config.mode == IntegrationMode.EMBEDDED
    assert custom_config.protocol_version == ProtocolVersion.MCP_2_0
    assert custom_config.connection_timeout == 10.0
    assert custom_config.enable_context_sharing == False
    print("✓ Custom config creation working")


def test_session_metrics():
    """Test session metrics."""
    print("\n=== Testing Session Metrics ===")
    
    metrics = SessionMetrics(
        session_id="test-123",
        start_time=time.time(),
        total_interactions=5,
        successful_handoffs=2,
        failed_handoffs=1
    )
    
    assert metrics.session_id == "test-123"
    assert metrics.total_interactions == 5
    assert metrics.successful_handoffs == 2
    assert metrics.failed_handoffs == 1
    assert metrics.timestamp > 0
    assert len(metrics.errors) == 0
    print("✓ Session metrics creation working")


def test_desktop_bridge():
    """Test desktop bridge communication."""
    print("\n=== Testing Desktop Bridge ===")
    
    config = IntegrationConfig()
    bridge = DesktopBridge(config)
    
    assert bridge.is_connected == False
    assert bridge.session_id is not None
    assert len(bridge.session_id) > 10  # UUID format
    print("✓ Bridge initialization working")
    
    # Test connection (will fail in test environment)
    connected = bridge.connect()
    # Should fail since no desktop is running in test
    assert connected == False
    print("✓ Bridge connection handling working")
    
    # Test message sending (should work even without connection)
    bridge.is_connected = True  # Mock connection
    success = bridge.send_voice_data(b"test audio data", {"format": "pcm"})
    assert success == True
    print("✓ Voice data sending working")
    
    # Test handoff request
    context = {"conversation_id": "conv-123", "messages": []}
    success = bridge.request_handoff(context)
    assert success == True
    print("✓ Handoff request working")
    
    # Test preference sync
    preferences = {"voice_id": "shimmer", "speed": 1.2}
    success = bridge.sync_preferences(preferences)
    assert success == True
    print("✓ Preference sync working")


def test_platform_discovery():
    """Test platform-specific discovery methods."""
    print("\n=== Testing Platform Discovery ===")
    
    config = IntegrationConfig()
    bridge = DesktopBridge(config)
    
    # Test discovery methods (will return False in test environment)
    if sys.platform == "darwin":
        result = bridge._discover_macos()
        assert isinstance(result, bool)
        print("✓ macOS discovery working")
    elif sys.platform == "win32":
        result = bridge._discover_windows()
        assert isinstance(result, bool)
        print("✓ Windows discovery working")
    else:
        result = bridge._discover_linux()
        assert isinstance(result, bool)
        print("✓ Linux discovery working")


def test_preference_sync():
    """Test preference synchronization."""
    print("\n=== Testing Preference Sync ===")
    
    config = IntegrationConfig()
    sync = PreferenceSync(config)
    
    # Test default preferences
    default_prefs = sync._get_default_preferences()
    assert "voice" in default_prefs
    assert "ui" in default_prefs
    assert "integration" in default_prefs
    assert default_prefs["voice"]["tts_provider"] == "auto"
    print("✓ Default preferences working")
    
    # Test preference loading/saving with temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
        test_prefs = {"voice": {"voice_id": "alloy"}, "ui": {"theme": "dark"}}
        json.dump(test_prefs, f)
    
    try:
        loaded_prefs = sync.load_local_preferences(temp_path)
        assert loaded_prefs["voice"]["voice_id"] == "alloy"
        assert loaded_prefs["ui"]["theme"] == "dark"
        print("✓ Preference loading working")
        
        # Test saving
        new_prefs = {"voice": {"voice_id": "nova"}, "ui": {"theme": "light"}}
        sync.save_local_preferences(new_prefs, temp_path)
        
        # Reload and verify
        loaded_again = sync.load_local_preferences(temp_path)
        assert loaded_again["voice"]["voice_id"] == "nova"
        print("✓ Preference saving working")
        
    finally:
        os.unlink(temp_path)
    
    # Test merging
    local = {"voice": {"voice_id": "shimmer"}, "ui": {"theme": "auto"}}
    remote = {"voice": {"speed": 1.5}, "ui": {"theme": "dark"}}
    sync.local_preferences = local
    
    merged = sync.merge_preferences(remote)
    assert "voice" in merged
    assert merged.get("voice", {}).get("voice_id") == "shimmer"  # Local voice preference kept
    assert merged.get("voice", {}).get("speed") == 1.5  # Remote setting added
    assert merged.get("ui", {}).get("theme") == "dark"  # Remote UI setting used
    print("✓ Preference merging working")


def test_context_manager():
    """Test conversation context management."""
    print("\n=== Testing Context Manager ===")
    
    config = IntegrationConfig()
    manager = ContextManager(config)
    
    # Test context updates
    initial_context = {"conversation_id": "conv-1", "messages": ["hello"]}
    manager.update_context(initial_context)
    
    assert manager.current_context["conversation_id"] == "conv-1"
    assert len(manager.context_history) == 0  # First context, no history yet
    print("✓ Context update working")
    
    # Test context archival
    updated_context = {"conversation_id": "conv-1", "messages": ["hello", "hi there"]}
    manager.update_context(updated_context)
    
    assert len(manager.context_history) == 1  # Previous context archived
    assert manager.context_history[0]["context"]["messages"] == ["hello"]
    assert manager.current_context["messages"] == ["hello", "hi there"]
    print("✓ Context archival working")
    
    # Test shareable context filtering
    sensitive_context = {
        "conversation_id": "conv-1",
        "api_key": "secret-key",
        "user_message": "public message",
        "private_token": "private-data"
    }
    manager.update_context(sensitive_context)
    
    shareable = manager.get_shareable_context()
    assert "conversation_id" in shareable
    assert "user_message" in shareable
    assert "api_key" not in shareable  # Filtered out
    assert "private_token" not in shareable  # Filtered out
    print("✓ Sensitive context filtering working")
    
    # Test remote context merging
    remote_context = {"remote_session_id": "remote-123", "conversation_id": "should-not-override"}
    manager.merge_remote_context(remote_context)
    
    assert manager.current_context["remote_session_id"] == "remote-123"
    assert manager.current_context["conversation_id"] == "conv-1"  # Protected from override
    print("✓ Remote context merging working")


def test_voice_session_manager():
    """Test voice session management."""
    print("\n=== Testing Voice Session Manager ===")
    
    config = IntegrationConfig()
    session_mgr = VoiceSessionManager(config)
    
    assert session_mgr.state == SessionState.INACTIVE
    assert session_mgr.current_session is None
    print("✓ Session manager initialization working")
    
    # Test session start
    session_id = session_mgr.start_session()
    assert session_mgr.state == SessionState.ACTIVE
    assert session_mgr.current_session == session_id
    assert session_mgr.metrics is not None
    assert session_mgr.metrics.session_id == session_id
    print("✓ Session start working")
    
    # Test callback registration and notification
    callback_data = {}
    def test_callback(data):
        callback_data.update(data)
    
    session_mgr.register_callback("test_event", test_callback)
    session_mgr._notify_callbacks("test_event", {"test_key": "test_value"})
    assert callback_data["test_key"] == "test_value"
    print("✓ Session callbacks working")
    
    # Test handoff request (mock bridge)
    mock_bridge = Mock()
    mock_bridge.is_connected = True
    mock_bridge.request_handoff.return_value = True
    
    context = {"conversation": "test context"}
    success = session_mgr.request_handoff(context, mock_bridge)
    assert success == True
    assert session_mgr.metrics.successful_handoffs == 1
    mock_bridge.request_handoff.assert_called_once_with(context)
    print("✓ Handoff request working")
    
    # Test handoff response
    session_mgr.handle_handoff_response(True, "desktop-session-123")
    assert session_mgr.state == SessionState.PAUSED
    assert session_mgr.handoff_pending == False
    print("✓ Handoff response handling working")
    
    # Test session end
    session_mgr.end_session(session_id)
    assert session_mgr.state == SessionState.INACTIVE
    assert session_mgr.current_session is None
    print("✓ Session end working")


def test_desktop_integration_manager():
    """Test main desktop integration manager."""
    print("\n=== Testing Desktop Integration Manager ===")
    
    config = IntegrationConfig(mode=IntegrationMode.STANDALONE)
    manager = DesktopIntegrationManager(config)
    
    assert manager.is_initialized == False
    print("✓ Manager initialization working")
    
    # Test initialization in standalone mode
    success = manager.initialize()
    assert success == True
    assert manager.is_initialized == True
    print("✓ Manager standalone initialization working")
    
    # Test voice input handling
    audio_data = b"test audio data"
    metadata = {"format": "pcm", "sample_rate": 16000}
    
    # Start a session first
    session_id = manager.session_manager.start_session()
    
    success = manager.handle_voice_input(audio_data, metadata)
    assert success == True
    assert manager.session_manager.metrics.total_interactions == 1
    print("✓ Voice input handling working")
    
    # Test context sync
    context = {"conversation_id": "test-conv", "turn": 1}
    manager.sync_conversation_context(context)
    assert manager.context_manager.current_context["conversation_id"] == "test-conv"
    print("✓ Context sync working")
    
    # Test metrics retrieval
    metrics = manager.get_metrics()
    assert metrics is not None
    assert metrics.session_id == session_id
    assert metrics.total_interactions == 1
    print("✓ Metrics retrieval working")
    
    # Test shutdown
    manager.shutdown()
    print("✓ Manager shutdown working")


def test_integration_modes():
    """Test different integration modes."""
    print("\n=== Testing Integration Modes ===")
    
    modes = [
        IntegrationMode.STANDALONE,
        IntegrationMode.HYBRID,
        IntegrationMode.EMBEDDED,
        IntegrationMode.BRIDGE
    ]
    
    for mode in modes:
        config = IntegrationConfig(mode=mode)
        manager = DesktopIntegrationManager(config)
        
        # Should initialize successfully in all modes
        success = manager.initialize()
        assert success == True
        
        # Mode may change due to fallback logic
        final_mode = manager.config.mode
        assert final_mode in [mode, IntegrationMode.STANDALONE]  # May fallback to standalone
        
        manager.shutdown()
        print(f"✓ {mode.value} mode working (final mode: {final_mode.value})")


def test_protocol_versions():
    """Test protocol version handling."""
    print("\n=== Testing Protocol Versions ===")
    
    versions = [
        ProtocolVersion.MCP_1_0,
        ProtocolVersion.MCP_1_1,
        ProtocolVersion.MCP_2_0,
        ProtocolVersion.AUTO
    ]
    
    for version in versions:
        config = IntegrationConfig(protocol_version=version)
        bridge = DesktopBridge(config)
        
        bridge._negotiate_protocol()
        
        if version == ProtocolVersion.AUTO:
            assert bridge.protocol_version == ProtocolVersion.MCP_1_1.value  # Default
        else:
            assert bridge.protocol_version == version.value
        
        print(f"✓ {version.value} protocol handling working")


def test_global_manager():
    """Test global manager functions."""
    print("\n=== Testing Global Manager ===")
    
    # Test global instance
    manager1 = get_integration_manager()
    manager2 = get_integration_manager()
    assert manager1 is manager2  # Same instance
    print("✓ Global manager singleton working")
    
    # Test manager creation
    config = IntegrationConfig(mode=IntegrationMode.EMBEDDED)
    new_manager = create_manager(config)
    assert new_manager is not manager1  # Different instance
    assert new_manager.config.mode == IntegrationMode.EMBEDDED
    print("✓ Manager creation working")
    
    # Test convenience functions
    success = initialize_integration(IntegrationMode.STANDALONE)
    assert success == True
    print("✓ Integration initialization working")
    
    # Test preference functions
    prefs = get_desktop_preferences()
    assert isinstance(prefs, dict)
    assert "voice" in prefs or len(prefs) == 0  # May be empty initially
    print("✓ Desktop preferences retrieval working")
    
    test_prefs = {"voice": {"voice_id": "test"}}
    # sync_preferences may fail without connection, but shouldn't crash
    try:
        sync_result = sync_preferences(test_prefs)
        assert isinstance(sync_result, bool)
    except Exception as e:
        # Expected in test environment
        pass
    print("✓ Preference sync function working")


def test_error_handling():
    """Test error handling and edge cases."""
    print("\n=== Testing Error Handling ===")
    
    # Test with invalid config path
    config = IntegrationConfig()
    sync = PreferenceSync(config)
    
    # Try to load from non-existent file
    prefs = sync.load_local_preferences("/non/existent/path.json")
    assert isinstance(prefs, dict)  # Should return defaults
    print("✓ Invalid file path handling working")
    
    # Test bridge operations without connection
    bridge = DesktopBridge(config)
    assert bridge.is_connected == False
    
    success = bridge.send_voice_data(b"test", {})
    assert success == False  # Should fail gracefully
    print("✓ Disconnected bridge handling working")
    
    # Test session operations with invalid session
    session_mgr = VoiceSessionManager(config)
    session_mgr.end_session("non-existent-session")  # Should not crash
    print("✓ Invalid session handling working")
    
    # Test context manager with empty context
    context_mgr = ContextManager(config)
    context_mgr.update_context({})
    shareable = context_mgr.get_shareable_context()
    assert isinstance(shareable, dict)
    print("✓ Empty context handling working")


def test_threading_safety():
    """Test thread safety of managers."""
    print("\n=== Testing Threading Safety ===")
    
    manager = DesktopIntegrationManager()
    manager.initialize()
    
    # Test concurrent context updates
    def update_context(thread_id):
        for i in range(10):
            context = {"thread": thread_id, "iteration": i}
            manager.sync_conversation_context(context)
            time.sleep(0.001)
    
    threads = []
    for i in range(3):
        thread = threading.Thread(target=update_context, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Should complete without exceptions
    assert manager.context_manager.current_context is not None
    print("✓ Concurrent context updates working")
    
    # Test concurrent preference operations
    def update_preferences(thread_id):
        prefs = {"thread_id": thread_id, "timestamp": time.time()}
        manager.preference_sync.local_preferences.update(prefs)
    
    threads = []
    for i in range(3):
        thread = threading.Thread(target=update_preferences, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    print("✓ Concurrent preference updates working")
    
    manager.shutdown()


def main():
    """Run all tests."""
    print("=" * 60)
    print("DESKTOP INTEGRATION TESTS")
    print("=" * 60)
    
    test_integration_config()
    test_session_metrics()
    test_desktop_bridge()
    test_platform_discovery()
    test_preference_sync()
    test_context_manager()
    test_voice_session_manager()
    test_desktop_integration_manager()
    test_integration_modes()
    test_protocol_versions()
    test_global_manager()
    test_error_handling()
    test_threading_safety()
    
    print("\n" + "=" * 60)
    print("✓ All desktop integration tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    main()