#!/usr/bin/env python3
"""User feedback collection system for VoiceMode."""

import asyncio
import json
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Set
import hashlib
import logging

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of user feedback."""
    BUG_REPORT = auto()
    FEATURE_REQUEST = auto()
    USABILITY_ISSUE = auto()
    PERFORMANCE_FEEDBACK = auto()
    AUDIO_QUALITY = auto()
    SATISFACTION_RATING = auto()
    GENERAL_COMMENT = auto()
    CRASH_REPORT = auto()


class FeedbackPriority(Enum):
    """Priority levels for feedback."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class FeedbackStatus(Enum):
    """Status of feedback processing."""
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    DUPLICATE = "duplicate"


class FeedbackSentiment(Enum):
    """Sentiment analysis of feedback."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


@dataclass
class FeedbackContext:
    """Context information when feedback was submitted."""
    app_version: str = ""
    platform: str = ""
    python_version: str = ""
    session_duration: float = 0.0
    active_features: List[str] = field(default_factory=list)
    error_context: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, float]] = None
    user_session_id: Optional[str] = None


@dataclass
class FeedbackItem:
    """Individual feedback item from user."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: FeedbackType = FeedbackType.GENERAL_COMMENT
    title: str = ""
    description: str = ""
    user_id: Optional[str] = None
    priority: FeedbackPriority = FeedbackPriority.MEDIUM
    status: FeedbackStatus = FeedbackStatus.SUBMITTED
    sentiment: Optional[FeedbackSentiment] = None
    context: FeedbackContext = field(default_factory=FeedbackContext)
    tags: Set[str] = field(default_factory=set)
    attachments: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolution_notes: str = ""
    votes: int = 0
    related_feedback: List[str] = field(default_factory=list)
    contact_info: Optional[str] = None


@dataclass
class FeedbackStats:
    """Statistics about collected feedback."""
    total_feedback: int = 0
    by_type: Dict[FeedbackType, int] = field(default_factory=dict)
    by_priority: Dict[FeedbackPriority, int] = field(default_factory=dict)
    by_status: Dict[FeedbackStatus, int] = field(default_factory=dict)
    by_sentiment: Dict[FeedbackSentiment, int] = field(default_factory=dict)
    average_rating: float = 0.0
    resolution_time: timedelta = field(default_factory=lambda: timedelta(0))
    common_issues: List[str] = field(default_factory=list)
    user_satisfaction: float = 0.0


