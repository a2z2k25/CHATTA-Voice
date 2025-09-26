#!/usr/bin/env python3
"""
Simple CHATTA Voice Demo with Docker Services
Uses CHATTA's converse function directly
"""
import os
import asyncio

# Configure environment to use Docker services
os.environ["STT_BASE_URL"] = "http://localhost:8880/v1"
os.environ["TTS_BASE_URL"] = "http://localhost:7888/v1"
os.environ["PREFER_LOCAL"] = "true"
os.environ["OPENAI_API_KEY"] = "dummy-key-for-local"

async def main():
    print("="*60)
    print("🎙️  CHATTA Voice Conversation Demo")
    print("="*60)
    
    try:
        # Import the converse function
        from voice_mode.tools.converse import converse
        print("✅ CHATTA loaded successfully\n")
        
        # Step 1: Greeting with TTS
        print("📍 Step 1: Kokoro speaks a greeting...")
        print("🤖 CHATTA: Hello! Testing the voice pipeline.\n")
        
        result = await converse(
            message="Hello! I'm CHATTA with Docker services. Say something after the tone!",
            voice="af_alloy",
            wait_for_response=True,
            transport="microphone",
            listen_duration=5
        )
        
        # Step 2: Process response
        if result and 'user_response' in result:
            user_text = result['user_response']
            print(f"📝 You said: '{user_text}'\n")
            
            # Step 3: Respond
            print("📍 Step 3: CHATTA responds...")
            
            # Simple response logic
            if any(word in user_text.lower() for word in ['hello', 'hi', 'hey']):
                response = "Hello! Great to hear from you. The voice system is working perfectly!"
            elif 'test' in user_text.lower():
                response = "Test successful! Both Whisper and Kokoro are operational."
            else:
                response = f"I heard: {user_text}. The Docker services are working great!"
            
            await converse(
                message=response,
                voice="af_alloy",
                wait_for_response=False
            )
            
            print(f"🤖 CHATTA: {response}")
            print("\n✅ Voice conversation complete!")
            
        else:
            print("⚠️  No response detected. Testing TTS only...")
            await converse(
                message="If you can hear this, Kokoro TTS is working!",
                voice="af_alloy",
                wait_for_response=False
            )
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting CHATTA with Docker services...\n")
    asyncio.run(main())