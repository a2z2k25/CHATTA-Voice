#!/usr/bin/env python3
"""Quick test to verify core fixes are working."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PREFER_LOCAL", "true")

async def test_fixes():
    """Test that our fixes are working."""
    print("Testing Core Fixes...")
    print("=" * 50)
    
    # Test 1: Provider Registry Import
    print("\n1. Testing Provider Registry...")
    try:
        from voice_mode.provider_discovery import provider_registry
        await provider_registry.initialize()
        tts_count = len(provider_registry.registry.get('tts', {}))
        stt_count = len(provider_registry.registry.get('stt', {}))
        print(f"   ✅ Provider Registry: {tts_count} TTS, {stt_count} STT")
    except Exception as e:
        print(f"   ❌ Provider Registry: {e}")
    
    # Test 2: TTS Generation
    print("\n2. Testing TTS Generation...")
    try:
        from voice_mode.tools import converse as converse_module
        converse_tool = converse_module.converse
        if hasattr(converse_tool, 'fn'):
            converse = converse_tool.fn
        else:
            converse = converse_tool
        
        result = await converse(
            message="Test TTS generation",
            wait_for_response=False,
            voice="af_alloy"
        )
        if result:
            print("   ✅ TTS Generation: PASS")
    except Exception as e:
        print(f"   ❌ TTS Generation: {e}")
    
    # Test 3: Service Health
    print("\n3. Testing Service Health...")
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            # Kokoro
            try:
                resp = await client.get("http://localhost:7888/health", timeout=2.0)
                if resp.status_code == 200:
                    print("   ✅ Kokoro TTS: ONLINE")
            except:
                print("   ❌ Kokoro TTS: OFFLINE")
            
            # Whisper
            try:
                resp = await client.get("http://localhost:8880/health", timeout=2.0)
                if resp.status_code == 200:
                    print("   ✅ Whisper STT: ONLINE")
            except:
                print("   ❌ Whisper STT: OFFLINE")
    except Exception as e:
        print(f"   ❌ Service Health: {e}")
    
    print("\n" + "=" * 50)
    print("Core fixes validation complete!")

if __name__ == "__main__":
    asyncio.run(test_fixes())