class FeedbackCollector:
    """Main feedback collection and management system."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".voice_mode" / "feedback.db"
        self.feedback_items: Dict[str, FeedbackItem] = {}
        self.listeners: List[Callable[[FeedbackItem], None]] = []
        self.auto_categorize = True
        self.sentiment_analysis = True
        self.duplicate_detection = True
        
        # Initialize database
        self._init_database()
        
        # Load existing feedback
        self._load_feedback()
    
    def _init_database(self):
        """Initialize SQLite database for feedback storage."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    user_id TEXT,
                    priority INTEGER,
                    status TEXT,
                    sentiment TEXT,
                    context TEXT,
                    tags TEXT,
                    attachments TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    resolved_at TEXT,
                    resolution_notes TEXT,
                    votes INTEGER DEFAULT 0,
                    related_feedback TEXT,
                    contact_info TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)
            """)
    
    def _load_feedback(self):
        """Load existing feedback from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM feedback ORDER BY created_at DESC")
                
                for row in cursor:
                    feedback = self._row_to_feedback(row)
                    self.feedback_items[feedback.id] = feedback
        except Exception as e:
            logger.error(f"Failed to load feedback from database: {e}")
    
    def _row_to_feedback(self, row: sqlite3.Row) -> FeedbackItem:
        """Convert database row to FeedbackItem."""
        context_data = json.loads(row["context"]) if row["context"] else {}
        context = FeedbackContext(**context_data)
        
        return FeedbackItem(
            id=row["id"],
            type=FeedbackType[row["type"]],
            title=row["title"],
            description=row["description"] or "",
            user_id=row["user_id"],
            priority=FeedbackPriority(row["priority"]),
            status=FeedbackStatus(row["status"]),
            sentiment=FeedbackSentiment(row["sentiment"]) if row["sentiment"] else None,
            context=context,
            tags=set(json.loads(row["tags"])) if row["tags"] else set(),
            attachments=json.loads(row["attachments"]) if row["attachments"] else [],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            resolution_notes=row["resolution_notes"] or "",
            votes=row["votes"] or 0,
            related_feedback=json.loads(row["related_feedback"]) if row["related_feedback"] else [],
            contact_info=row["contact_info"]
        )
    
    def _feedback_to_row(self, feedback: FeedbackItem) -> Dict[str, Any]:
        """Convert FeedbackItem to database row data."""
        return {
            "id": feedback.id,
            "type": feedback.type.name,
            "title": feedback.title,
            "description": feedback.description,
            "user_id": feedback.user_id,
            "priority": feedback.priority.value,
            "status": feedback.status.value,
            "sentiment": feedback.sentiment.value if feedback.sentiment else None,
            "context": json.dumps(asdict(feedback.context)),
            "tags": json.dumps(list(feedback.tags)),
            "attachments": json.dumps(feedback.attachments),
            "created_at": feedback.created_at.isoformat(),
            "updated_at": feedback.updated_at.isoformat(),
            "resolved_at": feedback.resolved_at.isoformat() if feedback.resolved_at else None,
            "resolution_notes": feedback.resolution_notes,
            "votes": feedback.votes,
            "related_feedback": json.dumps(feedback.related_feedback),
            "contact_info": feedback.contact_info
        }
    
    def _save_feedback(self, feedback: FeedbackItem):
        """Save feedback item to database."""
        try:
            row_data = self._feedback_to_row(feedback)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO feedback (
                        id, type, title, description, user_id, priority, status,
                        sentiment, context, tags, attachments, created_at, updated_at,
                        resolved_at, resolution_notes, votes, related_feedback, contact_info
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row_data["id"], row_data["type"], row_data["title"], row_data["description"],
                    row_data["user_id"], row_data["priority"], row_data["status"],
                    row_data["sentiment"], row_data["context"], row_data["tags"],
                    row_data["attachments"], row_data["created_at"], row_data["updated_at"],
                    row_data["resolved_at"], row_data["resolution_notes"], row_data["votes"],
                    row_data["related_feedback"], row_data["contact_info"]
                ))
        except Exception as e:
            logger.error(f"Failed to save feedback to database: {e}")
    
    async def submit_feedback(
        self,
        feedback_type: FeedbackType,
        title: str,
        description: str = "",
        user_id: Optional[str] = None,
        priority: FeedbackPriority = FeedbackPriority.MEDIUM,
        context: Optional[FeedbackContext] = None,
        tags: Optional[Set[str]] = None,
        attachments: Optional[List[str]] = None,
        contact_info: Optional[str] = None
    ) -> FeedbackItem:
        """Submit new feedback item."""
        feedback = FeedbackItem(
            type=feedback_type,
            title=title,
            description=description,
            user_id=user_id,
            priority=priority,
            context=context or FeedbackContext(),
            tags=tags or set(),
            attachments=attachments or [],
            contact_info=contact_info
        )
        
        # Auto-categorization
        if self.auto_categorize:
            await self._auto_categorize_feedback(feedback)
        
        # Sentiment analysis
        if self.sentiment_analysis:
            feedback.sentiment = await self._analyze_sentiment(feedback)
        
        # Duplicate detection
        if self.duplicate_detection:
            duplicates = await self._find_duplicates(feedback)
            if duplicates:
                feedback.related_feedback = [d.id for d in duplicates]
        
        # Store feedback
        self.feedback_items[feedback.id] = feedback
        self._save_feedback(feedback)
        
        # Notify listeners
        for listener in self.listeners:
            try:
                listener(feedback)
            except Exception as e:
                logger.error(f"Feedback listener error: {e}")
        
        return feedback
    
    async def _auto_categorize_feedback(self, feedback: FeedbackItem):
        """Automatically categorize feedback based on content."""
        content = f"{feedback.title} {feedback.description}".lower()
        
        # Add relevant tags based on keywords
        keyword_tags = {
            "audio": ["microphone", "speaker", "sound", "voice", "hearing"],
            "performance": ["slow", "lag", "delay", "fast", "speed", "memory"],
            "bug": ["error", "crash", "broken", "issue", "problem", "fail"],
            "ui": ["interface", "display", "screen", "button", "menu"],
            "voice": ["speech", "tts", "stt", "recognition", "synthesis"],
            "keyboard": ["shortcut", "hotkey", "key", "typing"],
            "setup": ["install", "configure", "setup", "initialization"]
        }
        
        for tag, keywords in keyword_tags.items():
            if any(keyword in content for keyword in keywords):
                feedback.tags.add(tag)
        
        # Auto-adjust priority based on severity words
        severity_words = {
            FeedbackPriority.CRITICAL: ["crash", "broken", "unusable", "critical", "severe"],
            FeedbackPriority.HIGH: ["major", "important", "urgent", "significant"],
            FeedbackPriority.MEDIUM: ["minor", "moderate", "normal"],
            FeedbackPriority.LOW: ["trivial", "cosmetic", "enhancement", "suggestion"]
        }
        
        for priority, words in severity_words.items():
            if any(word in content for word in words):
                if priority.value > feedback.priority.value:
                    feedback.priority = priority
                break
    
    async def _analyze_sentiment(self, feedback: FeedbackItem) -> FeedbackSentiment:
        """Analyze sentiment of feedback content."""
        content = f"{feedback.title} {feedback.description}".lower()
        
        positive_words = ["good", "great", "excellent", "love", "like", "amazing", "perfect", "helpful"]
        negative_words = ["bad", "terrible", "hate", "broken", "annoying", "frustrating", "awful", "useless"]
        
        positive_count = sum(1 for word in positive_words if word in content)
        negative_count = sum(1 for word in negative_words if word in content)
        
        if positive_count > negative_count:
            return FeedbackSentiment.POSITIVE if positive_count > negative_count * 2 else FeedbackSentiment.MIXED
        elif negative_count > positive_count:
            return FeedbackSentiment.NEGATIVE if negative_count > positive_count * 2 else FeedbackSentiment.MIXED
        else:
            return FeedbackSentiment.NEUTRAL
    
    async def _find_duplicates(self, feedback: FeedbackItem) -> List[FeedbackItem]:
        """Find potential duplicate feedback items."""
        duplicates = []
        
        # Simple similarity check based on title and type
        for existing in self.feedback_items.values():
            if existing.id == feedback.id:
                continue
                
            if existing.type == feedback.type:
                title_similarity = self._calculate_similarity(feedback.title, existing.title)
                if title_similarity > 0.8:
                    duplicates.append(existing)
        
        return duplicates
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        if not text1 or not text2:
            return 0.0
        
        # Simple character-based similarity
        common_chars = sum(1 for c in text1.lower() if c in text2.lower())
        max_len = max(len(text1), len(text2))
        
        return common_chars / max_len if max_len > 0 else 0.0
    
    def get_feedback(self, feedback_id: str) -> Optional[FeedbackItem]:
        """Get specific feedback item by ID."""
        return self.feedback_items.get(feedback_id)
    
    def list_feedback(
        self,
        feedback_type: Optional[FeedbackType] = None,
        status: Optional[FeedbackStatus] = None,
        priority: Optional[FeedbackPriority] = None,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[FeedbackItem]:
        """List feedback items with filtering."""
        items = list(self.feedback_items.values())
        
        # Apply filters
        if feedback_type:
            items = [item for item in items if item.type == feedback_type]
        
        if status:
            items = [item for item in items if item.status == status]
        
        if priority:
            items = [item for item in items if item.priority == priority]
        
        if user_id:
            items = [item for item in items if item.user_id == user_id]
        
        # Sort by creation date (newest first) and limit
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items[:limit]
    
    async def update_feedback_status(
        self,
        feedback_id: str,
        status: FeedbackStatus,
        resolution_notes: str = ""
    ) -> bool:
        """Update feedback status and resolution."""
        feedback = self.get_feedback(feedback_id)
        if not feedback:
            return False
        
        feedback.status = status
        feedback.resolution_notes = resolution_notes
        feedback.updated_at = datetime.now()
        
        if status == FeedbackStatus.RESOLVED:
            feedback.resolved_at = datetime.now()
        
        self._save_feedback(feedback)
        return True
    
    def vote_feedback(self, feedback_id: str, increment: int = 1) -> bool:
        """Add vote to feedback item."""
        feedback = self.get_feedback(feedback_id)
        if not feedback:
            return False
        
        feedback.votes += increment
        feedback.updated_at = datetime.now()
        self._save_feedback(feedback)
        return True
    
    def add_listener(self, listener: Callable[[FeedbackItem], None]):
        """Add feedback submission listener."""
        self.listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[FeedbackItem], None]):
        """Remove feedback listener."""
        if listener in self.listeners:
            self.listeners.remove(listener)
    
    def get_statistics(self) -> FeedbackStats:
        """Get feedback collection statistics."""
        items = list(self.feedback_items.values())
        stats = FeedbackStats(total_feedback=len(items))
        
        # Count by type
        for item in items:
            stats.by_type[item.type] = stats.by_type.get(item.type, 0) + 1
            stats.by_priority[item.priority] = stats.by_priority.get(item.priority, 0) + 1
            stats.by_status[item.status] = stats.by_status.get(item.status, 0) + 1
            if item.sentiment:
                stats.by_sentiment[item.sentiment] = stats.by_sentiment.get(item.sentiment, 0) + 1
        
        # Calculate resolution time
        resolved_items = [item for item in items if item.resolved_at]
        if resolved_items:
            total_resolution_time = sum(
                (item.resolved_at - item.created_at).total_seconds()
                for item in resolved_items
            )
            stats.resolution_time = timedelta(seconds=total_resolution_time / len(resolved_items))
        
        # Find common issues (most frequent tags)
        all_tags = {}
        for item in items:
            for tag in item.tags:
                all_tags[tag] = all_tags.get(tag, 0) + 1
        
        stats.common_issues = sorted(all_tags.keys(), key=all_tags.get, reverse=True)[:10]
        
        # Calculate user satisfaction (based on sentiment)
        sentiment_scores = {
            FeedbackSentiment.POSITIVE: 5,
            FeedbackSentiment.MIXED: 3,
            FeedbackSentiment.NEUTRAL: 3,
            FeedbackSentiment.NEGATIVE: 1
        }
        
        total_score = sum(
            sentiment_scores.get(item.sentiment, 3) * (item.votes + 1)
            for item in items if item.sentiment
        )
        total_weight = sum(item.votes + 1 for item in items if item.sentiment)
        
        if total_weight > 0:
            stats.user_satisfaction = total_score / total_weight
        
        return stats
    
    def export_feedback(self, format: str = "json") -> str:
        """Export all feedback data."""
        if format == "json":
            data = {
                "exported_at": datetime.now().isoformat(),
                "total_items": len(self.feedback_items),
                "feedback": [asdict(item) for item in self.feedback_items.values()]
            }
            return json.dumps(data, indent=2, default=str)
        
        # Could add CSV, XML formats here
        raise ValueError(f"Unsupported export format: {format}")


