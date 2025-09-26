"""
Help system and documentation interface for VoiceMode.
"""

import re
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import textwrap
from datetime import datetime

logger = logging.getLogger(__name__)


class HelpCategory(Enum):
    """Categories of help content."""
    GETTING_STARTED = auto()
    VOICE_COMMANDS = auto()
    KEYBOARD_SHORTCUTS = auto()
    CONFIGURATION = auto()
    TROUBLESHOOTING = auto()
    API_REFERENCE = auto()
    TUTORIALS = auto()
    FAQ = auto()


class HelpFormat(Enum):
    """Format options for help display."""
    PLAIN_TEXT = auto()
    MARKDOWN = auto()
    STRUCTURED = auto()
    INTERACTIVE = auto()


@dataclass
class HelpTopic:
    """Individual help topic or document."""
    id: str
    title: str
    category: HelpCategory
    content: str
    keywords: List[str] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches_query(self, query: str) -> float:
        """Check if topic matches search query."""
        query_lower = query.lower()
        score = 0.0
        
        if query_lower in self.title.lower():
            score += 0.4
        
        for keyword in self.keywords:
            if query_lower in keyword.lower():
                score += 0.3
                break
        
        if query_lower in self.content.lower():
            score += 0.2
        
        if query_lower in self.category.name.lower():
            score += 0.1
        
        return min(score, 1.0)


@dataclass
class HelpSearchResult:
    """Result from help search."""
    topic: HelpTopic
    confidence: float
    snippet: str = ""
    
    def __post_init__(self):
        """Generate content snippet."""
        if not self.snippet and self.topic.content:
            lines = self.topic.content.strip().split('\n')
            first_paragraph = lines[0] if lines else ""
            
            if len(first_paragraph) > 200:
                self.snippet = first_paragraph[:200] + "..."
            else:
                self.snippet = first_paragraph


class DocumentationBrowser:
    """Interactive documentation browser."""
    
    def __init__(self, help_system: 'HelpSystem'):
        """Initialize browser."""
        self.help_system = help_system
        self.current_topic: Optional[HelpTopic] = None
        self.history: List[str] = []
        self.bookmarks: List[str] = []
        
    def navigate_to(self, topic_id: str) -> Optional[HelpTopic]:
        """Navigate to specific topic."""
        topic = self.help_system.get_topic(topic_id)
        if topic:
            if self.current_topic:
                self.history.append(self.current_topic.id)
            self.current_topic = topic
        return topic
    
    def go_back(self) -> Optional[HelpTopic]:
        """Go back to previous topic."""
        if self.history:
            topic_id = self.history.pop()
            self.current_topic = self.help_system.get_topic(topic_id)
        return self.current_topic
    
    def bookmark_current(self):
        """Bookmark current topic."""
        if self.current_topic and self.current_topic.id not in self.bookmarks:
            self.bookmarks.append(self.current_topic.id)
    
    def get_bookmarks(self) -> List[HelpTopic]:
        """Get bookmarked topics."""
        return [
            topic for topic in [
                self.help_system.get_topic(topic_id) 
                for topic_id in self.bookmarks
            ]
            if topic is not None
        ]


