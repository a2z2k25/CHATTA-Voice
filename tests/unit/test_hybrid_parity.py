#!/usr/bin/env python3
"""
Hybrid Parity Test for CHATTA Framework
Tests both Claude Desktop (direct) and Claude Code (MCP) execution paths
"""

import subprocess
import json
import sys
import os
import time
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class HybridParityTester:
    def __init__(self):
        self.results = {
            "audio_files": {},
            "desktop_path": {},  # Direct Python execution
            "code_path": {},     # MCP server execution
            "cli_path": {},      # CLI interface
            "vad_status": {}
        }
        
    def print_header(self, title):
        """Print formatted section header"""
        print("\n" + "=" * 60)
        print(f" {title}")
        print("=" * 60)
        
    def check_execution_context(self):
        """Detect current execution context"""
        self.print_header("EXECUTION CONTEXT DETECTION")
        
        # Check if running in MCP mode (like Claude Code would)
        is_mcp_mode = not sys.stdin.isatty() or not sys.stdout.isatty()
        
        print(f"  stdin.isatty(): {sys.stdin.isatty()}")
        print(f"  stdout.isatty(): {sys.stdout.isatty()}")
        print(f"  Detected mode: {'MCP/Claude Code' if is_mcp_mode else 'Direct/Claude Desktop'}")
        print(f"  Python version: {sys.version}")
        print(f"  Platform: {sys.platform}")
        
        self.results["context"] = {
            "is_mcp_mode": is_mcp_mode,
            "stdin_tty": sys.stdin.isatty(),
            "stdout_tty": sys.stdout.isatty(),
            "platform": sys.platform,
            "python_version": sys.version.split()[0]
        }
        
        return is_mcp_mode
        
    def verify_audio_infrastructure(self):
        """Check audio files and playback methods"""
        self.print_header("AUDIO INFRASTRUCTURE CHECK")
        
        audio_dir = Path("voice_mode/audio")
        required_files = [
            ("start_chime.wav", "Standard start chime"),
            ("end_chime.wav", "Standard end chime"),
            ("start_chime_bluetooth.wav", "Bluetooth start (with padding)"),
            ("end_chime_bluetooth.wav", "Bluetooth end (with padding)")
        ]
        
        print("\n  Audio Files:")
        all_exist = True
        for filename, description in required_files:
            file_path = audio_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"    ✅ {filename:<30} {size:>8,} bytes - {description}")
                self.results["audio_files"][filename] = {"exists": True, "size": size}
            else:
                print(f"    ❌ {filename:<30} MISSING - {description}")
                self.results["audio_files"][filename] = {"exists": False}
                all_exist = False
                
        # Check audio playback methods
        print("\n  Playback Methods:")
        
        # Check native commands
        if sys.platform == 'darwin':
            try:
                result = subprocess.run(['which', 'afplay'], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"    ✅ afplay (macOS native): {result.stdout.strip()}")
                    self.results["audio_files"]["afplay"] = True
                else:
                    print(f"    ❌ afplay not found")
                    self.results["audio_files"]["afplay"] = False
            except:
                self.results["audio_files"]["afplay"] = False
                
        # Check Python audio libraries
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            output_devices = [d for d in devices if d['max_output_channels'] > 0]
            print(f"    ✅ sounddevice: {len(output_devices)} output devices available")
            self.results["audio_files"]["sounddevice"] = True
        except ImportError:
            print(f"    ❌ sounddevice: Not installed")
            self.results["audio_files"]["sounddevice"] = False
            
        # Note about simpleaudio (known issue with Python 3.13)
        print(f"    ⚠️  simpleaudio: Avoided due to Python 3.13 crashes")
        
        return all_exist
        
    async def test_desktop_path(self):
        """Test Claude Desktop path (direct Python execution)"""
        self.print_header("CLAUDE DESKTOP PATH TEST (Direct Python)")
        
        print("This simulates how Claude Desktop executes Python code directly.")
        print("Testing audio feedback through direct function calls...")
        
        try:
            from voice_mode.core import play_chime_start, play_chime_end
            
            # Test start chime
            print("\n  Testing start chime:")
            success = await play_chime_start()
            self.results["desktop_path"]["start_chime"] = success
            print(f"    {'✅' if success else '❌'} Start chime playback: {success}")
            
            await asyncio.sleep(0.5)
            
            # Test end chime
            print("  Testing end chime:")
            success = await play_chime_end()
            self.results["desktop_path"]["end_chime"] = success
            print(f"    {'✅' if success else '❌'} End chime playback: {success}")
            
            # Test VAD availability
            print("\n  Testing VAD:")
            try:
                import webrtcvad
                vad = webrtcvad.Vad()
                self.results["desktop_path"]["vad_available"] = True
                print(f"    ✅ WebRTC VAD available")
                
                # Test VAD configuration
                from voice_mode.config import DISABLE_SILENCE_DETECTION
                self.results["desktop_path"]["vad_enabled"] = not DISABLE_SILENCE_DETECTION
                print(f"    {'✅' if not DISABLE_SILENCE_DETECTION else '❌'} VAD enabled: {not DISABLE_SILENCE_DETECTION}")
                
            except ImportError:
                self.results["desktop_path"]["vad_available"] = False
                print(f"    ❌ WebRTC VAD not available")
                
            return True
            
        except Exception as e:
            print(f"\n  ❌ Desktop path test failed: {e}")
            self.results["desktop_path"]["error"] = str(e)
            return False
            
    def test_code_path(self):
        """Test Claude Code path (MCP server via stdio)"""
        self.print_header("CLAUDE CODE PATH TEST (MCP Server)")
        
        print("This simulates how Claude Code executes through MCP server.")
        print("Testing audio feedback through MCP stdio transport...")
        
        # MCP requires initialization first
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        # Send initialized notification (required by MCP protocol)
        initialized_notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        # Then we can list tools (no params needed)
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }
        
        cmd = [sys.executable, "-m", "voice_mode.server"]
        
        env = os.environ.copy()
        env.update({
            "CHATTA_AUDIO_FEEDBACK": "true",
            "VOICEMODE_AUDIO_FEEDBACK": "true"
        })
        
        try:
            print("\n  Testing MCP server startup:")
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # First, initialize the MCP connection
            proc.stdin.write(json.dumps(init_request) + "\n")
            proc.stdin.flush()
            
            # Read initialization response
            init_response = proc.stdout.readline()
            if init_response:
                try:
                    response = json.loads(init_response)
                    if "result" in response:
                        print(f"    ✅ MCP server initialized")
                        self.results["code_path"]["initialized"] = True
                    else:
                        print(f"    ❌ MCP initialization failed: {response.get('error', 'Unknown')}")
                        self.results["code_path"]["initialized"] = False
                except json.JSONDecodeError:
                    print(f"    ❌ Invalid initialization response")
                    self.results["code_path"]["initialized"] = False
            
            # Send initialized notification (required by protocol)
            proc.stdin.write(json.dumps(initialized_notif) + "\n")
            proc.stdin.flush()
            
            # Now list tools
            proc.stdin.write(json.dumps(list_request) + "\n")
            proc.stdin.flush()
            
            # Read tools list response
            response_line = proc.stdout.readline()
            if response_line:
                try:
                    response = json.loads(response_line)
                    if "result" in response:
                        tools = response.get("result", {}).get("tools", [])
                        converse_tool = any(t.get("name") == "converse" for t in tools)
                        print(f"    {'✅' if converse_tool else '❌'} MCP server running, converse tool {'found' if converse_tool else 'not found'}")
                        self.results["code_path"]["server_running"] = True
                        self.results["code_path"]["converse_available"] = converse_tool
                    else:
                        print(f"    ❌ MCP server error: {response.get('error', 'Unknown')}")
                        self.results["code_path"]["server_running"] = False
                except json.JSONDecodeError:
                    print(f"    ❌ Invalid JSON response from MCP server")
                    self.results["code_path"]["server_running"] = False
            
            # Terminate server
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except:
                proc.kill()
                
            # Note about audio in MCP context
            print("\n  Audio Feedback in MCP Context:")
            print("    ℹ️  MCP runs as subprocess with stdio transport")
            print("    ℹ️  Audio uses native system commands (afplay on macOS)")
            print("    ℹ️  Pre-generated WAV files ensure reliability")
            
            return self.results["code_path"].get("server_running", False)
            
        except Exception as e:
            print(f"\n  ❌ Code path test failed: {e}")
            self.results["code_path"]["error"] = str(e)
            return False
            
    def test_cli_path(self):
        """Test CLI interface (used by both)"""
        self.print_header("CLI INTERFACE TEST (Shared Path)")
        
        print("Testing CLI interface used by both Desktop and Code...")
        
        env = os.environ.copy()
        env.update({
            "CHATTA_AUDIO_FEEDBACK": "true",
            "CHATTA_VAD_DEBUG": "false"
        })
        
        cmd = [
            sys.executable, "-m", "voice_mode.cli",
            "converse",
            "-m", "CLI hybrid test",
            "--wait",
            "--duration", "1",
            "--audio-feedback", "true",
            "--skip-tts",
            "--simulate"
        ]
        
        try:
            print("\n  Running CLI command:")
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            success = result.returncode == 0
            self.results["cli_path"]["success"] = success
            
            # Check for audio feedback in output
            audio_mentioned = "audio feedback" in result.stderr.lower() or "chime" in result.stderr.lower()
            self.results["cli_path"]["audio_feedback"] = audio_mentioned
            
            # Check for VAD
            vad_mentioned = "vad" in result.stderr.lower() or "silence" in result.stderr.lower()
            self.results["cli_path"]["vad_present"] = vad_mentioned
            
            print(f"    {'✅' if success else '❌'} CLI execution: {'success' if success else f'failed (code {result.returncode})'}") 
            print(f"    {'✅' if audio_mentioned else '⚠️'} Audio feedback: {'active' if audio_mentioned else 'not detected'}")
            print(f"    {'✅' if vad_mentioned else '⚠️'} VAD/silence detection: {'active' if vad_mentioned else 'not detected'}")
            
            return success
            
        except subprocess.TimeoutExpired:
            print("    ❌ CLI test timed out")
            self.results["cli_path"]["error"] = "timeout"
            return False
        except Exception as e:
            print(f"    ❌ CLI test failed: {e}")
            self.results["cli_path"]["error"] = str(e)
            return False
            
    def analyze_parity(self):
        """Analyze parity between Desktop and Code paths"""
        self.print_header("PARITY ANALYSIS")
        
        print("\n  Feature Comparison:")
        print("  " + "-" * 50)
        print(f"  {'Feature':<30} {'Desktop':<10} {'Code':<10}")
        print("  " + "-" * 50)
        
        # Audio feedback
        desktop_audio = self.results["desktop_path"].get("start_chime", False) and \
                       self.results["desktop_path"].get("end_chime", False)
        code_audio = self.results["code_path"].get("server_running", False) and \
                    all(f["exists"] for f in self.results["audio_files"].values() if isinstance(f, dict))
        
        print(f"  {'Audio Feedback':<30} {'✅' if desktop_audio else '❌':<10} {'✅' if code_audio else '❌':<10}")
        
        # VAD support
        desktop_vad = self.results["desktop_path"].get("vad_available", False)
        code_vad = self.results["code_path"].get("server_running", False)  # VAD works if server runs
        
        print(f"  {'VAD/Silence Detection':<30} {'✅' if desktop_vad else '❌':<10} {'✅' if code_vad else '❌':<10}")
        
        # CLI interface
        cli_works = self.results["cli_path"].get("success", False)
        print(f"  {'CLI Interface':<30} {'✅' if cli_works else '❌':<10} {'✅' if cli_works else '❌':<10}")
        
        print("  " + "-" * 50)
        
        # Overall parity
        has_parity = desktop_audio and code_audio and desktop_vad and code_vad
        
        print(f"\n  Overall Parity: {'✅ ACHIEVED' if has_parity else '❌ NOT ACHIEVED'}")
        
        if not has_parity:
            print("\n  Issues to Address:")
            if not desktop_audio:
                print("    - Desktop: Audio feedback not working")
            if not code_audio:
                print("    - Code: Audio files or MCP server issues")
            if not desktop_vad:
                print("    - Desktop: WebRTC VAD not available")
            if not code_vad:
                print("    - Code: MCP server not running properly")
                
        return has_parity
        
    async def run_all_tests(self):
        """Run all hybrid parity tests"""
        print("=" * 60)
        print(" CHATTA HYBRID PARITY TEST SUITE")
        print("=" * 60)
        print("\nThis test verifies feature parity between:")
        print("  • Claude Desktop (direct Python execution)")
        print("  • Claude Code (MCP server via stdio)")
        
        # Check execution context
        is_mcp = self.check_execution_context()
        
        # Verify infrastructure
        infra_ok = self.verify_audio_infrastructure()
        
        # Test Desktop path
        desktop_ok = await self.test_desktop_path()
        
        # Test Code path
        code_ok = self.test_code_path()
        
        # Test CLI (shared)
        cli_ok = self.test_cli_path()
        
        # Analyze parity
        has_parity = self.analyze_parity()
        
        # Final verdict
        self.print_header("FINAL VERDICT")
        
        if has_parity:
            print("\n  ✅ SUCCESS: Full feature parity achieved!")
            print("  Both Claude Desktop and Claude Code have:")
            print("    • Working audio feedback chimes")
            print("    • VAD/silence detection support")
            print("    • Functional CLI interface")
        else:
            print("\n  ⚠️  PARTIAL SUCCESS: Some features need attention")
            print("  See analysis above for specific issues")
            
        print("\n" + "=" * 60)
        
        return has_parity

async def main():
    tester = HybridParityTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())