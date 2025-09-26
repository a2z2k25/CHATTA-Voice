#!/usr/bin/env python3
"""Test conversation context persistence."""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.context_persistence import (
    ContextType,
    StorageBackend,
    ContextEntry,
    ConversationContext,
    MemoryStorage,
    JSONStorage,
    SQLiteStorage,
    ContextPersistenceManager,
    get_context_manager
)


def test_context_entry():
    """Test context entry creation."""
    print("\n=== Testing Context Entry ===")
    
    entry = ContextEntry(
        type=ContextType.USER_INPUT,
        content="Hello, how are you?",
        metadata={"language": "en"},
        session_id="session-123"
    )
    
    print(f"Entry ID: {entry.entry_id}")
    print(f"Type: {entry.type.value}")
    print(f"Content: {entry.content}")
    print(f"Session: {entry.session_id}")
    print("✓ Context entry created")
    
    # Test serialization
    data = entry.to_dict()
    restored = ContextEntry.from_dict(data)
    assert restored.content == entry.content
    print("✓ Serialization working")


def test_conversation_context():
    """Test conversation context."""
    print("\n=== Testing Conversation Context ===")
    
    context = ConversationContext(max_entries=100)
    
    # Add entries
    for i in range(5):
        entry = ContextEntry(
            type=ContextType.USER_INPUT if i % 2 == 0 else ContextType.ASSISTANT_RESPONSE,
            content=f"Message {i}"
        )
        context.add_entry(entry)
    
    print(f"Context ID: {context.context_id}")
    print(f"Entries: {len(context.entries)}")
    
    # Test recent entries
    recent = context.get_recent(3)
    assert len(recent) == 3
    assert recent[-1].content == "Message 4"
    print("✓ Recent entries working")
    
    # Test by type
    user_entries = context.get_by_type(ContextType.USER_INPUT)
    assert len(user_entries) == 3
    print("✓ Filter by type working")


def test_memory_storage():
    """Test memory storage backend."""
    print("\n=== Testing Memory Storage ===")
    
    storage = MemoryStorage(max_contexts=5)
    
    # Create and save contexts
    contexts = []
    for i in range(3):
        context = ConversationContext()
        context.add_entry(ContextEntry(content=f"Context {i}"))
        storage.save(context)
        contexts.append(context)
    
    print(f"✓ Saved {len(contexts)} contexts")
    
    # Load context
    loaded = storage.load(contexts[0].context_id)
    assert loaded is not None
    assert len(loaded.entries) == 1
    print("✓ Context loading working")
    
    # List all
    all_ids = storage.list_all()
    assert len(all_ids) == 3
    print(f"✓ Listed {len(all_ids)} contexts")
    
    # Delete
    deleted = storage.delete(contexts[0].context_id)
    assert deleted == True
    assert len(storage.list_all()) == 2
    print("✓ Context deletion working")


