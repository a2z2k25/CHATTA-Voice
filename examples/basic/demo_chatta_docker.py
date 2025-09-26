#!/usr/bin/env python3
"""
CHATTA + Docker Services Demo
Demonstrates the full CHATTA voice conversation system using Docker STT/TTS services
"""
import os
import asyncio
import sys

# Configure environment to use our Docker services
os.environ["STT_BASE_URL"] = "http://localhost:8880/v1"
os.environ["TTS_BASE_URL"] = "http://localhost:7888/v1"
os.environ["PREFER_LOCAL"] = "true"
os.environ["OPENAI_API_KEY"] = "dummy-key-for-local"  # Not needed for local services

async def main():
    """Main demo function"""
    print("="*60)
    print("🎙️  CHATTA + Docker Services Voice Demo")
    print("="*60)
    
    # Import CHATTA components
    try:
        from voice_mode.tools.converse import converse
        from voice_mode.providers import provider_registry
        from voice_mode.config import SAMPLE_RATE, CHANNELS
        
        print("\n✅ CHATTA voice system loaded successfully")
        
        # Force discovery of our Docker endpoints
        print("\n🔍 Discovering Docker voice services...")
        await provider_registry.discover_endpoints()
        
        # List available endpoints
        endpoints = await provider_registry.get_all_endpoints()
        print("\n📊 Available voice services:")
        for ep in endpoints:
            if ep.is_available:
                print(f"   ✅ {ep.base_url} ({ep.provider_type})")
            else:
                print(f"   ❌ {ep.base_url} ({ep.provider_type}) - unavailable")
        
        print("\n" + "-"*60)
        print("\n🎤 Starting Voice Conversation Demo")
        print("   Audio config: {}Hz, {} channel(s)".format(SAMPLE_RATE, CHANNELS))
        print("\n" + "-"*60)
        
        # Step 1: Greeting from Kokoro
        print("\n📍 Step 1: Kokoro TTS Greeting")
        print("   Speaking through Kokoro TTS...")
        
        result = await converse(
            message="Hello! I'm CHATTA, running with local Docker services. I'm using Kokoro for text-to-speech and Whisper for speech-to-text. Please say something after the tone, and I'll transcribe it for you!",
            voice="af_alloy",  # Kokoro voice
            wait_for_response=True,  # Wait for user response
            transport="microphone",  # Use local microphone
            listen_duration=5  # Listen for 5 seconds
        )
        
        # Step 2: Show what was heard
        if result and result.get('user_response'):
            user_text = result['user_response']
            print(f"\n📝 Whisper STT heard: '{user_text}'")
            
            # Step 3: Respond based on what was heard
            print("\n📍 Step 3: Contextual Response")
            
            # Generate appropriate response
            if "test" in user_text.lower():
                response = "Perfect! The test is successful. Both Whisper and Kokoro are working beautifully together."
            elif "hello" in user_text.lower() or "hi" in user_text.lower():
                response = "Hello to you too! It's wonderful to have this conversation. The Docker services are performing excellently."
            elif "goodbye" in user_text.lower() or "bye" in user_text.lower():
                response = "Goodbye! Thanks for testing the voice system. Have a great day!"
            else:
                response = f"I heard you say: {user_text}. The voice pipeline is working perfectly with our Docker services!"
            
            # Speak the response
            await converse(
                message=response,
                voice="af_alloy",
                wait_for_response=False  # Don't wait for another response
            )
            
            print("\n" + "="*60)
            print("🎉 Voice Conversation Complete!")
            print("="*60)
            print("\n✅ Successfully demonstrated:")
            print("   • Kokoro TTS generated speech")
            print("   • Microphone captured audio")
            print("   • Whisper STT transcribed speech")
            print("   • Contextual response generated")
            
        else:
            print("\n⚠️  No response detected. Make sure your microphone is working.")
            print("   You may need to allow microphone access if prompted.")
            
            # Try a simple TTS test
            print("\n📍 Testing TTS only...")
            await converse(
                message="Testing text-to-speech only. If you can hear this, Kokoro is working!",
                voice="af_alloy",
                wait_for_response=False
            )
            
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\n💡 Make sure CHATTA is installed:")
        print("   pip install -e .")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🎤 CHATTA Docker Integration Demo")
    print("-" * 40)
    print("\nPrerequisites:")
    print("✓ Docker services running (docker-compose up)")
    print("✓ Microphone access enabled")
    print("✓ CHATTA installed (pip install -e .)")
    print("\nStarting demo...\n")
    
    asyncio.run(main())