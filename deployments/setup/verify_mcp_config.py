#!/usr/bin/env python3
"""
Verify CHATTA MCP Configuration
Quick check that everything is set up correctly
"""
import json
import os
import requests

def check_docker_services():
    """Check if Docker services are running"""
    services = {
        "Whisper STT": "http://localhost:8880/health",
        "Kokoro TTS": "http://localhost:7888/health"
    }
    
    print("🐳 Checking Docker services:")
    all_running = True
    for name, url in services.items():
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"   ✅ {name} is running")
            else:
                print(f"   ❌ {name} returned status {r.status_code}")
                all_running = False
        except:
            print(f"   ❌ {name} is not responding")
            all_running = False
    
    return all_running

def check_mcp_config():
    """Check if CHATTA is in MCP config"""
    config_path = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
    
    print("\n📋 Checking MCP configuration:")
    
    if not os.path.exists(config_path):
        print("   ❌ Config file not found")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    if "chatta" in config.get("mcpServers", {}):
        chatta_config = config["mcpServers"]["chatta"]
        print("   ✅ CHATTA is configured in MCP")
        print(f"      Command: {chatta_config.get('command')}")
        print(f"      Working dir: {chatta_config.get('cwd', 'not set')}")
        
        # Check environment variables
        env = chatta_config.get('env', {})
        if env.get('STT_BASE_URL') and env.get('TTS_BASE_URL'):
            print("      ✅ Docker service URLs configured")
        else:
            print("      ⚠️  Service URLs may not be configured")
        
        return True
    else:
        print("   ❌ CHATTA not found in MCP config")
        return False

def check_chatta_installation():
    """Check if CHATTA is properly installed"""
    print("\n🔧 Checking CHATTA installation:")
    
    try:
        import voice_mode
        print(f"   ✅ CHATTA (voice_mode) is installed")
        
        # Check for key modules
        from voice_mode.tools import converse
        from voice_mode import server
        print("   ✅ Core modules are available")
        
        return True
    except ImportError as e:
        print(f"   ❌ CHATTA not properly installed: {e}")
        return False

def main():
    print("=" * 60)
    print("🎙️  CHATTA MCP Integration Verification")
    print("=" * 60)
    
    # Run checks
    docker_ok = check_docker_services()
    mcp_ok = check_mcp_config()
    chatta_ok = check_chatta_installation()
    
    print("\n" + "=" * 60)
    
    if docker_ok and mcp_ok and chatta_ok:
        print("✅ Everything is configured correctly!")
        print("\n💡 Next steps:")
        print("1. Restart Claude Desktop or Claude Code")
        print("2. Look for 'chatta' in the MCP servers list")
        print("3. Try voice commands like:")
        print("   - 'Use the converse tool to say hello'")
        print("   - 'Start a voice conversation'")
    else:
        print("⚠️  Some components need attention:")
        
        if not docker_ok:
            print("\n🐳 Start Docker services:")
            print("   cd .")
            print("   docker-compose up -d")
        
        if not mcp_ok:
            print("\n📋 CHATTA needs to be added to MCP config")
        
        if not chatta_ok:
            print("\n🔧 Install CHATTA:")
            print("   cd .")
            print("   pip install -e .")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()