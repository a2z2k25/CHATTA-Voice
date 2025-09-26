#!/usr/bin/env python3
"""Conversation context persistence for voice mode.

This module provides persistent storage and retrieval of conversation context,
enabling continuity across sessions and maintaining conversation history.
"""

import json
import logging
import pickle
import sqlite3
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Deque, Tuple
import uuid

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of context entries."""
    USER_INPUT = "user_input"
    ASSISTANT_RESPONSE = "assistant_response"
    SYSTEM_EVENT = "system_event"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    METADATA = "metadata"


class StorageBackend(Enum):
    """Storage backend types."""
    MEMORY = "memory"
    JSON = "json"
    SQLITE = "sqlite"
    HYBRID = "hybrid"  # Memory + persistent


@dataclass
class ContextEntry:
    """Single context entry."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    type: ContextType = ContextType.USER_INPUT
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    profile_id: Optional[str] = None
    session_id: Optional[str] = None
    parent_id: Optional[str] = None  # For threading conversations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
            "profile_id": self.profile_id,
            "session_id": self.session_id,
            "parent_id": self.parent_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        """Create from dictionary."""
        return cls(
            entry_id=data.get("entry_id", str(uuid.uuid4())[:8]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            type=ContextType(data["type"]),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            profile_id=data.get("profile_id"),
            session_id=data.get("session_id"),
            parent_id=data.get("parent_id")
        )


@dataclass
class ConversationContext:
    """Complete conversation context."""
    context_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    entries: List[ContextEntry] = field(default_factory=list)
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_entries: int = 1000
    
    def add_entry(self, entry: ContextEntry) -> None:
        """Add entry to context."""
        self.entries.append(entry)
        self.updated_at = datetime.now()
        
        # Trim if exceeds max
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
    
    def get_recent(self, count: int = 10) -> List[ContextEntry]:
        """Get recent entries."""
        return self.entries[-count:]
    
    def get_by_type(self, entry_type: ContextType) -> List[ContextEntry]:
        """Get entries by type."""
        return [e for e in self.entries if e.type == entry_type]
    
    def clear_old_entries(self, days: int = 7) -> int:
        """Clear entries older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.entries)
        self.entries = [e for e in self.entries if e.timestamp > cutoff]
        return original_count - len(self.entries)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "context_id": self.context_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "entries": [e.to_dict() for e in self.entries],
            "summary": self.summary,
            "tags": self.tags,
            "metadata": self.metadata,
            "max_entries": self.max_entries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContext":
        """Create from dictionary."""
        return cls(
            context_id=data.get("context_id", str(uuid.uuid4())[:12]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            entries=[ContextEntry.from_dict(e) for e in data.get("entries", [])],
            summary=data.get("summary"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            max_entries=data.get("max_entries", 1000)
        )


class MemoryStorage:
    """In-memory context storage."""
    
    def __init__(self, max_contexts: int = 100):
        """Initialize memory storage."""
        self.contexts: Dict[str, ConversationContext] = {}
        self.max_contexts = max_contexts
        self._lock = threading.Lock()
    
    def save(self, context: ConversationContext) -> None:
        """Save context to memory."""
        with self._lock:
            self.contexts[context.context_id] = context
            
            # Trim if needed
            if len(self.contexts) > self.max_contexts:
                # Remove oldest
                oldest = min(self.contexts.values(), key=lambda c: c.updated_at)
                del self.contexts[oldest.context_id]
    
    def load(self, context_id: str) -> Optional[ConversationContext]:
        """Load context from memory."""
        with self._lock:
            return self.contexts.get(context_id)
    
    def list_all(self) -> List[str]:
        """List all context IDs."""
        with self._lock:
            return list(self.contexts.keys())
    
    def delete(self, context_id: str) -> bool:
        """Delete context."""
        with self._lock:
            if context_id in self.contexts:
                del self.contexts[context_id]
                return True
            return False


class JSONStorage:
    """JSON file-based context storage."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize JSON storage."""
        if storage_dir is None:
            storage_dir = Path.home() / ".chatta" / "contexts"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def _get_path(self, context_id: str) -> Path:
        """Get file path for context."""
        return self.storage_dir / f"{context_id}.json"
    
    def save(self, context: ConversationContext) -> None:
        """Save context to JSON file."""
        with self._lock:
            path = self._get_path(context.context_id)
            with open(path, 'w') as f:
                json.dump(context.to_dict(), f, indent=2)
            logger.info(f"Saved context to {path}")
    
    def load(self, context_id: str) -> Optional[ConversationContext]:
        """Load context from JSON file."""
        with self._lock:
            path = self._get_path(context_id)
            if not path.exists():
                return None
            
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                return ConversationContext.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load context: {e}")
                return None
    
    def list_all(self) -> List[str]:
        """List all context IDs."""
        with self._lock:
            contexts = []
            for path in self.storage_dir.glob("*.json"):
                contexts.append(path.stem)
            return contexts
    
    def delete(self, context_id: str) -> bool:
        """Delete context."""
        with self._lock:
            path = self._get_path(context_id)
            if path.exists():
                path.unlink()
                return True
            return False


class SQLiteStorage:
    """SQLite database context storage."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize SQLite storage."""
        if db_path is None:
            db_path = Path.home() / ".chatta" / "contexts.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create contexts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                context_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                summary TEXT,
                data BLOB NOT NULL
            )
        """)
        
        # Create entries table for quick queries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                entry_id TEXT PRIMARY KEY,
                context_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT,
                session_id TEXT,
                FOREIGN KEY (context_id) REFERENCES contexts(context_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_context_updated ON contexts(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entry_context ON entries(context_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entry_type ON entries(type)")
        
        conn.commit()
        conn.close()
    
    def save(self, context: ConversationContext) -> None:
        """Save context to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # Serialize context
            data = pickle.dumps(context)
            
            # Save context
            cursor.execute("""
                INSERT OR REPLACE INTO contexts 
                (context_id, created_at, updated_at, summary, data)
                VALUES (?, ?, ?, ?, ?)
            """, (
                context.context_id,
                context.created_at.isoformat(),
                context.updated_at.isoformat(),
                context.summary,
                data
            ))
            
            # Clear old entries
            cursor.execute("DELETE FROM entries WHERE context_id = ?", (context.context_id,))
            
            # Save entries for querying
            for entry in context.entries:
                cursor.execute("""
                    INSERT INTO entries 
                    (entry_id, context_id, timestamp, type, content, session_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    entry.entry_id,
                    context.context_id,
                    entry.timestamp.isoformat(),
                    entry.type.value,
                    entry.content,
                    entry.session_id
                ))
            
            conn.commit()
            logger.info(f"Saved context {context.context_id} to database")
            
        except Exception as e:
            logger.error(f"Failed to save context: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def load(self, context_id: str) -> Optional[ConversationContext]:
        """Load context from database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT data FROM contexts WHERE context_id = ?",
                (context_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return pickle.loads(row[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to load context: {e}")
            return None
        finally:
            conn.close()
    
    def list_all(self) -> List[str]:
        """List all context IDs."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT context_id FROM contexts ORDER BY updated_at DESC")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def delete(self, context_id: str) -> bool:
        """Delete context."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM entries WHERE context_id = ?", (context_id,))
            cursor.execute("DELETE FROM contexts WHERE context_id = ?", (context_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def search_entries(
        self,
        query: str,
        entry_type: Optional[ContextType] = None,
        limit: int = 50
    ) -> List[Tuple[str, ContextEntry]]:
        """Search entries across all contexts."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            sql = """
                SELECT c.data, e.entry_id 
                FROM entries e
                JOIN contexts c ON e.context_id = c.context_id
                WHERE e.content LIKE ?
            """
            params = [f"%{query}%"]
            
            if entry_type:
                sql += " AND e.type = ?"
                params.append(entry_type.value)
            
            sql += " ORDER BY e.timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            
            results = []
            for row in cursor.fetchall():
                context = pickle.loads(row[0])
                entry_id = row[1]
                
                # Find the specific entry
                for entry in context.entries:
                    if entry.entry_id == entry_id:
                        results.append((context.context_id, entry))
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
        finally:
            conn.close()


class ContextPersistenceManager:
    """Manages conversation context persistence."""
    
    def __init__(
        self,
        backend: StorageBackend = StorageBackend.HYBRID,
        storage_dir: Optional[Path] = None
    ):
        """Initialize context manager.
        
        Args:
            backend: Storage backend to use
            storage_dir: Directory for persistent storage
        """
        self.backend = backend
        self.storage_dir = storage_dir
        
        # Initialize storage backends
        self.memory_storage = MemoryStorage() if backend in [StorageBackend.MEMORY, StorageBackend.HYBRID] else None
        self.json_storage = JSONStorage(storage_dir) if backend == StorageBackend.JSON else None
        self.sqlite_storage = SQLiteStorage(storage_dir / "contexts.db" if storage_dir else None) if backend in [StorageBackend.SQLITE, StorageBackend.HYBRID] else None
        
        # Current context
        self.current_context: Optional[ConversationContext] = None
        
        # Context cache for hybrid mode
        self._context_cache: Dict[str, ConversationContext] = {}
        self._cache_lock = threading.Lock()
        
        logger.info(f"Initialized context manager with {backend.value} backend")
    
    def create_context(
        self,
        profile_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> ConversationContext:
        """Create new conversation context."""
        context = ConversationContext(**kwargs)
        
        # Add initial metadata
        if profile_id:
            context.metadata["profile_id"] = profile_id
        if session_id:
            context.metadata["session_id"] = session_id
        
        # Save to storage
        self._save_context(context)
        
        # Set as current
        self.current_context = context
        
        logger.info(f"Created context {context.context_id}")
        return context
    
    def load_context(self, context_id: str) -> Optional[ConversationContext]:
        """Load existing context."""
        # Check cache first
        with self._cache_lock:
            if context_id in self._context_cache:
                logger.info(f"Loaded context {context_id} from cache")
                self.current_context = self._context_cache[context_id]
                return self.current_context
        
        # Load from storage
        context = self._load_context(context_id)
        
        if context:
            # Cache it
            with self._cache_lock:
                self._context_cache[context_id] = context
            
            self.current_context = context
            logger.info(f"Loaded context {context_id}")
        
        return context
    
    def add_entry(
        self,
        content: str,
        entry_type: ContextType = ContextType.USER_INPUT,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ContextEntry:
        """Add entry to current context."""
        if not self.current_context:
            self.current_context = self.create_context()
        
        entry = ContextEntry(
            type=entry_type,
            content=content,
            metadata=metadata or {},
            **kwargs
        )
        
        self.current_context.add_entry(entry)
        
        # Save context
        self._save_context(self.current_context)
        
        return entry
    
    def get_recent_context(
        self,
        count: int = 10,
        include_system: bool = False
    ) -> List[ContextEntry]:
        """Get recent context entries."""
        if not self.current_context:
            return []
        
        entries = self.current_context.get_recent(count * 2)  # Get more to filter
        
        if not include_system:
            entries = [e for e in entries if e.type != ContextType.SYSTEM_EVENT]
        
        return entries[-count:] if count < len(entries) else entries
    
    def summarize_context(
        self,
        max_tokens: int = 500
    ) -> str:
        """Generate context summary."""
        if not self.current_context:
            return ""
        
        # Simple summary: recent exchanges
        exchanges = []
        entries = self.current_context.get_recent(20)
        
        for entry in entries:
            if entry.type == ContextType.USER_INPUT:
                exchanges.append(f"User: {entry.content[:100]}")
            elif entry.type == ContextType.ASSISTANT_RESPONSE:
                exchanges.append(f"Assistant: {entry.content[:100]}")
        
        summary = "\n".join(exchanges[-10:])  # Last 10 exchanges
        
        # Store summary
        self.current_context.summary = summary
        self._save_context(self.current_context)
        
        return summary
    
    def search_contexts(
        self,
        query: str,
        entry_type: Optional[ContextType] = None,
        limit: int = 10
    ) -> List[Tuple[str, ContextEntry]]:
        """Search across all contexts."""
        if self.sqlite_storage:
            return self.sqlite_storage.search_entries(query, entry_type, limit)
        
        # Fallback to simple search
        results = []
        for context_id in self.list_contexts():
            context = self.load_context(context_id)
            if context:
                for entry in context.entries:
                    if query.lower() in entry.content.lower():
                        if not entry_type or entry.type == entry_type:
                            results.append((context_id, entry))
                            if len(results) >= limit:
                                return results
        
        return results
    
    def list_contexts(self) -> List[str]:
        """List all context IDs."""
        if self.sqlite_storage:
            return self.sqlite_storage.list_all()
        elif self.json_storage:
            return self.json_storage.list_all()
        elif self.memory_storage:
            return self.memory_storage.list_all()
        return []
    
    def delete_context(self, context_id: str) -> bool:
        """Delete context."""
        # Remove from cache
        with self._cache_lock:
            if context_id in self._context_cache:
                del self._context_cache[context_id]
        
        # Delete from storage
        deleted = False
        if self.sqlite_storage:
            deleted = self.sqlite_storage.delete(context_id)
        elif self.json_storage:
            deleted = self.json_storage.delete(context_id)
        elif self.memory_storage:
            deleted = self.memory_storage.delete(context_id)
        
        if deleted:
            logger.info(f"Deleted context {context_id}")
        
        return deleted
    
    def export_context(
        self,
        context_id: str,
        output_path: Path
    ) -> bool:
        """Export context to file."""
        context = self.load_context(context_id)
        if not context:
            return False
        
        try:
            with open(output_path, 'w') as f:
                json.dump(context.to_dict(), f, indent=2)
            logger.info(f"Exported context to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def import_context(self, input_path: Path) -> Optional[ConversationContext]:
        """Import context from file."""
        try:
            with open(input_path, 'r') as f:
                data = json.load(f)
            
            context = ConversationContext.from_dict(data)
            self._save_context(context)
            
            logger.info(f"Imported context {context.context_id}")
            return context
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return None
    
    def _save_context(self, context: ConversationContext) -> None:
        """Save context to configured backend."""
        if self.backend == StorageBackend.MEMORY:
            self.memory_storage.save(context)
        elif self.backend == StorageBackend.JSON:
            self.json_storage.save(context)
        elif self.backend == StorageBackend.SQLITE:
            self.sqlite_storage.save(context)
        elif self.backend == StorageBackend.HYBRID:
            # Save to both memory and SQLite
            if self.memory_storage:
                self.memory_storage.save(context)
            if self.sqlite_storage:
                self.sqlite_storage.save(context)
    
    def _load_context(self, context_id: str) -> Optional[ConversationContext]:
        """Load context from configured backend."""
        if self.backend == StorageBackend.MEMORY:
            return self.memory_storage.load(context_id)
        elif self.backend == StorageBackend.JSON:
            return self.json_storage.load(context_id)
        elif self.backend == StorageBackend.SQLITE:
            return self.sqlite_storage.load(context_id)
        elif self.backend == StorageBackend.HYBRID:
            # Try memory first, then SQLite
            if self.memory_storage:
                context = self.memory_storage.load(context_id)
                if context:
                    return context
            if self.sqlite_storage:
                return self.sqlite_storage.load(context_id)
        
        return None


# Global manager instance
_manager: Optional[ContextPersistenceManager] = None


def get_context_manager(
    backend: StorageBackend = StorageBackend.HYBRID
) -> ContextPersistenceManager:
    """Get or create global context manager."""
    global _manager
    if _manager is None:
        _manager = ContextPersistenceManager(backend=backend)
    return _manager


def example_usage():
    """Example usage of context persistence."""
    # Initialize manager
    manager = get_context_manager(StorageBackend.HYBRID)
    
    # Create new context
    context = manager.create_context(
        profile_id="user-123",
        session_id="session-456"
    )
    
    # Add entries
    manager.add_entry(
        "Hello, how can I help you?",
        ContextType.ASSISTANT_RESPONSE
    )
    
    manager.add_entry(
        "I need help with Python",
        ContextType.USER_INPUT
    )
    
    manager.add_entry(
        "I can help you with Python programming",
        ContextType.ASSISTANT_RESPONSE
    )
    
    # Get recent context
    recent = manager.get_recent_context(5)
    print(f"Recent entries: {len(recent)}")
    
    # Search contexts
    results = manager.search_contexts("Python")
    print(f"Found {len(results)} matches")
    
    # Export context
    export_path = Path.home() / "context_export.json"
    manager.export_context(context.context_id, export_path)
    
    print(f"Context {context.context_id} persisted successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()