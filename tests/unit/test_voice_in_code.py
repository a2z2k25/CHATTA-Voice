#!/usr/bin/env python3
"""
Direct test of CHATTA voice functions
Run this to test voice without MCP
"""
import os
import asyncio

# Configure for Docker services
os.environ["STT_BASE_URL"] = "http://localhost:8880/v1"
os.environ["TTS_BASE_URL"] = "http://localhost:7888/v1"
os.environ["PREFER_LOCAL"] = "true"
os.environ["OPENAI_API_KEY"] = "dummy-key-for-local"

async def test_voice():
    """Test voice functions directly"""
    print("🎙️ Testing CHATTA Voice Functions")
    print("=" * 50)
    
    # Import core functions
    from voice_mode.core import text_to_speech
    from voice_mode.providers import provider_registry
    
    # Initialize providers
    openai_clients = {}
    
    # Test TTS
    message = "Hello! This is CHATTA testing voice services in Claude Code. The Docker services are working!"
    
    print(f"\n📢 Speaking: '{message}'")
    
    success, _ = await text_to_speech(
        text=message,
        openai_clients=openai_clients,
        tts_model="tts-1",
        tts_voice="af_alloy",
        tts_base_url="http://localhost:7888/v1",
        client_key="tts"
    )
    
    if success:
        print("✅ Voice test successful!")
    else:
        print("❌ Voice test failed")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(test_voice())
    print("\n" + "=" * 50)
    if result:
        print("✅ CHATTA voice is working!")
        print("\n💡 Since direct voice works, the issue is with MCP config.")
        print("   Try completely quitting and restarting Claude Desktop/Code")
    else:
        print("❌ Check that Docker services are running:")
        print("   docker-compose up -d")