class HelpSystem:
    """Comprehensive help and documentation system."""
    
    def __init__(self):
        """Initialize help system."""
        self.topics: Dict[str, HelpTopic] = {}
        self.categories: Dict[HelpCategory, List[str]] = {
            category: [] for category in HelpCategory
        }
        self.browser = DocumentationBrowser(self)
        
        self.search_count = 0
        self.topic_views = {}
        self.popular_searches = {}
        
        self._load_builtin_topics()
    
    def _load_builtin_topics(self):
        """Load built-in help topics."""
        
        # Getting Started
        self.add_topic(HelpTopic(
            id="getting_started.overview",
            title="Getting Started with VoiceMode",
            category=HelpCategory.GETTING_STARTED,
            content="""VoiceMode enables natural voice conversations with Claude Code through speech-to-text and text-to-speech services.

## Quick Start
1. Start a voice conversation: "start voice" or Ctrl+Shift+V
2. Speak naturally to Claude
3. Use "stop voice" or Space to end the conversation

## Key Features
- Real-time voice recognition
- Natural conversation flow
- Interruption handling
- Multiple voice models
- Keyboard shortcuts
- Customizable preferences""",
            keywords=["start", "begin", "introduction", "voice", "conversation"],
            see_also=["voice_commands.basic", "tutorials.first_conversation"]
        ))
        
        # Voice Commands
        self.add_topic(HelpTopic(
            id="voice_commands.basic",
            title="Basic Voice Commands",
            category=HelpCategory.VOICE_COMMANDS,
            content="""## Voice Control Commands
- "start voice" / "begin voice" - Start voice conversation
- "stop voice" / "end voice" - End voice conversation  
- "mute" / "silence" - Mute audio output
- "unmute" - Unmute audio output

## Conversation Commands
- "help" / "show help" - Display help information
- "status" - Show system status
- "repeat" / "say again" - Repeat last response
- "louder" / "volume up" - Increase volume
- "quieter" / "volume down" - Decrease volume""",
            keywords=["commands", "voice", "control", "speak", "say"],
            see_also=["keyboard_shortcuts.voice", "configuration.voice"],
            examples=["start voice", "help me", "volume up please", "stop voice"]
        ))
        
        # Keyboard Shortcuts
        self.add_topic(HelpTopic(
            id="keyboard_shortcuts.overview",
            title="Keyboard Shortcuts Reference",
            category=HelpCategory.KEYBOARD_SHORTCUTS,
            content="""## Voice Control
- Ctrl+Shift+V - Start/stop voice conversation
- Space (while speaking) - Interrupt and stop
- Ctrl+M - Mute/unmute audio

## Navigation
- Ctrl+H - Show help
- Ctrl+/ - Open command palette
- Ctrl+, - Open preferences
- Esc - Cancel current operation

## System
- Ctrl+Shift+S - Show status
- Ctrl+Q - Quit application
- F1 - Context help""",
            keywords=["shortcuts", "keys", "keyboard", "hotkeys", "bindings"],
            see_also=["voice_commands.basic", "configuration.shortcuts"]
        ))
        
        # Configuration
        self.add_topic(HelpTopic(
            id="configuration.overview",
            title="Configuration Guide",
            category=HelpCategory.CONFIGURATION,
            content="""## Voice Settings
- **TTS Provider**: Choose text-to-speech service (OpenAI, Kokoro, etc.)
- **TTS Voice**: Select voice model and settings
- **STT Provider**: Choose speech-to-text service (Whisper, OpenAI, etc.)
- **Audio Quality**: Configure sample rate and format

## Behavior Settings
- **Wake Word**: Enable/disable "hey claude" activation
- **Interruption**: Configure interruption sensitivity
- **Auto Start**: Start voice mode automatically
- **Conversation Memory**: How long to remember context""",
            keywords=["config", "settings", "preferences", "setup", "customize"],
            see_also=["troubleshooting.audio", "api_reference.config"]
        ))
        
        # FAQ
        self.add_topic(HelpTopic(
            id="faq.common",
            title="Frequently Asked Questions", 
            category=HelpCategory.FAQ,
            content="""## General Questions

**Q: What voice services does VoiceMode support?**
A: VoiceMode supports OpenAI's TTS/STT APIs, local Whisper for speech recognition, Kokoro for text-to-speech, and LiveKit for real-time communication.

**Q: Can I use VoiceMode offline?**  
A: Yes, with local services like Whisper.cpp and Kokoro you can have fully offline voice conversations.

**Q: How do I change the voice model?**
A: Go to preferences (Ctrl+,) and select a different TTS voice or provider in the Voice settings section.""",
            keywords=["faq", "questions", "common", "frequently", "asked"],
            see_also=["troubleshooting.audio", "configuration.overview"]
        ))
    
    def add_topic(self, topic: HelpTopic):
        """Add help topic to system."""
        self.topics[topic.id] = topic
        self.categories[topic.category].append(topic.id)
    
    def get_topic(self, topic_id: str) -> Optional[HelpTopic]:
        """Get help topic by ID."""
        topic = self.topics.get(topic_id)
        if topic:
            self.topic_views[topic_id] = self.topic_views.get(topic_id, 0) + 1
        return topic
    
    def search(
        self, 
        query: str, 
        category: Optional[HelpCategory] = None,
        limit: int = 10
    ) -> List[HelpSearchResult]:
        """Search help topics."""
        self.search_count += 1
        query_lower = query.lower()
        
        self.popular_searches[query_lower] = self.popular_searches.get(query_lower, 0) + 1
        
        results = []
        
        topics_to_search = []
        if category:
            topic_ids = self.categories.get(category, [])
            topics_to_search = [self.topics[tid] for tid in topic_ids]
        else:
            topics_to_search = list(self.topics.values())
        
        for topic in topics_to_search:
            confidence = topic.matches_query(query)
            if confidence > 0.0:
                result = HelpSearchResult(topic=topic, confidence=confidence)
                results.append(result)
        
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[:limit]
    
    def get_category_topics(self, category: HelpCategory) -> List[HelpTopic]:
        """Get all topics in a category."""
        topic_ids = self.categories.get(category, [])
        return [self.topics[tid] for tid in topic_ids]
    
    def get_contextual_help(self, context: str) -> List[HelpTopic]:
        """Get help relevant to current context."""
        context_mapping = {
            "voice_active": ["voice_commands.basic"],
            "preferences": ["configuration.overview"],
            "error": ["faq.common"],
            "first_time": ["getting_started.overview"]
        }
        
        topic_ids = context_mapping.get(context, ["getting_started.overview"])
        return [self.topics[tid] for tid in topic_ids if tid in self.topics]
    
    def format_topic(
        self, 
        topic: HelpTopic, 
        format: HelpFormat = HelpFormat.PLAIN_TEXT,
        include_metadata: bool = False
    ) -> str:
        """Format topic for display."""
        if format == HelpFormat.PLAIN_TEXT:
            output = f"{topic.title}\n{'=' * len(topic.title)}\n\n"
            output += topic.content
            
            if topic.examples:
                output += "\n\nExamples:\n"
                for example in topic.examples:
                    output += f"  • {example}\n"
            
            if topic.see_also:
                output += "\nSee also:\n"
                for ref in topic.see_also:
                    ref_topic = self.topics.get(ref)
                    if ref_topic:
                        output += f"  • {ref_topic.title}\n"
            
            return output
            
        elif format == HelpFormat.MARKDOWN:
            output = f"# {topic.title}\n\n"
            output += topic.content
            
            if topic.examples:
                output += "\n\n## Examples\n"
                for example in topic.examples:
                    output += f"- `{example}`\n"
            
            if topic.see_also:
                output += "\n## See Also\n"
                for ref in topic.see_also:
                    ref_topic = self.topics.get(ref)
                    if ref_topic:
                        output += f"- [{ref_topic.title}](#{ref})\n"
            
            return output
            
        elif format == HelpFormat.STRUCTURED:
            return {
                "id": topic.id,
                "title": topic.title,
                "category": topic.category.name,
                "content": topic.content,
                "keywords": topic.keywords,
                "examples": topic.examples,
                "see_also": topic.see_also,
                "metadata": topic.metadata if include_metadata else {}
            }
        
        return topic.content
    
    def get_command_help(self, command_id: str = None) -> str:
        """Get help for voice commands."""
        if command_id:
            topic = self.get_topic(f"voice_commands.{command_id}")
            if topic:
                return self.format_topic(topic)
            else:
                return f"No help available for command: {command_id}"
        else:
            topic = self.get_topic("voice_commands.basic")
            if topic:
                return self.format_topic(topic)
            else:
                return "Voice command help not available"
    
    def get_quick_help(self) -> str:
        """Get quick help summary."""
        return """VOICEMODE QUICK HELP
===================

Voice Commands:
• "start voice" - Begin voice conversation
• "stop voice" - End voice conversation  
• "help" - Show help information
• "status" - Show system status

Keyboard Shortcuts:
• Ctrl+Shift+V - Start/stop voice
• Ctrl+H - Show help
• Ctrl+, - Open preferences
• Space - Interrupt/stop

Getting Started:
1. Say "start voice" or press Ctrl+Shift+V
2. Speak naturally to Claude
3. Say "stop voice" when done

For detailed help, say "help" or search the documentation."""
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get help system usage statistics."""
        return {
            "total_topics": len(self.topics),
            "topics_by_category": {
                category.name: len(topic_ids) 
                for category, topic_ids in self.categories.items()
            },
            "search_count": self.search_count,
            "most_viewed_topics": sorted(
                self.topic_views.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5],
            "popular_searches": sorted(
                self.popular_searches.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


class InteractiveHelp:
    """Interactive help interface with conversation-style interaction."""
    
    def __init__(self, help_system: HelpSystem):
        """Initialize interactive help."""
        self.help_system = help_system
        self.context_stack = []
        self.conversation_history = []
    
    async def process_help_request(self, request: str) -> str:
        """Process natural language help request."""
        request_lower = request.lower().strip()
        
        if any(word in request_lower for word in ["getting started", "how to start", "begin"]):
            topic = self.help_system.get_topic("getting_started.overview")
            if topic:
                return self.help_system.format_topic(topic)
        
        elif any(word in request_lower for word in ["voice commands", "what can i say"]):
            topic = self.help_system.get_topic("voice_commands.basic")
            if topic:
                return self.help_system.format_topic(topic)
        
        elif any(word in request_lower for word in ["shortcuts", "keyboard", "keys"]):
            topic = self.help_system.get_topic("keyboard_shortcuts.overview")
            if topic:
                return self.help_system.format_topic(topic)
        
        elif any(word in request_lower for word in ["configuration", "settings", "preferences"]):
            topic = self.help_system.get_topic("configuration.overview")
            if topic:
                return self.help_system.format_topic(topic)
        
        else:
            results = self.help_system.search(request, limit=3)
            if results:
                if len(results) == 1:
                    return self.help_system.format_topic(results[0].topic)
                else:
                    response = f"Found {len(results)} help topics:\n\n"
                    for i, result in enumerate(results, 1):
                        response += f"{i}. {result.topic.title}\n"
                        response += f"   {result.snippet}\n\n"
                    response += "Ask about a specific topic for more details."
                    return response
            else:
                return self._get_fallback_help(request)
    
    def _get_fallback_help(self, request: str) -> str:
        """Get fallback help when no specific match found."""
        return f"""I couldn't find specific help for "{request}".

Here's what I can help you with:

• Getting Started - How to use VoiceMode
• Voice Commands - What you can say  
• Keyboard Shortcuts - Key combinations
• Configuration - Settings and preferences
• FAQ - Common questions and answers

Try asking: "help with getting started" or "show me voice commands"

Quick Help: {self.help_system.get_quick_help()}"""


# Global help system instance
_help_system: Optional[HelpSystem] = None

def get_help_system() -> HelpSystem:
    """Get global help system instance."""
    global _help_system
    if _help_system is None:
        _help_system = HelpSystem()
    return _help_system


if __name__ == "__main__":
    # Example usage
    help_system = get_help_system()
    print(f"Loaded {len(help_system.topics)} help topics")
    
    results = help_system.search("voice commands")
    print(f"Found {len(results)} results for 'voice commands'")