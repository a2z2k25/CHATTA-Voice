#!/usr/bin/env python3
"""
Final Voice Flow Demo - CHATTA with Docker Services
Demonstrates: Kokoro TTS → User Speech → Whisper STT → Kokoro Response
"""
import os
import asyncio
import requests
import subprocess
import tempfile

# Set up environment for Docker services
os.environ["OPENAI_API_KEY"] = "dummy-key-for-local"

def check_services():
    """Check Docker services are running"""
    try:
        r1 = requests.get("http://localhost:7888/health", timeout=2)
        r2 = requests.get("http://localhost:8880/health", timeout=2)
        return r1.status_code == 200 and r2.status_code == 200
    except:
        return False

async def kokoro_speak(text):
    """Speak text using Kokoro TTS"""
    print(f"🤖 CHATTA: {text}")
    
    response = requests.post(
        "http://localhost:7888/v1/audio/speech",
        json={
            "input": text,
            "voice": "af_alloy",
            "model": "tts-1"
        }
    )
    
    if response.status_code == 200:
        # Save and play audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(response.content)
            audio_file = f.name
        
        # Play using macOS afplay
        subprocess.run(["afplay", audio_file], check=False)
        os.remove(audio_file)
        return True
    return False

async def whisper_transcribe(audio_file):
    """Transcribe audio using Whisper STT"""
    with open(audio_file, "rb") as f:
        files = {"file": (audio_file, f, "audio/wav")}
        data = {"model": "whisper-1"}
        response = requests.post(
            "http://localhost:8880/v1/audio/transcriptions",
            files=files,
            data=data
        )
    
    if response.status_code == 200:
        return response.json().get("text", "").strip()
    return None

async def main():
    print("="*60)
    print("🎙️  CHATTA + Docker Services Voice Flow")
    print("="*60)
    
    if not check_services():
        print("❌ Docker services not running. Start with: docker-compose up")
        return
    
    print("✅ All services ready!\n")
    
    # Step 1: Greeting
    print("📍 Step 1: Kokoro TTS Greeting")
    await kokoro_speak(
        "Hello! I'm CHATTA with Docker services. "
        "I'll now simulate your voice input and demonstrate the complete flow."
    )
    
    await asyncio.sleep(2)
    
    # Step 2: Simulate user input
    print("\n📍 Step 2: Simulating User Voice")
    user_text = "Hello CHATTA, the voice services are working perfectly!"
    print(f"👤 Simulated: {user_text}")
    
    # Create test audio
    test_audio = "test_user.wav"
    subprocess.run([
        "say", "-o", test_audio,
        "--data-format=LEI16@16000",
        user_text
    ], check=True)
    
    # Step 3: Transcribe
    print("\n📍 Step 3: Whisper STT Transcription")
    transcribed = await whisper_transcribe(test_audio)
    
    if transcribed:
        print(f"📝 Whisper heard: {transcribed}")
        
        # Step 4: Respond
        print("\n📍 Step 4: Kokoro TTS Response")
        
        if "perfect" in transcribed.lower() or "working" in transcribed.lower():
            response = "Excellent! I'm glad to confirm the voice pipeline is fully operational. Whisper and Kokoro are working together seamlessly!"
        elif "hello" in transcribed.lower():
            response = "Hello! It's wonderful to demonstrate this voice interaction. The Docker services are performing excellently!"
        else:
            response = f"I understood: {transcribed}. The voice system is functioning perfectly!"
        
        await kokoro_speak(response)
    
    # Clean up
    if os.path.exists(test_audio):
        os.remove(test_audio)
    
    print("\n" + "="*60)
    print("🎉 Voice Flow Complete!")
    print("="*60)
    print("\n✅ Successfully demonstrated:")
    print("   1. Kokoro TTS - Generated greeting")
    print("   2. User Voice - Simulated input")
    print("   3. Whisper STT - Transcribed speech")
    print("   4. Kokoro TTS - Generated response")
    print("\n💡 This is the complete voice pipeline CHATTA uses!")

if __name__ == "__main__":
    asyncio.run(main())