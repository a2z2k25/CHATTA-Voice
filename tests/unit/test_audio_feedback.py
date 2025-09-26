#!/usr/bin/env python3
"""Test audio feedback chimes directly"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_chimes():
    """Test the audio feedback chimes"""
    print("Testing audio feedback chimes...")
    print(f"CHATTA_AUDIO_FEEDBACK env var: {os.getenv('CHATTA_AUDIO_FEEDBACK', 'not set')}")
    print(f"VOICEMODE_AUDIO_FEEDBACK env var: {os.getenv('VOICEMODE_AUDIO_FEEDBACK', 'not set')}")
    
    # Import after path setup
    from voice_mode.core import play_chime_start, play_chime_end
    from voice_mode.config import AUDIO_FEEDBACK_ENABLED
    
    print(f"AUDIO_FEEDBACK_ENABLED config value: {AUDIO_FEEDBACK_ENABLED}")
    
    try:
        # Test start chime
        print("\n🎵 Playing START chime (ascending tones)...")
        result = await play_chime_start()
        print(f"Start chime result: {result}")
        
        # Wait a bit
        await asyncio.sleep(1)
        
        # Test end chime
        print("\n🎵 Playing END chime (descending tones)...")
        result = await play_chime_end()
        print(f"End chime result: {result}")
        
        print("\n✅ Audio feedback test complete!")
        print("\nIf you didn't hear the chimes, possible issues:")
        print("1. Audio output device not available")
        print("2. Volume too low")
        print("3. sounddevice library issues")
        
    except Exception as e:
        print(f"\n❌ Error testing chimes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chimes())