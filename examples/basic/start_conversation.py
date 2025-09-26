#!/usr/bin/env python3
"""Quick script to start a voice conversation with Chatta"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    """Start a voice conversation using the converse tool directly"""
    # Import after path setup
    from voice_mode.tools.converse import converse
    
    print("Starting voice conversation...")
    print("I'll speak a greeting, then listen for your response.")
    print("Press Ctrl+C to stop at any time.\n")
    
    try:
        # Call the converse function directly
        result = await converse.fn(
            message="Hello! I'm ready to help you. Please speak your message after the chime.",
            wait_for_response=True,
            transport="local",  # Use local microphone
            voice="nova",  # Default voice
            listen_duration=10.0  # Listen for up to 10 seconds
        )
        print(f"\nYou said: {result}")
        
        # Continue conversation
        while True:
            response = input("\nYour response (or 'quit' to exit): ")
            if response.lower() == 'quit':
                break
                
            result = await converse.fn(
                message=response,
                wait_for_response=True,
                transport="local",
                voice="nova",
                listen_duration=10.0
            )
            print(f"\nYou said: {result}")
            
    except KeyboardInterrupt:
        print("\n\nConversation ended.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())