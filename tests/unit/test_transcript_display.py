#!/usr/bin/env python3
"""Test transcript display implementation."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.transcript_display import (
    MessageType,
    TranscriptEntry,
    TranscriptBuffer,
    StreamingTranscriptWriter,
    TranscriptRenderer,
    ConversationTranscript
)


def test_transcript_entry():
    """Test transcript entry formatting."""
    print("\n=== Testing Transcript Entry ===")
    
    # Create entries
    user_entry = TranscriptEntry(
        type=MessageType.USER,
        content="Hello, how are you?"
    )
    
    assistant_entry = TranscriptEntry(
        type=MessageType.ASSISTANT,
        content="I'm doing well, thank you!"
    )
    
    # Test plain formatting
    print("Plain format:")
    print(user_entry.format_plain())
    print(assistant_entry.format_plain())
    
    # Test with timestamp
    print("\nWith timestamp:")
    print(user_entry.format_plain(show_timestamp=True))
    
    # Test markdown
    print("\nMarkdown format:")
    print(user_entry.format_markdown())
    print(assistant_entry.format_markdown())


def test_transcript_buffer():
    """Test transcript buffer operations."""
    print("\n=== Testing Transcript Buffer ===")
    
    buffer = TranscriptBuffer(max_entries=5)
    
    # Add entries
    buffer.add_entry(MessageType.USER, "First message")
    buffer.add_entry(MessageType.ASSISTANT, "First response")
    buffer.add_entry(MessageType.USER, "Second message")
    buffer.add_entry(MessageType.ASSISTANT, "Second response")
    buffer.add_entry(MessageType.SYSTEM, "System notification")
    
    # Test retrieval
    entries = buffer.get_entries()
    print(f"Total entries: {len(entries)}")
    
    # Test filtering
    user_entries = buffer.get_entries(type_filter=MessageType.USER)
    print(f"User entries: {len(user_entries)}")
    
    # Test limit
    recent = buffer.get_entries(limit=2)
    print(f"Recent entries: {len(recent)}")
    
    # Test formatting
    print("\nFormatted transcript:")
    print(buffer.format_plain())
    
    # Test overflow
    buffer.add_entry(MessageType.USER, "Overflow test")
    print(f"\nAfter overflow (max 5): {len(buffer.get_entries())} entries")


async def test_streaming_writer():
    """Test streaming transcript writer."""
    print("\n=== Testing Streaming Writer ===")
    
    buffer = TranscriptBuffer()
    writer = StreamingTranscriptWriter(buffer)
    
    # Track updates
    updates = []
    def on_update(entry):
        updates.append(entry.content)
    
    buffer.register_update_callback(on_update)
    
    # Stream text
    async def generate_text():
        text = "This is a streaming test message."
        for word in text.split():
            yield word + " "
            await asyncio.sleep(0.05)
    
    print("Streaming text...")
    await writer.stream_text(
        MessageType.ASSISTANT,
        generate_text(),
        char_delay=0.001
    )
    
    print(f"Updates received: {len(updates)}")
    print(f"Final content: {buffer.get_entries()[-1].content}")


def test_transcript_renderer():
    """Test transcript renderer."""
    print("\n=== Testing Transcript Renderer ===")
    
    buffer = TranscriptBuffer()
    renderer = TranscriptRenderer(buffer)
    
    # Add sample conversation
    buffer.add_entry(MessageType.USER, "What's the weather?")
    buffer.add_entry(MessageType.ASSISTANT, "I don't have weather data.")
    buffer.add_entry(MessageType.ERROR, "Connection error")
    
    # Test console rendering
    print("Console output:")
    renderer.render_to_console(clear_screen=False, show_timestamps=True)
    
    # Test JSON
    json_data = renderer.get_json()
    print(f"\nJSON entries: {len(json_data)}")
    for entry in json_data:
        print(f"  - {entry['type']}: {entry['content'][:30]}...")


async def test_conversation_transcript():
    """Test high-level conversation transcript."""
    print("\n=== Testing Conversation Transcript ===")
    
    transcript = ConversationTranscript()
    
    # Add messages
    transcript.add_user_message("Hello!")
    transcript.add_assistant_message("Hi there!")
    transcript.add_system_message("Connection established")
    transcript.add_error_message("Rate limit exceeded")
    
    # Get statistics
    stats = transcript.get_statistics()
    print(f"Statistics: {stats}")
    
    # Test streaming
    async def generate_response():
        response = "Let me help you with that."
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.05)
    
    print("\nStreaming assistant response...")
    await transcript.stream_assistant_response(generate_response())
    
    # Export formats
    print("\nExport (plain):")
    print(transcript.export("plain"))
    
    print("\nExport (markdown):")
    print(transcript.export("markdown"))


def test_callback_system():
    """Test callback registration and execution."""
    print("\n=== Testing Callback System ===")
    
    buffer = TranscriptBuffer()
    
    # Track callbacks
    callback_count = 0
    def callback(entry):
        nonlocal callback_count
        callback_count += 1
        print(f"Callback {callback_count}: {entry.format_plain()}")
    
    buffer.register_update_callback(callback)
    
    # Trigger callbacks
    buffer.add_entry(MessageType.USER, "Test 1")
    buffer.add_entry(MessageType.ASSISTANT, "Test 2")
    
    print(f"Total callbacks triggered: {callback_count}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("TRANSCRIPT DISPLAY TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_transcript_entry()
    test_transcript_buffer()
    test_transcript_renderer()
    test_callback_system()
    
    # Run async tests
    asyncio.run(test_streaming_writer())
    asyncio.run(test_conversation_transcript())
    
    print("\n" + "=" * 60)
    print("✓ All transcript display tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()