def test_json_storage():
    """Test JSON storage backend."""
    print("\n=== Testing JSON Storage ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONStorage(storage_dir=tmpdir)
        
        # Create and save context
        context = ConversationContext()
        context.add_entry(ContextEntry(
            type=ContextType.USER_INPUT,
            content="Test message"
        ))
        storage.save(context)
        print("✓ Saved to JSON")
        
        # Verify file exists
        json_file = Path(tmpdir) / f"{context.context_id}.json"
        assert json_file.exists()
        print("✓ JSON file created")
        
        # Load context
        loaded = storage.load(context.context_id)
        assert loaded is not None
        assert len(loaded.entries) == 1
        assert loaded.entries[0].content == "Test message"
        print("✓ Loaded from JSON")
        
        # List all
        all_ids = storage.list_all()
        assert context.context_id in all_ids
        print("✓ Context listing working")


def test_sqlite_storage():
    """Test SQLite storage backend."""
    print("\n=== Testing SQLite Storage ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        storage = SQLiteStorage(db_path=db_path)
        
        # Create and save context
        context = ConversationContext()
        context.add_entry(ContextEntry(
            type=ContextType.USER_INPUT,
            content="Python programming question"
        ))
        context.add_entry(ContextEntry(
            type=ContextType.ASSISTANT_RESPONSE,
            content="I can help with Python"
        ))
        storage.save(context)
        print("✓ Saved to SQLite")
        
        # Load context
        loaded = storage.load(context.context_id)
        assert loaded is not None
        assert len(loaded.entries) == 2
        print("✓ Loaded from SQLite")
        
        # Search entries
        results = storage.search_entries("Python")
        assert len(results) > 0
        print(f"✓ Search found {len(results)} results")
        
        # Delete
        deleted = storage.delete(context.context_id)
        assert deleted == True
        print("✓ Deletion working")


def test_context_manager():
    """Test context persistence manager."""
    print("\n=== Testing Context Manager ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ContextPersistenceManager(
            backend=StorageBackend.HYBRID,
            storage_dir=Path(tmpdir)
        )
        
        # Create context
        context = manager.create_context(
            profile_id="test-profile",
            session_id="test-session"
        )
        print(f"✓ Created context: {context.context_id}")
        
        # Add entries
        manager.add_entry("Hello", ContextType.USER_INPUT)
        manager.add_entry("Hi there!", ContextType.ASSISTANT_RESPONSE)
        manager.add_entry("How are you?", ContextType.USER_INPUT)
        
        # Get recent
        recent = manager.get_recent_context(2)
        assert len(recent) == 2
        # The most recent should be last in the list
        assert recent[-1].content == "How are you?"
        assert recent[0].content == "Hi there!"
        print("✓ Recent context working")
        
        # Save and reload
        context_id = context.context_id
        
        # Create new manager instance
        manager2 = ContextPersistenceManager(
            backend=StorageBackend.HYBRID,
            storage_dir=Path(tmpdir)
        )
        
        # Load context
        loaded = manager2.load_context(context_id)
        assert loaded is not None
        assert len(loaded.entries) == 3
        print("✓ Persistence across instances working")


def test_context_export_import():
    """Test context export and import."""
    print("\n=== Testing Export/Import ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ContextPersistenceManager(
            backend=StorageBackend.JSON,
            storage_dir=Path(tmpdir)
        )
        
        # Create context with data
        context = manager.create_context()
        manager.add_entry("Test message 1", ContextType.USER_INPUT)
        manager.add_entry("Test response", ContextType.ASSISTANT_RESPONSE)
        
        # Export
        export_path = Path(tmpdir) / "export.json"
        success = manager.export_context(context.context_id, export_path)
        assert success == True
        assert export_path.exists()
        print("✓ Context exported")
        
        # Delete original
        manager.delete_context(context.context_id)
        
        # Import
        imported = manager.import_context(export_path)
        assert imported is not None
        assert len(imported.entries) == 2
        print("✓ Context imported")


def test_context_search():
    """Test context searching."""
    print("\n=== Testing Context Search ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "search_test.db"
        manager = ContextPersistenceManager(
            backend=StorageBackend.SQLITE,
            storage_dir=Path(tmpdir)
        )
        
        # Create multiple contexts
        for i in range(3):
            context = manager.create_context()
            manager.add_entry(f"Python question {i}", ContextType.USER_INPUT)
            manager.add_entry(f"Answer about Python {i}", ContextType.ASSISTANT_RESPONSE)
        
        # Search
        results = manager.search_contexts("Python")
        assert len(results) > 0
        print(f"✓ Found {len(results)} search results")
        
        # Search by type
        results = manager.search_contexts("question", ContextType.USER_INPUT)
        assert all(r[1].type == ContextType.USER_INPUT for r in results)
        print("✓ Type-filtered search working")


def test_context_cleanup():
    """Test old entry cleanup."""
    print("\n=== Testing Context Cleanup ===")
    
    context = ConversationContext()
    
    # Add old entries
    old_date = datetime.now() - timedelta(days=10)
    for i in range(5):
        entry = ContextEntry(content=f"Old message {i}")
        entry.timestamp = old_date
        context.entries.append(entry)
    
    # Add recent entries
    for i in range(3):
        context.add_entry(ContextEntry(content=f"Recent message {i}"))
    
    print(f"Total entries: {len(context.entries)}")
    
    # Clean old entries
    removed = context.clear_old_entries(days=7)
    assert removed == 5
    assert len(context.entries) == 3
    print(f"✓ Removed {removed} old entries")


def test_hybrid_storage():
    """Test hybrid storage mode."""
    print("\n=== Testing Hybrid Storage ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create manager with hybrid backend
        manager = ContextPersistenceManager(
            backend=StorageBackend.HYBRID,
            storage_dir=Path(tmpdir)
        )
        
        # Create context
        context = manager.create_context()
        manager.add_entry("Hybrid test", ContextType.USER_INPUT)
        context_id = context.context_id
        
        # Should be in memory
        assert context_id in manager.memory_storage.list_all()
        print("✓ Stored in memory")
        
        # Should also be in SQLite
        assert context_id in manager.sqlite_storage.list_all()
        print("✓ Stored in SQLite")
        
        # Load should use cache
        loaded = manager.load_context(context_id)
        assert loaded is not None
        
        # Clear memory, should still load from SQLite
        manager.memory_storage.delete(context_id)
        manager._context_cache.clear()
        
        loaded = manager.load_context(context_id)
        assert loaded is not None
        print("✓ Hybrid fallback working")


def main():
    """Run all tests."""
    print("=" * 60)
    print("CONTEXT PERSISTENCE TESTS")
    print("=" * 60)
    
    test_context_entry()
    test_conversation_context()
    test_memory_storage()
    test_json_storage()
    test_sqlite_storage()
    test_context_manager()
    test_context_export_import()
    test_context_search()
    test_context_cleanup()
    test_hybrid_storage()
    
    print("\n" + "=" * 60)
    print("✓ All context persistence tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    main()