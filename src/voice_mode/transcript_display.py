"""
Transcript display system for real-time conversation visualization.

This module provides plain text transcript display with real-time updates,
replacing collapsed/expandable objects with clear, inline text.
"""

import asyncio
import threading
import time
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import queue
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in transcript."""
    USER = auto()
    ASSISTANT = auto()
    SYSTEM = auto()
    ERROR = auto()


@dataclass
class TranscriptEntry:
    """Single entry in conversation transcript."""
    type: MessageType
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def format_plain(self, show_timestamp: bool = False) -> str:
        """Format as plain text.
        
        Args:
            show_timestamp: Whether to include timestamp
            
        Returns:
            Formatted plain text string
        """
        prefix = {
            MessageType.USER: "You:",
            MessageType.ASSISTANT: "Assistant:",
            MessageType.SYSTEM: "[System]",
            MessageType.ERROR: "[Error]"
        }[self.type]
        
        if show_timestamp:
            time_str = self.timestamp.strftime("%H:%M:%S")
            return f"[{time_str}] {prefix} {self.content}"
        else:
            return f"{prefix} {self.content}"
    
    def format_markdown(self) -> str:
        """Format as markdown.
        
        Returns:
            Formatted markdown string
        """
        prefix = {
            MessageType.USER: "**You:**",
            MessageType.ASSISTANT: "**Assistant:**",
            MessageType.SYSTEM: "_[System]_",
            MessageType.ERROR: "**[Error]**"
        }[self.type]
        
        return f"{prefix} {self.content}"


class TranscriptBuffer:
    """Manages conversation transcript with real-time updates."""
    
    def __init__(self, max_entries: int = 1000):
        """Initialize transcript buffer.
        
        Args:
            max_entries: Maximum entries to keep in memory
        """
        self.entries: List[TranscriptEntry] = []
        self.max_entries = max_entries
        self.lock = threading.Lock()
        self.update_callbacks: List[Callable[[TranscriptEntry], None]] = []
        
    def add_entry(
        self,
        type: MessageType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TranscriptEntry:
        """Add new entry to transcript.
        
        Args:
            type: Type of message
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Created transcript entry
        """
        entry = TranscriptEntry(
            type=type,
            content=content,
            metadata=metadata or {}
        )
        
        with self.lock:
            self.entries.append(entry)
            
            # Trim if needed
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries:]
        
        # Notify callbacks
        for callback in self.update_callbacks:
            try:
                callback(entry)
            except Exception as e:
                logger.error(f"Transcript callback error: {e}")
        
        return entry
    
    def register_update_callback(self, callback: Callable[[TranscriptEntry], None]):
        """Register callback for transcript updates.
        
        Args:
            callback: Function to call on new entries
        """
        self.update_callbacks.append(callback)
    
    def get_entries(
        self,
        limit: Optional[int] = None,
        type_filter: Optional[MessageType] = None
    ) -> List[TranscriptEntry]:
        """Get transcript entries.
        
        Args:
            limit: Maximum entries to return
            type_filter: Filter by message type
            
        Returns:
            List of transcript entries
        """
        with self.lock:
            entries = self.entries.copy()
        
        # Apply filter
        if type_filter:
            entries = [e for e in entries if e.type == type_filter]
        
        # Apply limit
        if limit:
            entries = entries[-limit:]
        
        return entries
    
    def format_plain(
        self,
        show_timestamps: bool = False,
        separator: str = "\n"
    ) -> str:
        """Format entire transcript as plain text.
        
        Args:
            show_timestamps: Include timestamps
            separator: Line separator
            
        Returns:
            Formatted transcript
        """
        entries = self.get_entries()
        lines = [e.format_plain(show_timestamps) for e in entries]
        return separator.join(lines)
    
    def format_markdown(self, separator: str = "\n\n") -> str:
        """Format entire transcript as markdown.
        
        Args:
            separator: Line separator
            
        Returns:
            Formatted transcript
        """
        entries = self.get_entries()
        lines = [e.format_markdown() for e in entries]
        return separator.join(lines)
    
    def clear(self):
        """Clear all entries."""
        with self.lock:
            self.entries.clear()


class StreamingTranscriptWriter:
    """Writes transcript entries character by character for streaming effect."""
    
    def __init__(self, buffer: TranscriptBuffer):
        """Initialize streaming writer.
        
        Args:
            buffer: Transcript buffer to write to
        """
        self.buffer = buffer
        self.current_entry: Optional[TranscriptEntry] = None
        self.accumulated_text = ""
        self.streaming = False
        
    async def stream_text(
        self,
        type: MessageType,
        text_generator,
        char_delay: float = 0.01
    ):
        """Stream text character by character.
        
        Args:
            type: Message type
            text_generator: Async generator yielding text chunks
            char_delay: Delay between characters (seconds)
        """
        self.streaming = True
        self.accumulated_text = ""
        
        # Create initial entry
        self.current_entry = self.buffer.add_entry(type, "")
        
        try:
            async for chunk in text_generator:
                if not self.streaming:
                    break
                
                for char in chunk:
                    if not self.streaming:
                        break
                    
                    self.accumulated_text += char
                    
                    # Update entry
                    with self.buffer.lock:
                        if self.current_entry in self.buffer.entries:
                            self.current_entry.content = self.accumulated_text
                    
                    # Notify callbacks
                    for callback in self.buffer.update_callbacks:
                        try:
                            callback(self.current_entry)
                        except Exception as e:
                            logger.error(f"Streaming callback error: {e}")
                    
                    # Delay for effect
                    if char_delay > 0:
                        await asyncio.sleep(char_delay)
        
        finally:
            self.streaming = False
            self.current_entry = None
    
    def stop_streaming(self):
        """Stop current streaming operation."""
        self.streaming = False


class TranscriptRenderer:
    """Renders transcript for display."""
    
    def __init__(self, buffer: TranscriptBuffer):
        """Initialize renderer.
        
        Args:
            buffer: Transcript buffer to render
        """
        self.buffer = buffer
        self.render_queue = queue.Queue()
        self.rendering = False
        
    def render_to_console(
        self,
        clear_screen: bool = True,
        show_timestamps: bool = False
    ):
        """Render transcript to console.
        
        Args:
            clear_screen: Clear screen before rendering
            show_timestamps: Show timestamps
        """
        if clear_screen:
            print("\033[2J\033[H")  # Clear screen and move cursor to top
        
        print("=" * 60)
        print("CONVERSATION TRANSCRIPT")
        print("=" * 60)
        print()
        
        transcript = self.buffer.format_plain(show_timestamps)
        print(transcript)
        
        print()
        print("=" * 60)
    
    def get_html(self, auto_scroll: bool = True) -> str:
        """Get HTML representation of transcript.
        
        Args:
            auto_scroll: Include auto-scroll JavaScript
            
        Returns:
            HTML string
        """
        entries = self.buffer.get_entries()
        
        html = ['<div class="transcript-container">']
        
        for entry in entries:
            css_class = {
                MessageType.USER: "user-message",
                MessageType.ASSISTANT: "assistant-message",
                MessageType.SYSTEM: "system-message",
                MessageType.ERROR: "error-message"
            }[entry.type]
            
            prefix = {
                MessageType.USER: "You",
                MessageType.ASSISTANT: "Assistant",
                MessageType.SYSTEM: "System",
                MessageType.ERROR: "Error"
            }[entry.type]
            
            html.append(f'<div class="transcript-entry {css_class}">')
            html.append(f'<span class="speaker">{prefix}:</span>')
            html.append(f'<span class="content">{entry.content}</span>')
            html.append('</div>')
        
        html.append('</div>')
        
        if auto_scroll:
            html.append('''
            <script>
            const container = document.querySelector('.transcript-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
            </script>
            ''')
        
        return '\n'.join(html)
    
    def get_json(self) -> List[Dict[str, Any]]:
        """Get JSON representation of transcript.
        
        Returns:
            List of entry dictionaries
        """
        entries = self.buffer.get_entries()
        
        return [
            {
                'type': entry.type.name,
                'content': entry.content,
                'timestamp': entry.timestamp.isoformat(),
                'metadata': entry.metadata
            }
            for entry in entries
        ]


class ConversationTranscript:
    """High-level conversation transcript manager."""
    
    def __init__(self):
        """Initialize conversation transcript."""
        self.buffer = TranscriptBuffer()
        self.writer = StreamingTranscriptWriter(self.buffer)
        self.renderer = TranscriptRenderer(self.buffer)
        
        # Statistics
        self.message_count = {
            MessageType.USER: 0,
            MessageType.ASSISTANT: 0,
            MessageType.SYSTEM: 0,
            MessageType.ERROR: 0
        }
        
        # Register callback to track statistics
        self.buffer.register_update_callback(self._update_stats)
    
    def _update_stats(self, entry: TranscriptEntry):
        """Update statistics on new entry.
        
        Args:
            entry: New transcript entry
        """
        self.message_count[entry.type] += 1
    
    def add_user_message(self, text: str, **metadata) -> TranscriptEntry:
        """Add user message to transcript.
        
        Args:
            text: Message text
            **metadata: Additional metadata
            
        Returns:
            Created entry
        """
        return self.buffer.add_entry(MessageType.USER, text, metadata)
    
    def add_assistant_message(self, text: str, **metadata) -> TranscriptEntry:
        """Add assistant message to transcript.
        
        Args:
            text: Message text
            **metadata: Additional metadata
            
        Returns:
            Created entry
        """
        return self.buffer.add_entry(MessageType.ASSISTANT, text, metadata)
    
    def add_system_message(self, text: str, **metadata) -> TranscriptEntry:
        """Add system message to transcript.
        
        Args:
            text: Message text
            **metadata: Additional metadata
            
        Returns:
            Created entry
        """
        return self.buffer.add_entry(MessageType.SYSTEM, text, metadata)
    
    def add_error_message(self, text: str, **metadata) -> TranscriptEntry:
        """Add error message to transcript.
        
        Args:
            text: Message text
            **metadata: Additional metadata
            
        Returns:
            Created entry
        """
        return self.buffer.add_entry(MessageType.ERROR, text, metadata)
    
    async def stream_assistant_response(self, text_generator):
        """Stream assistant response character by character.
        
        Args:
            text_generator: Async generator yielding text chunks
        """
        await self.writer.stream_text(
            MessageType.ASSISTANT,
            text_generator,
            char_delay=0.005  # Faster for assistant responses
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transcript statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'total_messages': sum(self.message_count.values()),
            'message_counts': self.message_count.copy(),
            'buffer_size': len(self.buffer.entries),
            'max_buffer_size': self.buffer.max_entries
        }
    
    def export(self, format: str = "plain") -> str:
        """Export transcript in specified format.
        
        Args:
            format: Export format (plain, markdown, html, json)
            
        Returns:
            Formatted transcript
        """
        if format == "plain":
            return self.buffer.format_plain(show_timestamps=True)
        elif format == "markdown":
            return self.buffer.format_markdown()
        elif format == "html":
            return self.renderer.get_html()
        elif format == "json":
            import json
            return json.dumps(self.renderer.get_json(), indent=2)
        else:
            raise ValueError(f"Unknown format: {format}")


# Example usage
async def example_conversation():
    """Example conversation with transcript."""
    
    # Create transcript
    transcript = ConversationTranscript()
    
    # Register update callback
    def on_update(entry: TranscriptEntry):
        print(f"New: {entry.format_plain()}")
    
    transcript.buffer.register_update_callback(on_update)
    
    # Simulate conversation
    transcript.add_user_message("Hello, how are you?")
    
    # Stream assistant response
    async def generate_response():
        response = "I'm doing well, thank you for asking! How can I help you today?"
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.1)
    
    await transcript.stream_assistant_response(generate_response())
    
    transcript.add_user_message("What's the weather like?")
    transcript.add_assistant_message("I don't have access to real-time weather data.")
    
    # Show statistics
    print("\nStatistics:", transcript.get_statistics())
    
    # Export
    print("\nPlain text export:")
    print(transcript.export("plain"))


if __name__ == "__main__":
    # Run example
    asyncio.run(example_conversation())