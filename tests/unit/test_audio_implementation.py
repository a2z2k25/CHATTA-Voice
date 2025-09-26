#!/usr/bin/env python3
"""Test the new audio feedback implementation with pre-generated files"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.core import play_chime_start, play_chime_end

async def test_audio_chimes():
    """Test both start and end chimes"""
    print("=" * 60)
    print("TESTING AUDIO FEEDBACK WITH PRE-GENERATED FILES")
    print("=" * 60)
    
    # Test standard chimes
    print("\n1. Testing STANDARD chimes...")
    print("   Playing start chime (ascending: 800Hz → 1000Hz)...")
    success = await play_chime_start()
    if success:
        print("   ✅ Start chime played successfully")
    else:
        print("   ❌ Start chime failed")
    
    await asyncio.sleep(1)
    
    print("   Playing end chime (descending: 1000Hz → 800Hz)...")
    success = await play_chime_end()
    if success:
        print("   ✅ End chime played successfully")
    else:
        print("   ❌ End chime failed")
    
    await asyncio.sleep(2)
    
    # Test Bluetooth chimes (with longer silence)
    print("\n2. Testing BLUETOOTH chimes (with extra silence)...")
    print("   Playing Bluetooth start chime...")
    success = await play_chime_start(leading_silence=1.0)
    if success:
        print("   ✅ Bluetooth start chime played successfully")
    else:
        print("   ❌ Bluetooth start chime failed")
    
    await asyncio.sleep(1)
    
    print("   Playing Bluetooth end chime...")
    success = await play_chime_end(leading_silence=1.0)
    if success:
        print("   ✅ Bluetooth end chime played successfully")
    else:
        print("   ❌ Bluetooth end chime failed")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\n✅ If you heard all 4 chimes, the implementation is working!")
    print("   - Standard start/end: Quick chimes")
    print("   - Bluetooth start/end: Chimes with longer silence padding")

if __name__ == "__main__":
    asyncio.run(test_audio_chimes())