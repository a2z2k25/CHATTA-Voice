#!/usr/bin/env python3
"""Simple test to verify audio feedback works in terminal"""

import os
import sys
import subprocess
import time

def test_cli_audio():
    """Test audio feedback using CLI directly"""
    print("=" * 60)
    print("AUDIO FEEDBACK TEST - CLI Mode")
    print("=" * 60)
    
    # Set environment variable
    env = os.environ.copy()
    env['CHATTA_AUDIO_FEEDBACK'] = 'true'
    env['VOICEMODE_AUDIO_FEEDBACK'] = 'true'
    
    print("\n1. Testing with audio feedback ENABLED...")
    print("Listen for:")
    print("  - ASCENDING tones (beep-BEEP) when recording starts")
    print("  - DESCENDING tones (BEEP-beep) when recording ends\n")
    
    # Run the converse command with audio feedback
    cmd = [
        sys.executable, "-m", "voice_mode.cli",
        "converse",
        "-m", "Test with audio feedback. Say something after the beep!",
        "--wait",
        "--duration", "3",
        "--audio-feedback", "true",
        "--skip-tts"  # Skip TTS to focus on recording
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print("-" * 40)
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\n✅ Did you hear the audio chimes?")
    print("   - Start chime: ascending tones (800Hz → 1000Hz)")
    print("   - End chime: descending tones (1000Hz → 800Hz)")
    print("\nIf not, check:")
    print("1. System audio is not muted")
    print("2. Audio output device is available")
    print("3. Try running with higher volume")

if __name__ == "__main__":
    test_cli_audio()