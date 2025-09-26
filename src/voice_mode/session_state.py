"""
Session state management for voice conversations.

This module provides persistent session state management, enabling
conversations to be resumed after interruptions or errors.
"""

import json
import pickle
import threading
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
import hashlib

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status states."""
    ACTIVE = auto()
    PAUSED = auto()
    EXPIRED = auto()
    TERMINATED = auto()
    ERROR = auto()


@dataclass
class SessionMetadata:
    """Metadata for a session."""
    session_id: str
    created_at: datetime
    last_active: datetime
    status: SessionStatus
    platform: str = "unknown"
    user_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'last_active': self.last_active.isoformat(),
            'status': self.status.name,
            'platform': self.platform,
            'user_id': self.user_id,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMetadata':
        """Create from dictionary."""
        return cls(
            session_id=data['session_id'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_active=datetime.fromisoformat(data['last_active']),
            status=SessionStatus[data['status']],
            platform=data.get('platform', 'unknown'),
            user_id=data.get('user_id'),
            tags=data.get('tags', [])
        )


@dataclass
class ConversationContext:
    """Context for ongoing conversation."""
    messages: List[Dict[str, str]] = field(default_factory=list)
    audio_settings: Dict[str, Any] = field(default_factory=dict)
    voice_preferences: Dict[str, Any] = field(default_factory=dict)
    interruption_count: int = 0
    error_count: int = 0
    total_duration: float = 0.0
    custom_data: Dict[str, Any] = field(default_factory=dict)


class SessionState:
    """Manages individual session state."""
    
    def __init__(self, session_id: str, platform: str = "unknown"):
        """Initialize session state.
        
        Args:
            session_id: Unique session identifier
            platform: Platform name (claude-desktop, claude-code)
        """
        self.session_id = session_id
        self.metadata = SessionMetadata(
            session_id=session_id,
            created_at=datetime.now(),
            last_active=datetime.now(),
            status=SessionStatus.ACTIVE,
            platform=platform
        )
        self.context = ConversationContext()
        self.lock = threading.Lock()
        self.checkpoints: List[Dict[str, Any]] = []
        self.max_checkpoints = 10
        
    def update_activity(self):
        """Update last activity timestamp."""
        with self.lock:
            self.metadata.last_active = datetime.now()
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        with self.lock:
            self.context.messages.append({
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat()
            })
            self.update_activity()
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation messages.
        
        Args:
            limit: Maximum messages to return
            
        Returns:
            List of messages
        """
        with self.lock:
            messages = self.context.messages.copy()
            if limit:
                messages = messages[-limit:]
            return messages
    
    def create_checkpoint(self, label: str = ""):
        """Create state checkpoint.
        
        Args:
            label: Optional checkpoint label
        """
        with self.lock:
            checkpoint = {
                'timestamp': datetime.now().isoformat(),
                'label': label,
                'metadata': self.metadata.to_dict(),
                'context': {
                    'messages': self.context.messages.copy(),
                    'audio_settings': self.context.audio_settings.copy(),
                    'voice_preferences': self.context.voice_preferences.copy(),
                    'interruption_count': self.context.interruption_count,
                    'error_count': self.context.error_count,
                    'total_duration': self.context.total_duration
                }
            }
            
            self.checkpoints.append(checkpoint)
            
            # Trim old checkpoints
            if len(self.checkpoints) > self.max_checkpoints:
                self.checkpoints = self.checkpoints[-self.max_checkpoints:]
            
            logger.info(f"Created checkpoint: {label}")
    
    def restore_checkpoint(self, index: int = -1) -> bool:
        """Restore from checkpoint.
        
        Args:
            index: Checkpoint index (negative for from end)
            
        Returns:
            True if restored successfully
        """
        with self.lock:
            if not self.checkpoints:
                logger.warning("No checkpoints available")
                return False
            
            try:
                checkpoint = self.checkpoints[index]
                
                # Restore metadata
                self.metadata = SessionMetadata.from_dict(checkpoint['metadata'])
                
                # Restore context
                ctx = checkpoint['context']
                self.context.messages = ctx['messages'].copy()
                self.context.audio_settings = ctx['audio_settings'].copy()
                self.context.voice_preferences = ctx['voice_preferences'].copy()
                self.context.interruption_count = ctx['interruption_count']
                self.context.error_count = ctx['error_count']
                self.context.total_duration = ctx['total_duration']
                
                logger.info(f"Restored checkpoint: {checkpoint.get('label', 'unnamed')}")
                return True
                
            except (IndexError, KeyError) as e:
                logger.error(f"Failed to restore checkpoint: {e}")
                return False
    
    def set_status(self, status: SessionStatus):
        """Set session status.
        
        Args:
            status: New status
        """
        with self.lock:
            self.metadata.status = status
            self.update_activity()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session is expired.
        
        Args:
            timeout_minutes: Inactivity timeout in minutes
            
        Returns:
            True if expired
        """
        with self.lock:
            if self.metadata.status == SessionStatus.EXPIRED:
                return True
            
            inactive_time = datetime.now() - self.metadata.last_active
            return inactive_time > timedelta(minutes=timeout_minutes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export session state to dictionary."""
        with self.lock:
            return {
                'metadata': self.metadata.to_dict(),
                'context': {
                    'messages': self.context.messages,
                    'audio_settings': self.context.audio_settings,
                    'voice_preferences': self.context.voice_preferences,
                    'interruption_count': self.context.interruption_count,
                    'error_count': self.context.error_count,
                    'total_duration': self.context.total_duration,
                    'custom_data': self.context.custom_data
                },
                'checkpoints': self.checkpoints
            }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Create session from dictionary."""
        metadata = SessionMetadata.from_dict(data['metadata'])
        session = cls(metadata.session_id, metadata.platform)
        session.metadata = metadata
        
        # Restore context
        ctx = data['context']
        session.context.messages = ctx.get('messages', [])
        session.context.audio_settings = ctx.get('audio_settings', {})
        session.context.voice_preferences = ctx.get('voice_preferences', {})
        session.context.interruption_count = ctx.get('interruption_count', 0)
        session.context.error_count = ctx.get('error_count', 0)
        session.context.total_duration = ctx.get('total_duration', 0.0)
        session.context.custom_data = ctx.get('custom_data', {})
        
        # Restore checkpoints
        session.checkpoints = data.get('checkpoints', [])
        
        return session


class SessionManager:
    """Manages multiple conversation sessions."""
    
    def __init__(self, storage_dir: Optional[Path] = None, auto_save: bool = True):
        """Initialize session manager.
        
        Args:
            storage_dir: Directory for persistent storage
            auto_save: Enable auto-save feature
        """
        self.sessions: Dict[str, SessionState] = {}
        self.storage_dir = storage_dir or Path.home() / '.chatta' / 'sessions'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.auto_save = auto_save
        self.save_interval = 60  # seconds
        self._save_thread = None
        self._running = False
        
        # Load existing sessions
        self._load_sessions()
        
        # Start auto-save thread
        if self.auto_save:
            self._start_auto_save()
    
    def create_session(self, platform: str = "unknown") -> str:
        """Create new session.
        
        Args:
            platform: Platform name
            
        Returns:
            Session ID
        """
        # Generate unique session ID
        session_id = self._generate_session_id()
        
        with self.lock:
            session = SessionState(session_id, platform)
            self.sessions[session_id] = session
            
            # Save immediately
            if self.auto_save:
                self._save_session(session_id)
        
        logger.info(f"Created session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session state or None
        """
        with self.lock:
            return self.sessions.get(session_id)
    
    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        platform: Optional[str] = None
    ) -> List[SessionMetadata]:
        """List available sessions.
        
        Args:
            status: Filter by status
            platform: Filter by platform
            
        Returns:
            List of session metadata
        """
        with self.lock:
            sessions = []
            for session in self.sessions.values():
                metadata = session.metadata
                
                # Apply filters
                if status and metadata.status != status:
                    continue
                if platform and metadata.platform != platform:
                    continue
                
                sessions.append(metadata)
            
            return sessions
    
    def terminate_session(self, session_id: str):
        """Terminate session.
        
        Args:
            session_id: Session to terminate
        """
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].set_status(SessionStatus.TERMINATED)
                
                # Save final state
                if self.auto_save:
                    self._save_session(session_id)
                
                # Remove from active sessions
                del self.sessions[session_id]
                
                logger.info(f"Terminated session: {session_id}")
    
    def cleanup_expired(self, timeout_minutes: int = 30):
        """Clean up expired sessions.
        
        Args:
            timeout_minutes: Inactivity timeout
        """
        with self.lock:
            expired = []
            for session_id, session in self.sessions.items():
                if session.is_expired(timeout_minutes):
                    expired.append(session_id)
            
            for session_id in expired:
                self.sessions[session_id].set_status(SessionStatus.EXPIRED)
                self._save_session(session_id)
                del self.sessions[session_id]
                logger.info(f"Cleaned up expired session: {session_id}")
    
    def save_all(self):
        """Save all active sessions."""
        with self.lock:
            for session_id in self.sessions:
                self._save_session(session_id)
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = str(time.time()).encode()
        return hashlib.sha256(timestamp).hexdigest()[:16]
    
    def _save_session(self, session_id: str):
        """Save session to disk.
        
        Args:
            session_id: Session to save
        """
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        file_path = self.storage_dir / f"{session_id}.json"
        
        try:
            data = session.to_dict()
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
    
    def _load_sessions(self):
        """Load sessions from disk."""
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                session = SessionState.from_dict(data)
                
                # Only load active/paused sessions
                if session.metadata.status in [SessionStatus.ACTIVE, SessionStatus.PAUSED]:
                    self.sessions[session.session_id] = session
                    logger.debug(f"Loaded session: {session.session_id}")
                    
            except Exception as e:
                logger.error(f"Failed to load session from {file_path}: {e}")
    
    def _start_auto_save(self):
        """Start auto-save thread."""
        import threading
        
        def auto_save_loop():
            while self._running:
                time.sleep(self.save_interval)
                if self._running:
                    self.save_all()
        
        self._running = True
        self._save_thread = threading.Thread(target=auto_save_loop, daemon=True)
        self._save_thread.start()
        logger.info("Started auto-save thread")
    
    def shutdown(self):
        """Shutdown session manager."""
        self._running = False
        if self._save_thread:
            self._save_thread.join(timeout=5)
        
        # Final save
        self.save_all()
        logger.info("Session manager shutdown complete")


