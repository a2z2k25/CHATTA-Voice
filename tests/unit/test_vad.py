#!/usr/bin/env python3
"""Test VAD (Voice Activity Detection) functionality"""

import subprocess
import sys
import os

def test_vad_with_different_settings():
    """Test VAD with various configurations"""
    print("=" * 60)
    print("VAD FUNCTIONALITY TEST")
    print("=" * 60)
    
    tests = [
        {
            "name": "Default VAD (800ms silence threshold)",
            "env": {
                "CHATTA_VAD_DEBUG": "true",
                "CHATTA_AUDIO_FEEDBACK": "true"
            },
            "args": []
        },
        {
            "name": "Aggressive VAD (level 3)",
            "env": {
                "CHATTA_VAD_DEBUG": "true",
                "CHATTA_VAD_AGGRESSIVENESS": "3",
                "CHATTA_AUDIO_FEEDBACK": "true"
            },
            "args": []
        },
        {
            "name": "Longer silence threshold (1500ms)",
            "env": {
                "CHATTA_VAD_DEBUG": "true",
                "CHATTA_SILENCE_THRESHOLD_MS": "1500",
                "CHATTA_AUDIO_FEEDBACK": "true"
            },
            "args": []
        },
        {
            "name": "VAD Disabled (fixed duration)",
            "env": {
                "CHATTA_DISABLE_SILENCE_DETECTION": "true",
                "CHATTA_AUDIO_FEEDBACK": "true"
            },
            "args": ["--duration", "3"]
        }
    ]
    
    for test in tests:
        print(f"\n{'='*40}")
        print(f"Test: {test['name']}")
        print(f"{'='*40}")
        
        env = os.environ.copy()
        env.update(test['env'])
        
        cmd = [
            sys.executable, "-m", "voice_mode.cli",
            "converse",
            "-m", f"Testing: {test['name']}. Please speak and then pause.",
            "--wait"
        ] + test['args']
        
        print(f"Configuration:")
        for key, value in test['env'].items():
            if "VAD" in key or "SILENCE" in key:
                print(f"  {key}: {value}")
        
        print(f"\nRunning test...")
        print("Instructions:")
        print("  1. Wait for the start chime")
        print("  2. Say something like 'Hello, testing VAD'")
        print("  3. Pause and remain silent")
        print("  4. Recording should stop automatically (or after fixed duration)")
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=15)
            
            # Check for VAD debug output
            if "VAD_DEBUG" in result.stderr or "VAD_DEBUG" in result.stdout:
                print("\n✅ VAD debug output detected")
            
            if "Speech detected" in result.stderr:
                print("✅ Speech detection worked")
            
            if "Silence threshold reached" in result.stderr:
                print("✅ Silence detection triggered stop")
            
            if result.returncode == 0:
                print("✅ Test completed successfully")
            else:
                print(f"❌ Test failed with return code: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            print("❌ Test timed out")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("VAD TESTING COMPLETE")
    print("=" * 60)
    print("\nKey observations:")
    print("- Default 800ms silence threshold for natural pauses")
    print("- Aggressiveness levels 0-3 affect sensitivity")
    print("- Can be disabled for fixed duration recording")
    print("- Debug mode shows detailed VAD state changes")

if __name__ == "__main__":
    test_vad_with_different_settings()