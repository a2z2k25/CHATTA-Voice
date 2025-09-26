#!/usr/bin/env python3
"""Test session state management implementation."""

import sys
import os
import time
import json
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.session_state import (
    SessionStatus,
    SessionMetadata,
    ConversationContext,
    SessionState,
    SessionManager,
    get_manager
)


def test_session_metadata():
    """Test session metadata."""
    print("\n=== Testing Session Metadata ===")
    
    from datetime import datetime
    
    metadata = SessionMetadata(
        session_id="test123",
        created_at=datetime.now(),
        last_active=datetime.now(),
        status=SessionStatus.ACTIVE,
        platform="claude-code",
        user_id="user456",
        tags=["test", "demo"]
    )
    
    # Test conversion
    data = metadata.to_dict()
    print(f"Metadata dict keys: {list(data.keys())}")
    
    # Test reconstruction
    restored = SessionMetadata.from_dict(data)
    assert restored.session_id == "test123"
    assert restored.platform == "claude-code"
    assert restored.status == SessionStatus.ACTIVE
    print("✓ Metadata serialization working")


def test_session_state():
    """Test individual session state."""
    print("\n=== Testing Session State ===")
    
    session = SessionState("test_session", "claude-desktop")
    
    # Test message management
    session.add_message("user", "Hello world")
    session.add_message("assistant", "Hello! How can I help?")
    
    messages = session.get_messages()
    assert len(messages) == 2
    assert messages[0]['role'] == "user"
    print(f"✓ Added {len(messages)} messages")
    
    # Test settings
    session.context.audio_settings = {
        'sample_rate': 24000,
        'format': 'pcm16'
    }
    session.context.voice_preferences = {
        'voice': 'nova',
        'speed': 1.0
    }
    
    # Test checkpoints
    session.create_checkpoint("Initial state")
    
    # Modify state
    session.add_message("user", "Another message")
    session.context.error_count += 1
    
    # Create another checkpoint
    session.create_checkpoint("After error")
    
    assert len(session.checkpoints) == 2
    print(f"✓ Created {len(session.checkpoints)} checkpoints")
    
    # Test restoration
    messages_before = len(session.get_messages())
    session.restore_checkpoint(0)  # Restore first checkpoint
    messages_after = len(session.get_messages())
    
    assert messages_after < messages_before
    print(f"✓ Restored checkpoint (messages: {messages_before} → {messages_after})")
    
    # Test serialization
    data = session.to_dict()
    restored = SessionState.from_dict(data)
    assert restored.session_id == session.session_id
    assert len(restored.context.messages) == len(session.context.messages)
    print("✓ Session serialization working")


def test_session_manager():
    """Test session manager."""
    print("\n=== Testing Session Manager ===")
    
    # Use temp directory for testing
    temp_dir = Path("/tmp/chatta_test_sessions")
    temp_dir.mkdir(exist_ok=True)
    
    # Disable auto-save for testing to avoid hanging
    manager = SessionManager(storage_dir=temp_dir, auto_save=False)
    
    # Create sessions
    session1 = manager.create_session("claude-desktop")
    session2 = manager.create_session("claude-code")
    
    print(f"Created sessions: {session1[:8]}..., {session2[:8]}...")
    
    # Get session and modify
    session = manager.get_session(session1)
    if session:
        session.add_message("user", "Test message")
        session.context.interruption_count = 2
        session.create_checkpoint("Test checkpoint")
    
    # List sessions
    all_sessions = manager.list_sessions()
    desktop_sessions = manager.list_sessions(platform="claude-desktop")
    
    assert len(all_sessions) >= 2
    assert len(desktop_sessions) >= 1
    print(f"✓ Found {len(all_sessions)} total sessions")
    print(f"✓ Found {len(desktop_sessions)} desktop sessions")
    
    # Test persistence
    manager.save_all()
    
    # Check files created
    session_files = list(temp_dir.glob("*.json"))
    assert len(session_files) >= 2
    print(f"✓ Saved {len(session_files)} session files")
    
    # Test loading
    manager2 = SessionManager(storage_dir=temp_dir, auto_save=False)
    loaded_sessions = manager2.list_sessions()
    assert len(loaded_sessions) == len(all_sessions)
    print(f"✓ Loaded {len(loaded_sessions)} sessions from disk")
    
    # Test termination
    manager.terminate_session(session1)
    remaining = manager.list_sessions()
    assert len(remaining) < len(all_sessions)
    print(f"✓ Terminated session, {len(remaining)} remaining")
    
    # Cleanup
    manager.shutdown()
    manager2.shutdown()
    
    # Clean test files
    for f in temp_dir.glob("*.json"):
        f.unlink()
    temp_dir.rmdir()


def test_session_expiry():
    """Test session expiry detection."""
    print("\n=== Testing Session Expiry ===")
    
    session = SessionState("expiry_test", "test")
    
    # Fresh session should not be expired
    assert not session.is_expired(timeout_minutes=30)
    print("✓ Fresh session not expired")
    
    # Manually set old timestamp
    from datetime import datetime, timedelta
    session.metadata.last_active = datetime.now() - timedelta(minutes=31)
    
    assert session.is_expired(timeout_minutes=30)
    print("✓ Old session detected as expired")
    
    # Update activity
    session.update_activity()
    assert not session.is_expired(timeout_minutes=30)
    print("✓ Updated session not expired")


def test_error_recovery():
    """Test error recovery scenarios."""
    print("\n=== Testing Error Recovery ===")
    
    session = SessionState("recovery_test", "test")
    
    # Simulate conversation
    session.add_message("user", "Start conversation")
    session.add_message("assistant", "Response 1")
    session.create_checkpoint("Good state")
    
    # Simulate errors
    session.context.error_count = 5
    session.add_message("error", "Something went wrong")
    session.set_status(SessionStatus.ERROR)
    
    print(f"Error state: {session.context.error_count} errors")
    
    # Recover from checkpoint
    success = session.restore_checkpoint()
    assert success
    assert session.context.error_count == 0
    assert len(session.get_messages()) == 2
    print("✓ Recovered from checkpoint successfully")


def test_concurrent_access():
    """Test concurrent session access."""
    print("\n=== Testing Concurrent Access ===")
    
    import threading
    
    session = SessionState("concurrent_test", "test")
    
    def add_messages(thread_id):
        for i in range(10):
            session.add_message("user", f"Thread {thread_id} message {i}")
            time.sleep(0.001)
    
    # Start multiple threads
    threads = []
    for i in range(3):
        t = threading.Thread(target=add_messages, args=(i,))
        threads.append(t)
        t.start()
    
    # Wait for completion
    for t in threads:
        t.join()
    
    messages = session.get_messages()
    assert len(messages) == 30
    print(f"✓ Concurrent access: {len(messages)} messages added")


def main():
    """Run all tests."""
    print("=" * 60)
    print("SESSION STATE MANAGEMENT TESTS")
    print("=" * 60)
    
    test_session_metadata()
    test_session_state()
    test_session_manager()
    test_session_expiry()
    test_error_recovery()
    test_concurrent_access()
    
    print("\n" + "=" * 60)
    print("✓ All session state tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()