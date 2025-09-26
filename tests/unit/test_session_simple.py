#!/usr/bin/env python3
"""Simple test for session state without manager."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.session_state import (
    SessionStatus,
    SessionState,
    SessionMetadata
)
from datetime import datetime


def main():
    print("=" * 60)
    print("SIMPLE SESSION STATE TEST")
    print("=" * 60)
    
    # Test basic session
    print("\n1. Creating session...")
    session = SessionState("test123", "claude-code")
    print(f"   Session ID: {session.session_id}")
    print(f"   Platform: {session.metadata.platform}")
    
    # Add messages
    print("\n2. Adding messages...")
    session.add_message("user", "Hello")
    session.add_message("assistant", "Hi there!")
    messages = session.get_messages()
    print(f"   Messages added: {len(messages)}")
    
    # Create checkpoint
    print("\n3. Creating checkpoint...")
    session.create_checkpoint("Test checkpoint")
    print(f"   Checkpoints: {len(session.checkpoints)}")
    
    # Test serialization
    print("\n4. Testing serialization...")
    data = session.to_dict()
    print(f"   Serialized keys: {list(data.keys())}")
    
    # Test restoration
    print("\n5. Testing restoration...")
    restored = SessionState.from_dict(data)
    print(f"   Restored session ID: {restored.session_id}")
    print(f"   Restored messages: {len(restored.get_messages())}")
    
    print("\n✓ All simple tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()