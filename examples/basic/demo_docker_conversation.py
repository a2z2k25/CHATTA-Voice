#!/usr/bin/env python3
"""
CHATTA Docker Services Demo
Demonstrates voice conversation using the Docker-based STT/TTS services
This uses the existing CHATTA infrastructure with our Docker endpoints
"""
import os
import asyncio
import requests
import time

def check_services():
    """Check if Docker services are running"""
    services = {
        "Whisper STT": "http://localhost:8880/health",
        "Kokoro TTS": "http://localhost:7888/health",
    }
    
    all_ready = True
    for name, url in services.items():
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"✅ {name} is ready")
            else:
                print(f"❌ {name} returned status {r.status_code}")
                all_ready = False
        except Exception as e:
            print(f"❌ {name} is not responding: {e}")
            all_ready = False
    
    return all_ready

async def demo_conversation():
    """
    Demo conversation using CHATTA's existing voice infrastructure
    with our Docker services
    """
    print("\n" + "="*60)
    print("🎙️  CHATTA Docker Services Voice Demo")
    print("="*60)
    print("\nThis demo uses CHATTA's built-in voice conversation system")
    print("with our local Docker STT/TTS services.\n")
    
    # Check services first
    if not check_services():
        print("\n⚠️  Please start Docker services first:")
        print("   docker-compose up -d")
        return
    
    print("\n" + "-"*60)
    
    # Set environment variables to use our Docker services
    os.environ["STT_BASE_URL"] = "http://localhost:8880/v1"
    os.environ["TTS_BASE_URL"] = "http://localhost:7888/v1"
    os.environ["PREFER_LOCAL"] = "true"
    
    # Import CHATTA's voice conversation system
    try:
        from voice_mode.tools.converse import voice_converse
        from voice_mode.providers import provider_registry
        
        # Force refresh of provider registry to pick up our Docker services
        await provider_registry.discover_endpoints()
        
        print("📊 Available voice services:")
        endpoints = await provider_registry.get_all_endpoints()
        for ep in endpoints:
            if ep.is_available:
                print(f"   ✅ {ep.base_url} - {ep.provider_type}")
        
        print("\n" + "-"*60)
        print("\n🎤 Starting voice conversation...")
        print("   - Kokoro will greet you")
        print("   - You can speak naturally")
        print("   - Say 'goodbye' to end\n")
        
        # Start with a greeting from Kokoro
        result = await voice_converse(
            message="Hello! I'm CHATTA, your voice assistant powered by local Docker services. I can hear you through Whisper and speak to you through Kokoro. How can I help you today?",
            voice="af_alloy",  # Kokoro voice
            wait_for_response=True,  # Wait for user to respond
            transport="microphone"  # Use local microphone
        )
        
        print(f"\n📝 You said: {result.get('user_response', 'No response detected')}")
        
        # Continue conversation based on response
        if result.get('user_response'):
            response_text = result['user_response'].lower()
            
            if 'test' in response_text:
                await voice_converse(
                    message="Great! The voice system is working perfectly. I can hear you clearly through Whisper and you can hear me through Kokoro. What else would you like to test?",
                    voice="af_alloy",
                    wait_for_response=False
                )
            elif 'hello' in response_text or 'hi' in response_text:
                await voice_converse(
                    message="Hello there! It's wonderful to hear from you. The Docker services are working beautifully. Feel free to ask me anything or just chat!",
                    voice="af_alloy",
                    wait_for_response=False
                )
            else:
                await voice_converse(
                    message=f"I heard you say: {result['user_response']}. That's interesting! The voice pipeline is working great with our local services.",
                    voice="af_alloy",
                    wait_for_response=False
                )
        
        print("\n" + "="*60)
        print("🎉 Demo complete! Voice services are working!")
        print("="*60)
        
    except ImportError as e:
        print(f"\n❌ Error: CHATTA voice_mode not found")
        print(f"   Details: {e}")
        print("\n📦 To use CHATTA's voice system, install it first:")
        print("   pip install -e .")
        print("   # or")
        print("   uv pip install -e .")
    except Exception as e:
        print(f"\n❌ Error during conversation: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point"""
    print("🎤 CHATTA Docker Services Integration")
    print("-" * 40)
    
    # Simple fallback demo if CHATTA not available
    if not os.path.exists("voice_mode"):
        print("\n📝 Running simple API test instead...\n")
        
        # Test TTS
        print("Testing Kokoro TTS...")
        response = requests.post(
            "http://localhost:7888/v1/audio/speech",
            json={
                "input": "Hello from Docker services!",
                "voice": "af_alloy",
                "model": "tts-1"
            }
        )
        if response.status_code == 200:
            print("✅ TTS working - generated audio")
            # Save for testing
            with open("test_output.wav", "wb") as f:
                f.write(response.content)
            print("   Saved to test_output.wav")
        
        # Test STT with a simple file
        print("\nFor STT testing, provide an audio file to:")
        print("curl -X POST http://localhost:8880/v1/audio/transcriptions \\")
        print("  -F 'file=@your_audio.wav' -F 'model=whisper-1'")
        
    else:
        # Run the full CHATTA demo
        asyncio.run(demo_conversation())

if __name__ == "__main__":
    main()