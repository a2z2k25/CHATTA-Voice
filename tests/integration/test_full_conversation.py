#!/usr/bin/env python3
"""Full back-and-forth CHATTA voice conversation test."""

import asyncio
import os
import sys

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure environment for local services
os.environ.setdefault("PREFER_LOCAL", "true")
os.environ.setdefault("CHATTA_AUDIO_FEEDBACK", "true")
os.environ.setdefault("CHATTA_DISABLE_SILENCE_DETECTION", "false")

async def full_conversation():
    """Run a full back-and-forth voice conversation."""
    print("=" * 70)
    print("🎤 CHATTA Full Conversation Test")
    print("=" * 70)
    print()
    
    try:
        # Import and unwrap the converse function
        from voice_mode.tools import converse as converse_module
        
        if hasattr(converse_module, 'converse'):
            converse_tool = converse_module.converse
            # FastMCP FunctionTool has an 'fn' attribute with the actual function
            if hasattr(converse_tool, 'fn'):
                converse = converse_tool.fn
            else:
                converse = converse_tool
        else:
            raise ImportError("Cannot find converse function")
            
        print("✅ CHATTA voice module loaded successfully")
        print()
        
        # Conversation turns
        conversation_turns = [
            {
                "message": "Hello! I'm CHATTA, your voice assistant. I've completed all 48 sprints and I'm ready for a conversation. What's your name?",
                "wait_for_response": True,
                "listen_duration": 4.0
            },
            {
                "message": "Nice to meet you! Tell me, what would you like to talk about today?",
                "wait_for_response": True,
                "listen_duration": 5.0
            },
            {
                "message": "That's interesting! Let me ask you one more question. What's your favorite programming language?",
                "wait_for_response": True,
                "listen_duration": 4.0
            },
            {
                "message": "Great choice! Thanks for testing the CHATTA voice system with me. The full conversation pipeline is working perfectly!",
                "wait_for_response": False
            }
        ]
        
        # Run the conversation
        for i, turn in enumerate(conversation_turns, 1):
            print(f"📍 Turn {i}/{len(conversation_turns)}")
            print("-" * 40)
            print(f"🤖 CHATTA: {turn['message'][:60]}...")
            print()
            
            result = await converse(
                message=turn['message'],
                voice="af_alloy",  # Kokoro voice
                wait_for_response=turn['wait_for_response'],
                listen_duration=turn.get('listen_duration', 5.0)
            )
            
            if turn['wait_for_response'] and result and 'user_response' in result:
                user_text = result['user_response']
                print(f"🎤 You said: '{user_text}'")
                print()
                
                # Adapt next message based on response (for turns 2 and 3)
                if i == 1 and i < len(conversation_turns) - 1:
                    # Personalize greeting with name if detected
                    if user_text:
                        conversation_turns[i]["message"] = f"Nice to meet you, {user_text}! Tell me, what would you like to talk about today?"
                elif i == 2 and i < len(conversation_turns) - 1:
                    # Reference their topic in the next question
                    if user_text:
                        conversation_turns[i]["message"] = f"That's interesting that you want to talk about {user_text}! Let me ask you - what's your favorite programming language?"
                elif i == 3:
                    # Reference their language choice in final message
                    if user_text:
                        conversation_turns[i]["message"] = f"{user_text} is a great choice! Thanks for testing the CHATTA voice system with me. The full conversation pipeline is working perfectly!"
            
            elif turn['wait_for_response']:
                print("⚠️  No response detected")
                print()
            
            # Small pause between turns
            if i < len(conversation_turns):
                await asyncio.sleep(0.5)
        
        print()
        print("=" * 70)
        print("✅ Full conversation test complete!")
        print("=" * 70)
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   Make sure you're in the CHATTA project directory")
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting CHATTA full conversation test...")
    print("📢 Speak clearly when prompted!")
    print()
    asyncio.run(full_conversation())