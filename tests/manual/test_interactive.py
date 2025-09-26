#!/usr/bin/env python3
"""
Test CHATTA interactive conversation
"""
import subprocess
import time

print("="*60)
print("🎙️  Testing CHATTA Interactive Conversation")
print("="*60)
print("\nThis will:")
print("1. Say a greeting through Kokoro TTS")
print("2. Wait for your voice response (5 seconds)")
print("3. Transcribe what you said with Whisper STT")
print("\nStarting in 3 seconds...")
time.sleep(3)

# Run chatta converse in interactive mode
cmd = [
    "chatta", "converse",
    "-m", "Hello! I'm CHATTA running with Docker services. Please say something after the beep!",
    "--wait",  # Wait for user response
    "-d", "5"  # Listen for 5 seconds
]

print("\n" + "="*60)
print("🎤 Starting voice conversation...")
print("="*60)

result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode == 0:
    print("\n✅ Voice conversation completed successfully!")
    if result.stdout:
        print("\nOutput:")
        print(result.stdout)
else:
    print("\n❌ Error occurred:")
    print(result.stderr)

print("\n💡 You can also run directly in terminal:")
print("   chatta converse")
print("   chatta converse --continuous  # For ongoing conversation")
print("   chatta converse --help        # For all options")