class FeedbackUI:
    """User interface for feedback collection."""
    
    def __init__(self, collector: FeedbackCollector):
        self.collector = collector
        self.current_feedback: Optional[FeedbackItem] = None
    
    async def show_feedback_form(
        self,
        feedback_type: Optional[FeedbackType] = None,
        pre_filled_title: str = "",
        pre_filled_description: str = "",
        context: Optional[FeedbackContext] = None
    ) -> Dict[str, Any]:
        """Show feedback collection form."""
        return {
            "form_id": str(uuid.uuid4()),
            "feedback_types": [t.name.lower().replace("_", " ") for t in FeedbackType],
            "priority_levels": [p.name.lower() for p in FeedbackPriority],
            "pre_filled": {
                "type": feedback_type.name.lower() if feedback_type else "",
                "title": pre_filled_title,
                "description": pre_filled_description
            },
            "context_available": context is not None,
            "optional_fields": ["contact_info", "attachments", "tags"]
        }
    
    async def submit_form_data(
        self,
        form_data: Dict[str, Any],
        context: Optional[FeedbackContext] = None
    ) -> Dict[str, Any]:
        """Process submitted feedback form."""
        try:
            feedback_type = FeedbackType[form_data.get("type", "GENERAL_COMMENT").upper()]
            priority = FeedbackPriority[form_data.get("priority", "MEDIUM").upper()]
            
            tags = set()
            if form_data.get("tags"):
                tags = set(tag.strip() for tag in form_data["tags"].split(","))
            
            feedback = await self.collector.submit_feedback(
                feedback_type=feedback_type,
                title=form_data.get("title", ""),
                description=form_data.get("description", ""),
                user_id=form_data.get("user_id"),
                priority=priority,
                context=context,
                tags=tags,
                attachments=form_data.get("attachments", []),
                contact_info=form_data.get("contact_info")
            )
            
            return {
                "success": True,
                "feedback_id": feedback.id,
                "message": "Thank you for your feedback! We'll review it soon.",
                "estimated_response_time": "1-3 business days"
            }
        
        except Exception as e:
            logger.error(f"Form submission error: {e}")
            return {
                "success": False,
                "error": "Failed to submit feedback. Please try again.",
                "details": str(e)
            }
    
    def get_feedback_status(self, feedback_id: str) -> Dict[str, Any]:
        """Get status of submitted feedback."""
        feedback = self.collector.get_feedback(feedback_id)
        if not feedback:
            return {"error": "Feedback not found"}
        
        return {
            "id": feedback.id,
            "title": feedback.title,
            "status": feedback.status.value,
            "submitted_at": feedback.created_at.isoformat(),
            "updated_at": feedback.updated_at.isoformat(),
            "votes": feedback.votes,
            "resolution_notes": feedback.resolution_notes if feedback.status == FeedbackStatus.RESOLVED else ""
        }
    
    def get_user_feedback_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's submitted feedback."""
        user_feedback = self.collector.list_feedback(user_id=user_id, limit=100)
        
        return {
            "total_submitted": len(user_feedback),
            "by_status": {
                status.value: len([f for f in user_feedback if f.status == status])
                for status in FeedbackStatus
            },
            "recent_feedback": [
                {
                    "id": f.id,
                    "title": f.title,
                    "type": f.type.name.lower(),
                    "status": f.status.value,
                    "submitted_at": f.created_at.isoformat(),
                    "votes": f.votes
                }
                for f in user_feedback[:10]
            ]
        }


# Global feedback system instance
_feedback_collector: Optional[FeedbackCollector] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get or create global feedback collector instance."""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector


def get_feedback_ui() -> FeedbackUI:
    """Get feedback UI instance."""
    return FeedbackUI(get_feedback_collector())