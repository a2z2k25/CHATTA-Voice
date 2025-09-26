#!/usr/bin/env python3
"""
Comprehensive parity test for Claude Desktop and Claude Code
Tests audio feedback and VAD functionality in both environments
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

class ParityTester:
    def __init__(self):
        self.results = {
            "direct_python": {},
            "cli": {},
            "mcp_server": {},
            "audio_files": {}
        }
        
    def print_header(self, title):
        """Print formatted section header"""
        print("\n" + "=" * 60)
        print(f" {title}")
        print("=" * 60)
        
    def check_audio_files(self):
        """Verify all audio files exist"""
        self.print_header("1. AUDIO FILES CHECK")
        
        audio_dir = Path("voice_mode/audio")
        required_files = [
            "start_chime.wav",
            "end_chime.wav",
            "start_chime_bluetooth.wav",
            "end_chime_bluetooth.wav"
        ]
        
        all_exist = True
        for file in required_files:
            file_path = audio_dir / file
            exists = file_path.exists()
            if exists:
                size = file_path.stat().st_size
                print(f"  ✅ {file:<30} ({size:,} bytes)")
                self.results["audio_files"][file] = True
            else:
                print(f"  ❌ {file:<30} MISSING")
                self.results["audio_files"][file] = False
                all_exist = False
                
        return all_exist
    
    async def test_direct_python(self):
        """Test direct Python execution (simulates Claude Desktop)"""
        self.print_header("2. DIRECT PYTHON TEST (Claude Desktop simulation)")
        
        print("Testing audio feedback directly...")
        
        try:
            from voice_mode.core import play_chime_start, play_chime_end
            
            # Test start chime
            print("  Playing start chime...")
            success = await play_chime_start()
            self.results["direct_python"]["start_chime"] = success
            print(f"  {'✅' if success else '❌'} Start chime: {success}")
            
            await asyncio.sleep(0.5)
            
            # Test end chime
            print("  Playing end chime...")
            success = await play_chime_end()
            self.results["direct_python"]["end_chime"] = success
            print(f"  {'✅' if success else '❌'} End chime: {success}")
            
            # Test VAD availability
            from voice_mode.config import DISABLE_SILENCE_DETECTION
            
            # Check if webrtcvad is available
            try:
                import webrtcvad
                vad_available = True
            except ImportError:
                vad_available = False
                
            self.results["direct_python"]["vad_available"] = vad_available
            self.results["direct_python"]["vad_enabled"] = not DISABLE_SILENCE_DETECTION
            
            print(f"  {'✅' if vad_available else '❌'} VAD available: {vad_available}")
            print(f"  {'✅' if not DISABLE_SILENCE_DETECTION else '❌'} VAD enabled: {not DISABLE_SILENCE_DETECTION}")
            
            return all([
                self.results["direct_python"].get("start_chime", False),
                self.results["direct_python"].get("end_chime", False),
                vad_available
            ])
            
        except Exception as e:
            print(f"  ❌ Direct Python test failed: {e}")
            self.results["direct_python"]["error"] = str(e)
            return False
    
    def test_cli(self):
        """Test CLI execution"""
        self.print_header("3. CLI TEST")
        
        print("Testing through CLI interface...")
        
        env = os.environ.copy()
        env.update({
            "CHATTA_AUDIO_FEEDBACK": "true",
            "VOICEMODE_AUDIO_FEEDBACK": "true",
            "CHATTA_VAD_DEBUG": "false"
        })
        
        cmd = [
            sys.executable, "-m", "voice_mode.cli",
            "converse",
            "-m", "CLI parity test",
            "--wait",
            "--duration", "2",
            "--audio-feedback", "true",
            "--skip-tts",
            "--simulate"
        ]
        
        try:
            print("  Running CLI command...")
            result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            success = result.returncode == 0
            self.results["cli"]["success"] = success
            self.results["cli"]["return_code"] = result.returncode
            
            # Check for VAD in output
            vad_present = "silence detection" in result.stderr.lower() or "vad" in result.stderr.lower()
            self.results["cli"]["vad_present"] = vad_present
            
            print(f"  {'✅' if success else '❌'} CLI execution: {'success' if success else f'failed (code {result.returncode})'}")
            print(f"  {'✅' if vad_present else '⚠️'} VAD mentioned: {vad_present}")
            
            return success
            
        except subprocess.TimeoutExpired:
            print("  ❌ CLI test timed out")
            self.results["cli"]["error"] = "timeout"
            return False
        except Exception as e:
            print(f"  ❌ CLI test failed: {e}")
            self.results["cli"]["error"] = str(e)
            return False
    
    def test_mcp_server(self):
        """Test MCP server execution (Claude Code context)"""
        self.print_header("4. MCP SERVER TEST (Claude Code simulation)")
        
        print("Testing through MCP server subprocess...")
        
        # Prepare MCP request with correct parameters
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "converse",
                "arguments": {
                    "message": "MCP parity test",
                    "wait": True,
                    "duration": 2.0,
                    "audio_feedback": "true",
                    "skip_tts": True,
                    "simulate": True
                }
            },
            "id": 1
        }
        
        cmd = [sys.executable, "-m", "voice_mode.server"]
        
        env = os.environ.copy()
        env.update({
            "CHATTA_AUDIO_FEEDBACK": "true",
            "VOICEMODE_AUDIO_FEEDBACK": "true"
        })
        
        try:
            print("  Starting MCP server...")
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Send request
            print("  Sending MCP request...")
            proc.stdin.write(json.dumps(request) + "\n")
            proc.stdin.flush()
            
            # Wait for response
            start_time = time.time()
            response_received = False
            
            while time.time() - start_time < 5:
                line = proc.stdout.readline()
                if line:
                    try:
                        response = json.loads(line)
                        if "result" in response or "error" in response:
                            response_received = True
                            self.results["mcp_server"]["response"] = response
                            
                            if "error" in response:
                                print(f"  ❌ MCP error: {response['error']}")
                                self.results["mcp_server"]["success"] = False
                            else:
                                print(f"  ✅ MCP response received")
                                self.results["mcp_server"]["success"] = True
                            break
                    except json.JSONDecodeError:
                        continue
            
            # Terminate server
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except:
                proc.kill()
            
            if not response_received:
                print("  ❌ No MCP response received")
                self.results["mcp_server"]["success"] = False
                return False
                
            return self.results["mcp_server"].get("success", False)
            
        except Exception as e:
            print(f"  ❌ MCP server test failed: {e}")
            self.results["mcp_server"]["error"] = str(e)
            return False
    
    def test_audio_playback_methods(self):
        """Test different audio playback methods"""
        self.print_header("5. AUDIO PLAYBACK METHODS TEST")
        
        audio_file = Path("voice_mode/audio/start_chime.wav")
        
        if not audio_file.exists():
            print("  ❌ Test audio file not found")
            return False
        
        # Test afplay (macOS)
        if sys.platform == 'darwin':
            print("  Testing macOS afplay...")
            try:
                result = subprocess.run(
                    ['afplay', str(audio_file)],
                    capture_output=True,
                    timeout=2
                )
                success = result.returncode == 0
                print(f"  {'✅' if success else '❌'} afplay: {'works' if success else 'failed'}")
                self.results["audio_files"]["afplay"] = success
            except Exception as e:
                print(f"  ❌ afplay test failed: {e}")
                self.results["audio_files"]["afplay"] = False
        
        # Test sounddevice availability
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            has_output = any(d['max_output_channels'] > 0 for d in devices)
            print(f"  {'✅' if has_output else '❌'} sounddevice: {'output available' if has_output else 'no output devices'}")
            self.results["audio_files"]["sounddevice"] = has_output
        except Exception as e:
            print(f"  ❌ sounddevice test failed: {e}")
            self.results["audio_files"]["sounddevice"] = False
        
        return True
    
    def verify_vad_configuration(self):
        """Verify VAD configuration"""
        self.print_header("6. VAD CONFIGURATION CHECK")
        
        from voice_mode.config import (
            DISABLE_SILENCE_DETECTION,
            VAD_AGGRESSIVENESS,
            SILENCE_THRESHOLD_MS,
            MIN_RECORDING_DURATION
        )
        
        # Check if webrtcvad is available
        try:
            import webrtcvad
            VAD_AVAILABLE = True
        except ImportError:
            VAD_AVAILABLE = False
        
        print(f"  VAD Available: {VAD_AVAILABLE}")
        print(f"  Silence Detection: {'DISABLED' if DISABLE_SILENCE_DETECTION else 'ENABLED'}")
        print(f"  VAD Aggressiveness: {VAD_AGGRESSIVENESS}")
        print(f"  Silence Threshold: {SILENCE_THRESHOLD_MS}ms")
        print(f"  Min Recording Duration: {MIN_RECORDING_DURATION}s")
        
        self.results["vad_config"] = {
            "available": VAD_AVAILABLE,
            "enabled": not DISABLE_SILENCE_DETECTION,
            "aggressiveness": VAD_AGGRESSIVENESS,
            "threshold_ms": SILENCE_THRESHOLD_MS,
            "min_duration": MIN_RECORDING_DURATION
        }
        
        return VAD_AVAILABLE and not DISABLE_SILENCE_DETECTION
    
    async def run_all_tests(self):
        """Run all parity tests"""
        print("=" * 60)
        print(" CLAUDE DESKTOP/CODE PARITY TEST SUITE")
        print("=" * 60)
        print("\nThis test verifies that audio feedback and VAD work")
        print("equally well in both Claude Desktop and Claude Code.")
        
        # Run tests
        audio_ok = self.check_audio_files()
        direct_ok = await self.test_direct_python()
        cli_ok = self.test_cli()
        mcp_ok = self.test_mcp_server()
        playback_ok = self.test_audio_playback_methods()
        vad_ok = self.verify_vad_configuration()
        
        # Final report
        self.print_header("FINAL REPORT")
        
        print("\nComponent Status:")
        print(f"  {'✅' if audio_ok else '❌'} Audio files present")
        print(f"  {'✅' if direct_ok else '❌'} Direct Python (Desktop-like)")
        print(f"  {'✅' if cli_ok else '❌'} CLI interface")
        print(f"  {'✅' if mcp_ok else '❌'} MCP server (Code-like)")
        print(f"  {'✅' if playback_ok else '❌'} Audio playback methods")
        print(f"  {'✅' if vad_ok else '❌'} VAD configuration")
        
        all_pass = all([audio_ok, direct_ok, cli_ok, mcp_ok, playback_ok, vad_ok])
        
        print("\n" + "=" * 60)
        if all_pass:
            print(" ✅ PARITY ACHIEVED - Works in both environments!")
        else:
            print(" ❌ PARITY ISSUES - Some components need attention")
        print("=" * 60)
        
        # Detailed results
        if not all_pass:
            print("\nIssues to address:")
            if not audio_ok:
                print("  - Run generate_chimes.py to create audio files")
            if not direct_ok:
                print("  - Check Python audio libraries")
            if not cli_ok:
                print("  - Verify CLI installation")
            if not mcp_ok:
                print("  - Check MCP server configuration")
            if not vad_ok:
                print("  - Install webrtcvad for silence detection")
        
        return all_pass

async def main():
    tester = ParityTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())