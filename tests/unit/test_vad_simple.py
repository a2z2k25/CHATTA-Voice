#!/usr/bin/env python3
"""Simple VAD test with simulation mode"""

import subprocess
import sys
import os

def test_vad_simulation():
    """Test VAD in simulation mode"""
    print("=" * 60)
    print("VAD SIMULATION TEST")
    print("Testing silence detection without actual recording")
    print("=" * 60)
    
    env = os.environ.copy()
    env.update({
        "CHATTA_VAD_DEBUG": "true",
        "CHATTA_AUDIO_FEEDBACK": "true",
        "CHATTA_SAVE_ALL": "false"
    })
    
    cmd = [
        sys.executable, "-m", "voice_mode.cli",
        "converse",
        "-m", "VAD test in simulation mode",
        "--wait",
        "--simulate",  # Simulate mode
        "--duration", "5"
    ]
    
    print("\nConfiguration:")
    print("  VAD_DEBUG: enabled")
    print("  AUDIO_FEEDBACK: enabled")
    print("  Mode: SIMULATION (no actual recording)")
    
    print("\nRunning simulation...")
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
        
        print("\n--- Output Analysis ---")
        
        # Check stderr for debug output
        if result.stderr:
            if "VAD" in result.stderr:
                print("✅ VAD system active")
            if "webrtcvad not available" in result.stderr:
                print("⚠️  WebRTC VAD not available - will use fixed duration")
            if "Silence detection disabled" in result.stderr:
                print("⚠️  Silence detection is disabled")
            if "Recording with silence detection" in result.stderr:
                print("✅ Silence detection is enabled")
                
        # Check return code
        if result.returncode == 0:
            print("✅ Command executed successfully")
        else:
            print(f"❌ Command failed with code: {result.returncode}")
            
        # Show relevant debug output
        if result.stderr:
            print("\nDebug output:")
            for line in result.stderr.split('\n'):
                if any(keyword in line for keyword in ['VAD', 'silence', 'Speech', 'Recording']):
                    print(f"  {line}")
                    
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_vad_simulation()