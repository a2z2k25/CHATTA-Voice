#!/usr/bin/env python3
"""Test audio feedback through MCP server subprocess"""

import subprocess
import json
import sys
import time

def test_mcp_audio():
    """Test audio through MCP server context"""
    print("=" * 60)
    print("TESTING AUDIO FEEDBACK THROUGH MCP SERVER")
    print("=" * 60)
    
    # Prepare the MCP request for the converse tool
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "converse",
            "arguments": {
                "message": "Test audio feedback through MCP",
                "wait": True,
                "duration": 2,
                "audio_feedback": True,
                "skip_tts": True,
                "simulate": True  # Simulate mode to test without actual recording
            }
        },
        "id": 1
    }
    
    # Start the MCP server as a subprocess
    cmd = [sys.executable, "-m", "voice_mode.server"]
    
    print("\nStarting MCP server and sending request...")
    print("Listen for audio chimes:")
    print("  - Start chime: ascending tones (800Hz → 1000Hz)")
    print("  - End chime: descending tones (1000Hz → 800Hz)")
    print("-" * 40)
    
    try:
        # Start the server
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                **subprocess.os.environ,
                "CHATTA_AUDIO_FEEDBACK": "true",
                "VOICEMODE_AUDIO_FEEDBACK": "true"
            }
        )
        
        # Send the request
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < 5:
            line = proc.stdout.readline()
            if line:
                try:
                    response = json.loads(line)
                    print(f"\nMCP Response: {json.dumps(response, indent=2)}")
                    if "result" in response:
                        break
                except json.JSONDecodeError:
                    pass
        
        # Terminate the server
        proc.terminate()
        proc.wait(timeout=2)
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\n✅ If you heard the chimes, MCP audio is working!")
    print("❌ If not, there may still be subprocess audio issues")

if __name__ == "__main__":
    test_mcp_audio()