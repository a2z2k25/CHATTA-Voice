#!/usr/bin/env python3
"""Test audio feedback through MCP server simulation"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_mcp_converse():
    """Test the converse tool with audio feedback"""
    print("Testing MCP converse tool with audio feedback...")
    
    # Set environment variables as MCP would
    os.environ['CHATTA_AUDIO_FEEDBACK'] = 'true'
    os.environ['VOICEMODE_AUDIO_FEEDBACK'] = 'true'
    
    # Import after setting env vars
    from voice_mode.tools.converse import converse
    from voice_mode.config import AUDIO_FEEDBACK_ENABLED
    
    print(f"AUDIO_FEEDBACK_ENABLED: {AUDIO_FEEDBACK_ENABLED}")
    
    try:
        # Test with a simple message and wait for response
        print("\n🎤 Testing converse with audio feedback enabled...")
        result = await converse(
            message="Testing audio feedback. Please say 'test' after the beep.",
            wait_for_response=True,
            duration=3.0,  # Short duration for testing
            audio_feedback=True,  # Explicitly enable
            skip_tts=True  # Skip TTS to focus on recording
        )
        
        print(f"\nResult: {result}")
        
        print("\n✅ MCP audio feedback test complete!")
        print("\nDid you hear:")
        print("1. An ascending chime before recording started?")
        print("2. A descending chime after recording ended?")
        
    except Exception as e:
        print(f"\n❌ Error testing MCP converse: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_converse())