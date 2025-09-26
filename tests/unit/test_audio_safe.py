#!/usr/bin/env python3
"""Safe audio feedback test - uses native macOS afplay"""

import asyncio
import sys
import os
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.core import play_chime_start, play_chime_end

def verify_audio_files():
    """Verify audio files exist"""
    audio_dir = Path("voice_mode/audio")
    files = [
        "start_chime.wav",
        "end_chime.wav", 
        "start_chime_bluetooth.wav",
        "end_chime_bluetooth.wav"
    ]
    
    print("Checking audio files...")
    all_exist = True
    for file in files:
        file_path = audio_dir / file
        if file_path.exists():
            print(f"  ✅ {file} exists")
        else:
            print(f"  ❌ {file} missing")
            all_exist = False
    
    return all_exist

def test_direct_afplay():
    """Test playing audio directly with afplay"""
    print("\n1. Testing direct afplay playback...")
    audio_file = Path("voice_mode/audio/start_chime.wav")
    
    try:
        result = subprocess.run(['afplay', str(audio_file)], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ Direct afplay works")
            return True
        else:
            print(f"   ❌ afplay failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def test_chime_functions():
    """Test the chime functions"""
    print("\n2. Testing chime functions (using afplay on macOS)...")
    
    # Test start chime
    print("   Testing start chime...")
    success = await play_chime_start()
    if success:
        print("   ✅ Start chime played")
    else:
        print("   ❌ Start chime failed")
    
    await asyncio.sleep(1)
    
    # Test end chime
    print("   Testing end chime...")
    success = await play_chime_end()
    if success:
        print("   ✅ End chime played")
    else:
        print("   ❌ End chime failed")
    
    return success

async def test_cli_integration():
    """Test through CLI"""
    print("\n3. Testing CLI integration...")
    
    env = os.environ.copy()
    env['CHATTA_AUDIO_FEEDBACK'] = 'true'
    env['VOICEMODE_AUDIO_FEEDBACK'] = 'true'
    
    cmd = [
        sys.executable, "-m", "voice_mode.cli",
        "converse",
        "-m", "Test audio feedback",
        "--wait",
        "--duration", "2",
        "--audio-feedback", "true",
        "--skip-tts",
        "--simulate"  # Simulate mode to avoid actual recording
    ]
    
    print(f"   Running: {' '.join(cmd[-5:])}")
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("   ✅ CLI test passed")
            return True
        else:
            print(f"   ❌ CLI test failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("   ❌ CLI test timed out")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 60)
    print("SAFE AUDIO FEEDBACK TEST")
    print("Using native macOS afplay to avoid crashes")
    print("=" * 60)
    
    # Check files
    files_ok = verify_audio_files()
    if not files_ok:
        print("\n⚠️  Some audio files missing. Run generate_chimes.py first.")
        return
    
    # Test direct playback
    direct_ok = test_direct_afplay()
    
    # Test functions
    funcs_ok = await test_chime_functions()
    
    # Test CLI
    cli_ok = await test_cli_integration()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Audio files present: {'✅' if files_ok else '❌'}")
    print(f"Direct afplay works: {'✅' if direct_ok else '❌'}")
    print(f"Chime functions work: {'✅' if funcs_ok else '❌'}")
    print(f"CLI integration works: {'✅' if cli_ok else '❌'}")
    
    if all([files_ok, direct_ok, funcs_ok, cli_ok]):
        print("\n✅ ALL TESTS PASSED - Audio feedback is working!")
    else:
        print("\n❌ Some tests failed - check the output above")

if __name__ == "__main__":
    asyncio.run(main())