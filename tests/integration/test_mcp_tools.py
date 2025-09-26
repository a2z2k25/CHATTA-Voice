#!/usr/bin/env python3
"""Test if CHATTA MCP server exposes tools correctly"""
import json
import os
import subprocess
import sys

def test_mcp_tools():
    """Test MCP server tools listing"""
    # Initialize request
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
    
    # List tools request
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        # Start the server
        process = subprocess.Popen(
            [sys.executable, "-m", "voice_mode.server"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                **subprocess.os.environ,
                "STT_BASE_URL": "http://localhost:8880/v1",
                "TTS_BASE_URL": "http://localhost:7888/v1",
                "PREFER_LOCAL": "true"
            }
        )
        
        # Send initialize
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response = process.stdout.readline()
        if response:
            init_result = json.loads(response)
            print("✅ Server initialized successfully")
            
            # Check if tools are mentioned in capabilities
            server_info = init_result.get("result", {}).get("serverInfo", {})
            capabilities = init_result.get("result", {}).get("capabilities", {})
            print(f"   Server: {server_info.get('name')} v{server_info.get('version')}")
            print(f"   Capabilities: {list(capabilities.keys())}")
        
        # Send list tools request
        process.stdin.write(json.dumps(list_tools_request) + "\n")
        process.stdin.flush()
        
        # Read tools response
        response = process.stdout.readline()
        if response:
            tools_result = json.loads(response)
            tools = tools_result.get("result", {}).get("tools", [])
            
            print(f"\n📦 Found {len(tools)} tools:")
            for tool in tools:
                print(f"   • {tool.get('name')}: {tool.get('description', '')[:60]}...")
                
            # Look for converse tool
            converse_tools = [t for t in tools if 'converse' in t.get('name', '').lower()]
            if converse_tools:
                print("\n✅ Converse tool found!")
                for t in converse_tools:
                    print(f"   Name: {t.get('name')}")
                    print(f"   Description: {t.get('description', '')[:100]}...")
            else:
                print("\n❌ Converse tool not found in tools list")
        
        # Terminate
        process.terminate()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Testing CHATTA MCP Server Tools")
    print("=" * 60)
    
    success = test_mcp_tools()
    
    if not success:
        print("\n⚠️  Server may not be exposing tools correctly")
        print("Check that tools are properly decorated with @mcp.tool()")
    
    print("=" * 60)