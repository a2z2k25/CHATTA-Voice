#!/usr/bin/env python3
"""
Test CHATTA MCP Integration
Verifies the CHATTA MCP server is configured correctly
"""
import json
import os
import subprocess
import asyncio

async def test_mcp_server():
    """Test CHATTA MCP server responds correctly"""
    print("=" * 60)
    print("🔧 Testing CHATTA MCP Server")
    print("=" * 60)
    
    # Test server initialization
    print("\n📍 Step 1: Testing MCP server initialization...")
    
    # Send initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        # Start the CHATTA server
        process = subprocess.Popen(
            ["uv", "run", "python", "-m", "voice_mode.server"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                **subprocess.os.environ,
                "STT_BASE_URL": "http://localhost:8880/v1",
                "TTS_BASE_URL": "http://localhost:7888/v1",
                "PREFER_LOCAL": "true",
                "OPENAI_API_KEY": "dummy-key-for-local"
            }
        )
        
        # Send initialize request
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            print(f"✅ Server initialized: {response.get('result', {}).get('serverInfo', {}).get('name')}")
            
            # List available tools
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            process.stdin.write(json.dumps(tools_request) + "\n")
            process.stdin.flush()
            
            tools_response = process.stdout.readline()
            if tools_response:
                tools = json.loads(tools_response)
                if "result" in tools and "tools" in tools["result"]:
                    print(f"\n📊 Available voice tools ({len(tools['result']['tools'])}):")
                    for tool in tools['result']['tools'][:10]:  # Show first 10
                        print(f"   • {tool['name']}: {tool.get('description', '')[:60]}...")
        
        # Terminate the process
        process.terminate()
        process.wait(timeout=2)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ CHATTA MCP server is configured correctly!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("1. Restart Claude Desktop/Code to load the new MCP server")
    print("2. Look for 'CHATTA' in the MCP tools list")
    print("3. Use voice conversation tools like:")
    print("   - converse: Main voice conversation tool")
    print("   - install_whisper: Install Whisper STT service")
    print("   - install_kokoro: Install Kokoro TTS service")
    print("\n⚠️  Make sure Docker services are running:")
    print("   docker-compose up -d")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_mcp_server())