# Global session manager instance
_manager: Optional[SessionManager] = None


def get_manager(storage_dir: Optional[Path] = None) -> SessionManager:
    """Get global session manager instance.
    
    Args:
        storage_dir: Storage directory (first call only)
        
    Returns:
        Session manager instance
    """
    global _manager
    if _manager is None:
        _manager = SessionManager(storage_dir)
    return _manager


# Example usage
def example_usage():
    """Example of using session management."""
    
    # Get manager
    manager = get_manager()
    
    # Create session
    session_id = manager.create_session(platform="claude-code")
    print(f"Created session: {session_id}")
    
    # Get session
    session = manager.get_session(session_id)
    if session:
        # Add messages
        session.add_message("user", "Hello!")
        session.add_message("assistant", "Hi there!")
        
        # Update settings
        session.context.audio_settings = {
            'sample_rate': 24000,
            'channels': 1
        }
        
        # Create checkpoint
        session.create_checkpoint("After greeting")
        
        # Simulate error
        session.context.error_count += 1
        session.add_message("system", "Error occurred")
        
        # Restore checkpoint
        session.restore_checkpoint()
        
        # Check messages
        messages = session.get_messages()
        print(f"Messages: {len(messages)}")
    
    # List sessions
    sessions = manager.list_sessions(platform="claude-code")
    print(f"Active sessions: {len(sessions)}")
    
    # Cleanup
    manager.cleanup_expired(timeout_minutes=30)
    
    # Shutdown
    manager.shutdown()


if __name__ == "__main__":
    example_usage()