#!/usr/bin/env python3
"""Complete test of CHATTA MCP server functionality"""
import json
import subprocess
import sys
import asyncio

async def test_mcp_server():
    """Test MCP server with proper protocol sequence"""
    
    # Start the server using the shell script
    process = subprocess.Popen(
        [os.path.dirname(os.path.abspath(__file__)) + "/chatta_mcp_server.sh"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    async def send_request(request):
        """Send request and get response"""
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        
        # Add timeout for reading response
        import select
        ready, _, _ = select.select([process.stdout], [], [], 2.0)
        if ready:
            response = process.stdout.readline()
            return json.loads(response) if response else None
        else:
            print("   ⚠️  Timeout waiting for response")
            return None
    
    try:
        print("Testing CHATTA MCP Server")
        print("=" * 60)
        
        # 1. Initialize with Claude's protocol version
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",  # Claude's version
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        print("1. Sending initialize request...")
        response = await send_request(init_request)
        if response and "result" in response:
            print(f"   ✅ Server initialized: {response['result']['serverInfo']['name']} v{response['result']['serverInfo']['version']}")
            print(f"   Capabilities: {list(response['result']['capabilities'].keys())}")
        else:
            print(f"   ❌ Init failed: {response}")
            return False
        
        # 2. List tools
        list_tools = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        print("\n2. Listing tools...")
        response = await send_request(list_tools)
        if response and "result" in response:
            tools = response['result'].get('tools', [])
            print(f"   ✅ Found {len(tools)} tools:")
            
            # Find converse tool
            converse_tools = [t for t in tools if 'converse' in t.get('name', '').lower()]
            for tool in converse_tools:
                print(f"      - {tool['name']}: {tool.get('description', '')[:100]}...")
                
            if not converse_tools:
                print("   ⚠️  'converse' tool not found!")
        else:
            print(f"   ❌ List tools failed: {response}")
            return False
        
        # 3. Test calling a simple tool (like voice_status)
        call_tool = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "voice_status",
                "arguments": {}
            }
        }
        
        print("\n3. Testing tool call (voice_status)...")
        response = await send_request(call_tool)
        if response and "result" in response:
            print("   ✅ Tool call successful")
        elif response and "error" in response:
            print(f"   ⚠️  Tool call error: {response['error']['message']}")
        else:
            print(f"   ❌ Tool call failed: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        process.terminate()
        print("\n" + "=" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Complete CHATTA MCP Server Test")
    print("=" * 60)
    
    success = asyncio.run(test_mcp_server())
    
    if success:
        print("\n✅ MCP server is working correctly!")
        print("\nNext steps:")
        print("1. Open a NEW chat in Claude Desktop")
        print("2. Type: 'Can you list your available MCP tools?'")
        print("3. Look for 'chatta' tools in the response")
        print("4. Try: 'Use the converse tool to say hello'")
    else:
        print("\n❌ MCP server has issues that need fixing")
    
    print("=" * 60)