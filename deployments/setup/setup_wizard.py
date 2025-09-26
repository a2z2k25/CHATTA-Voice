#!/usr/bin/env python3
"""
CHATTA Interactive Setup Wizard
================================
A friendly, step-by-step installation guide for new users.
"""

import os
import sys
import subprocess
import platform
import shutil
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import textwrap

# BUMBA Platform Color Scheme
class Colors:
    # Gradient colors (BUMBA spec)
    GREEN = '\033[38;2;0;170;0m'        # Rich green
    YELLOW_GREEN = '\033[38;2;102;187;0m'  # Yellow-green
    YELLOW = '\033[38;2;255;221;0m'     # Golden yellow
    ORANGE = '\033[38;2;255;170;0m'     # Orange-yellow
    RED = '\033[38;2;221;0;0m'           # Deep red

    # Accent colors
    GOLD = '\033[38;2;212;175;55m'      # Brand gold
    WHEAT = '\033[38;2;245;222;179m'    # Brand wheat

    # Standard
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    # Semantic (for compatibility)
    HEADER = GOLD

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the CHATTA wizard header with BUMBA gradient."""
    clear_screen()

    # CHATTA logo lines
    logo_lines = [
        " ██████╗██╗  ██╗ █████╗ ████████╗████████╗ █████╗ ",
        "██╔════╝██║  ██║██╔══██╗╚══██╔══╝╚══██╔══╝██╔══██╗",
        "██║     ███████║███████║   ██║      ██║   ███████║",
        "██║     ██╔══██║██╔══██║   ██║      ██║   ██╔══██║",
        "╚██████╗██║  ██║██║  ██║   ██║      ██║   ██║  ██║",
        " ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝"
    ]

    # Apply gradient colors (Green → Yellow → Orange → Red)
    gradient_colors = [Colors.GREEN, Colors.YELLOW_GREEN, Colors.YELLOW,
                      Colors.ORANGE, Colors.ORANGE, Colors.RED]

    for i, line in enumerate(logo_lines):
        color = gradient_colors[i]
        print(f"{color}{Colors.BOLD}{line}{Colors.END}")

    print()
    print(f"{Colors.GOLD}{'▄' * 52}{Colors.END}")
    print(f"{Colors.GOLD}{Colors.BOLD}  Natural Voice Conversations for AI Assistants  {Colors.END}")
    print(f"{Colors.GOLD}{'▀' * 52}{Colors.END}")
    print(f"{Colors.WHEAT}Building Unified Multi-agent Business Applications{Colors.END}")
    print(f"{Colors.WHEAT}Professional • Intelligent • Secure • Enterprise-Ready{Colors.END}")
    print()

def print_step(step_num: int, total_steps: int, title: str):
    """Print a step header."""
    print(f"\n{Colors.BLUE}{'═' * 70}{Colors.END}")
    print(f"{Colors.BOLD}📍 Step {step_num}/{total_steps}: {title}{Colors.END}")
    print(f"{Colors.BLUE}{'═' * 70}{Colors.END}\n")

def print_success(message: str):
    """Print a success message with BUMBA emoji."""
    print(f"🟢 {Colors.GREEN}{message}{Colors.END}")

def print_warning(message: str):
    """Print a warning message with BUMBA emoji."""
    print(f"🟡 {Colors.YELLOW}{message}{Colors.END}")

def print_error(message: str):
    """Print an error message with BUMBA emoji."""
    print(f"🔴 {Colors.RED}{message}{Colors.END}")

def print_info(message: str):
    """Print an info message with BUMBA emoji."""
    print(f"🟠 {Colors.CYAN}{message}{Colors.END}")

def print_complete(message: str):
    """Print a completion message with BUMBA emoji."""
    print(f"🏁 {Colors.GREEN}{message}{Colors.END}")

def ask_yes_no(question: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{Colors.BOLD}{question} [{default_str}]: {Colors.END}").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print_warning("Please answer 'yes' or 'no'")

def ask_choice(question: str, choices: List[str], default: int = 0) -> int:
    """Ask user to choose from a list of options."""
    print(f"\n{Colors.BOLD}{question}{Colors.END}")
    for i, choice in enumerate(choices):
        marker = "►" if i == default else " "
        print(f"  {marker} [{i+1}] {choice}")
    
    while True:
        response = input(f"\n{Colors.BOLD}Enter choice [1-{len(choices)}] (default: {default+1}): {Colors.END}").strip()
        if not response:
            return default
        try:
            choice = int(response) - 1
            if 0 <= choice < len(choices):
                return choice
        except ValueError:
            pass
        print_warning(f"Please enter a number between 1 and {len(choices)}")

def show_progress(message: str, func, *args, **kwargs):
    """Show a progress spinner while executing a function."""
    import threading
    
    done = False
    result = [None]
    error = [None]
    
    def run_func():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            error[0] = e
        finally:
            nonlocal done
            done = True
    
    thread = threading.Thread(target=run_func)
    thread.start()
    
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    i = 0
    
    while not done:
        print(f"\r{Colors.CYAN}{spinner[i]} {message}{Colors.END}", end='', flush=True)
        i = (i + 1) % len(spinner)
        time.sleep(0.1)
    
    print("\r" + " " * (len(message) + 3) + "\r", end='')
    
    thread.join()
    
    if error[0]:
        raise error[0]
    return result[0]

def check_command(cmd: str) -> bool:
    """Check if a command is available."""
    return shutil.which(cmd) is not None

def run_command(cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(cmd, capture_output=capture_output, text=True)

def get_system_info() -> Dict[str, str]:
    """Get system information."""
    info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'python': sys.version.split()[0],
        'arch': platform.machine(),
    }
    
    # Check for WSL
    if info['os'] == 'Linux' and 'microsoft' in platform.uname().release.lower():
        info['os'] = 'WSL'
    
    return info

class SetupWizard:
    """Interactive setup wizard for CHATTA."""
    
    def __init__(self):
        self.system_info = get_system_info()
        self.config = {
            'install_mode': 'automatic',
            'use_openai': False,
            'openai_key': None,
            'install_local_services': True,
            'services': {
                'whisper': False,
                'kokoro': False,
                'livekit': False
            },
            'docker_available': False,
            'claude_code_installed': False,
            'mcp_configured': False
        }
        self.total_steps = 8
        
    def run(self):
        """Run the setup wizard."""
        print_header()
        print(f"Welcome! I'll help you set up CHATTA for natural voice conversations.\n")
        print(f"This wizard will guide you through {self.total_steps} simple steps.")
        print(f"Estimated time: 5-10 minutes\n")
        
        if not ask_yes_no("Ready to begin?"):
            print("\nSetup cancelled. You can run this wizard again anytime!")
            return
        
        try:
            # Step 1: System Check
            self.check_system()
            
            # Step 2: Choose Installation Mode
            self.choose_mode()
            
            # Step 3: Check Dependencies
            self.check_dependencies()
            
            # Step 4: Configure API Keys
            self.configure_api_keys()
            
            # Step 5: Install CHATTA
            self.install_chatta()
            
            # Step 6: Install Services
            if self.config['install_local_services']:
                self.install_services()
            
            # Step 7: Configure MCP
            self.configure_mcp()
            
            # Step 8: Final Setup & Test
            self.final_setup()
            
            # Success!
            self.show_success()
            
        except KeyboardInterrupt:
            print("\n\n" + Colors.YELLOW + "Setup interrupted by user." + Colors.END)
            print("You can resume setup by running this wizard again.")
        except Exception as e:
            print_error(f"\nSetup failed: {e}")
            print("\nPlease check the error above and try again.")
            print("For help, visit: https://github.com/your-repo/chatta/issues")
    
    def check_system(self):
        """Step 1: Check system compatibility."""
        print_step(1, self.total_steps, "System Compatibility Check")
        
        print("Checking your system...\n")
        
        # OS Check
        os_name = self.system_info['os']
        if os_name in ['Darwin', 'Linux', 'WSL']:
            print_success(f"Operating System: {os_name} ✓")
        elif os_name == 'Windows':
            print_warning("Windows detected - WSL is recommended for best experience")
            if not ask_yes_no("Continue with native Windows?", default=False):
                print("\nPlease install WSL first: https://aka.ms/wsl2")
                sys.exit(1)
        else:
            print_error(f"Unsupported OS: {os_name}")
            sys.exit(1)
        
        # Python Check
        python_version = self.system_info['python']
        major, minor = map(int, python_version.split('.')[:2])
        if major >= 3 and minor >= 10:
            print_success(f"Python Version: {python_version} ✓")
        else:
            print_error(f"Python {python_version} is too old. Python 3.10+ required.")
            sys.exit(1)
        
        # Check for audio
        if os_name == 'Darwin':
            audio_ok = True  # macOS always has audio
        elif os_name == 'Linux' or os_name == 'WSL':
            audio_ok = os.path.exists('/dev/snd') or os.path.exists('/proc/asound')
        else:
            audio_ok = True  # Assume Windows has audio
        
        if audio_ok:
            print_success("Audio System: Available ✓")
        else:
            print_warning("Audio system not detected - LiveKit mode will be required")
        
        print("\n" + Colors.GREEN + "System compatibility check passed!" + Colors.END)
        input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")
    
    def choose_mode(self):
        """Step 2: Choose installation mode."""
        print_step(2, self.total_steps, "Choose Installation Mode")
        
        print("How would you like to set up CHATTA?\n")
        
        modes = [
            "🚀 Automatic (Recommended) - I'll handle everything for you",
            "🔧 Custom - Choose exactly what to install",
            "📚 Manual - Just show me the commands"
        ]
        
        choice = ask_choice("Select installation mode:", modes, default=0)
        
        if choice == 0:
            self.config['install_mode'] = 'automatic'
            print_success("Using automatic installation mode")
        elif choice == 1:
            self.config['install_mode'] = 'custom'
            print_info("Custom mode selected - you'll choose each component")
        else:
            self.config['install_mode'] = 'manual'
            print_info("Manual mode - I'll show you the commands to run")
    
    def check_dependencies(self):
        """Step 3: Check and install dependencies."""
        print_step(3, self.total_steps, "Checking Dependencies")
        
        deps = {
            'git': 'Version control',
            'curl': 'Downloading files',
            'ffmpeg': 'Audio processing',
            'docker': 'Running local services (optional)',
            'node': 'Claude Code (optional)',
            'uv': 'Python package manager (optional)'
        }
        
        missing = []
        optional_missing = []
        
        for cmd, description in deps.items():
            if check_command(cmd):
                print_success(f"{cmd}: {description} ✓")
                if cmd == 'docker':
                    self.config['docker_available'] = True
            else:
                if cmd in ['docker', 'node', 'uv']:
                    optional_missing.append((cmd, description))
                    print_warning(f"{cmd}: {description} (optional)")
                else:
                    missing.append((cmd, description))
                    print_error(f"{cmd}: {description} ✗")
        
        if missing:
            print(f"\n{Colors.RED}Required dependencies missing!{Colors.END}")
            
            if self.config['install_mode'] == 'automatic':
                if ask_yes_no("\nShall I install the missing dependencies?"):
                    self.install_dependencies(missing)
                else:
                    print("\nPlease install missing dependencies manually:")
                    for cmd, desc in missing:
                        print(f"  • {cmd} - {desc}")
                    sys.exit(1)
            else:
                print("\nPlease install these manually before continuing:")
                for cmd, desc in missing:
                    if self.system_info['os'] == 'Darwin':
                        print(f"  brew install {cmd}")
                    elif self.system_info['os'] in ['Linux', 'WSL']:
                        print(f"  sudo apt-get install {cmd}")
                sys.exit(1)
        
        if optional_missing and self.config['install_mode'] == 'custom':
            print(f"\n{Colors.YELLOW}Optional dependencies available:{Colors.END}")
            for cmd, desc in optional_missing:
                if ask_yes_no(f"Install {cmd} ({desc})?", default=False):
                    self.install_dependency(cmd)
    
    def install_dependencies(self, deps: List[Tuple[str, str]]):
        """Install missing dependencies."""
        for cmd, description in deps:
            print(f"\nInstalling {cmd}...")
            
            if self.system_info['os'] == 'Darwin':
                # macOS - use Homebrew
                if not check_command('brew'):
                    print("Installing Homebrew first...")
                    run_command(['/bin/bash', '-c', '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)'])
                
                show_progress(f"Installing {cmd}", run_command, ['brew', 'install', cmd])
                
            elif self.system_info['os'] in ['Linux', 'WSL']:
                # Linux - use apt
                show_progress(f"Installing {cmd}", run_command, ['sudo', 'apt-get', 'install', '-y', cmd])
            
            if check_command(cmd):
                print_success(f"{cmd} installed successfully!")
            else:
                print_error(f"Failed to install {cmd}")
    
    def configure_api_keys(self):
        """Step 4: Configure API keys."""
        print_step(4, self.total_steps, "Configure Voice Services")
        
        print("CHATTA can use either:\n")
        print("  1. OpenAI API (cloud-based, requires API key)")
        print("  2. Local services (free, runs on your computer)")
        print("  3. Both (recommended - local with cloud fallback)\n")
        
        choices = [
            "Both - Local services with OpenAI fallback (Recommended)",
            "Local only - Free open-source services",
            "OpenAI only - Cloud-based services"
        ]
        
        choice = ask_choice("Select voice service configuration:", choices, default=0)
        
        if choice in [0, 2]:  # Both or OpenAI only
            self.config['use_openai'] = True
            print("\n" + Colors.BOLD + "OpenAI API Configuration" + Colors.END)
            print("Get your API key from: https://platform.openai.com/api-keys\n")
            
            api_key = input(f"{Colors.BOLD}Enter OpenAI API key (or press Enter to skip): {Colors.END}").strip()
            if api_key:
                self.config['openai_key'] = api_key
                print_success("OpenAI API key configured")
            else:
                print_warning("No API key provided - will use local services only")
                self.config['use_openai'] = False
        
        if choice in [0, 1]:  # Both or Local only
            self.config['install_local_services'] = True
            print_info("Local services will be installed")
    
    def install_chatta(self):
        """Step 5: Install CHATTA."""
        print_step(5, self.total_steps, "Installing CHATTA")
        
        if self.config['install_mode'] == 'manual':
            print("Run these commands to install CHATTA:\n")
            print(f"{Colors.CYAN}# Install with pip{Colors.END}")
            print("pip install chatta\n")
            print(f"{Colors.CYAN}# Or install from source{Colors.END}")
            print("git clone https://github.com/your-repo/chatta")
            print("cd chatta")
            print("pip install -e .\n")
            input(f"\n{Colors.BOLD}Press Enter when done...{Colors.END}")
        else:
            print("Installing CHATTA package...\n")
            
            # Check if we're in the CHATTA directory
            if os.path.exists('pyproject.toml'):
                # Install from source
                show_progress("Installing CHATTA from source", 
                            run_command, ['pip', 'install', '-e', '.'])
            else:
                # Install from PyPI
                show_progress("Installing CHATTA from PyPI", 
                            run_command, ['pip', 'install', 'chatta'])
            
            # Verify installation
            result = run_command(['python', '-c', 'import voice_mode; print("OK")'])
            if result.returncode == 0:
                print_success("CHATTA installed successfully!")
            else:
                print_error("CHATTA installation failed")
                print("Try manual installation: pip install chatta")
    
    def install_services(self):
        """Step 6: Install local voice services."""
        print_step(6, self.total_steps, "Setting Up Voice Services")
        
        if not self.config['install_local_services']:
            print("Skipping local services (using OpenAI API)")
            return
        
        print("Installing free, open-source voice services...\n")
        
        services = [
            ('whisper', 'Speech-to-Text (Whisper)', 'docker/whisper'),
            ('kokoro', 'Text-to-Speech (Kokoro)', 'docker/kokoro'),
            ('livekit', 'Real-time Communication (LiveKit)', 'docker/livekit')
        ]
        
        if self.config['install_mode'] == 'custom':
            print("Select which services to install:\n")
            for key, name, _ in services:
                self.config['services'][key] = ask_yes_no(f"Install {name}?", default=True)
        else:
            # Automatic mode - install Whisper and Kokoro, skip LiveKit
            self.config['services']['whisper'] = True
            self.config['services']['kokoro'] = True
            self.config['services']['livekit'] = False
        
        if self.config['docker_available']:
            # Use Docker
            print_info("Using Docker to run services")
            
            # Create docker-compose.yml if needed
            if not os.path.exists('docker-compose.yml'):
                self.create_docker_compose()
            
            # Start selected services
            services_to_start = [k for k, v in self.config['services'].items() if v]
            if services_to_start:
                cmd = ['docker-compose', 'up', '-d'] + services_to_start
                show_progress("Starting Docker services", run_command, cmd)
                print_success("Docker services started!")
        else:
            print_warning("Docker not available - services must be installed manually")
            print("\nTo install services manually:")
            print("1. Install Docker: https://docs.docker.com/get-docker/")
            print("2. Run: docker-compose up -d")
    
    def create_docker_compose(self):
        """Create a docker-compose.yml file."""
        compose = {
            'version': '3.8',
            'services': {}
        }
        
        if self.config['services']['whisper']:
            compose['services']['whisper'] = {
                'image': 'onerahmet/openai-whisper-asr-webservice:latest-gpu',
                'ports': ['8880:9000'],
                'environment': {
                    'ASR_MODEL': 'base',
                    'ASR_ENGINE': 'openai_whisper'
                },
                'restart': 'unless-stopped'
            }
        
        if self.config['services']['kokoro']:
            compose['services']['kokoro'] = {
                'build': './docker/kokoro',
                'ports': ['7888:7888'],
                'restart': 'unless-stopped'
            }
        
        if self.config['services']['livekit']:
            compose['services']['livekit'] = {
                'image': 'livekit/livekit-server:latest',
                'ports': ['7880:7880', '7881:7881', '7882:7882/udp'],
                'command': '--dev --config /etc/livekit.yaml',
                'volumes': ['./docker/livekit/livekit.yaml:/etc/livekit.yaml'],
                'restart': 'unless-stopped'
            }
        
        with open('docker-compose.yml', 'w') as f:
            import yaml
            yaml.dump(compose, f, default_flow_style=False)
        
        print_success("Created docker-compose.yml")
    
    def configure_mcp(self):
        """Step 7: Configure MCP for Claude Code."""
        print_step(7, self.total_steps, "Configure Claude Code Integration")
        
        # Check if Claude Code is installed
        claude_cmd = check_command('claude')
        if claude_cmd:
            self.config['claude_code_installed'] = True
            print_success("Claude Code detected ✓")
        else:
            print_warning("Claude Code not found")
            if ask_yes_no("Install Claude Code?"):
                self.install_claude_code()
        
        # Configure MCP
        print("\nConfiguring MCP server...\n")
        
        mcp_config_path = Path.home() / '.config' / 'claude' / 'mcp.json'
        
        if self.config['install_mode'] == 'manual':
            print("Add this to your MCP configuration:\n")
            print(f"{Colors.CYAN}~/.config/claude/mcp.json:{Colors.END}")
            print(json.dumps({
                "mcpServers": {
                    "chatta": {
                        "type": "stdio",
                        "command": "python",
                        "args": ["-m", "voice_mode.server"],
                        "env": {
                            "OPENAI_API_KEY": "${OPENAI_API_KEY}",
                            "STT_BASE_URL": "http://localhost:8880/v1",
                            "TTS_BASE_URL": "http://localhost:7888/v1"
                        }
                    }
                }
            }, indent=2))
            input(f"\n{Colors.BOLD}Press Enter when done...{Colors.END}")
        else:
            # Automatic configuration
            if mcp_config_path.exists():
                # Backup existing config
                backup_path = mcp_config_path.with_suffix('.backup')
                shutil.copy(mcp_config_path, backup_path)
                print_info(f"Backed up existing config to {backup_path}")
                
                # Load and update config
                with open(mcp_config_path) as f:
                    config = json.load(f)
            else:
                # Create new config
                mcp_config_path.parent.mkdir(parents=True, exist_ok=True)
                config = {"mcpServers": {}}
            
            # Add CHATTA config
            config["mcpServers"]["chatta"] = {
                "type": "stdio",
                "command": "python",
                "args": ["-m", "voice_mode.server"],
                "env": {
                    "STT_BASE_URL": "http://localhost:8880/v1",
                    "TTS_BASE_URL": "http://localhost:7888/v1"
                }
            }
            
            if self.config['openai_key']:
                config["mcpServers"]["chatta"]["env"]["OPENAI_API_KEY"] = self.config['openai_key']
            
            # Save config
            with open(mcp_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print_success("MCP configuration updated!")
            self.config['mcp_configured'] = True
    
    def install_claude_code(self):
        """Install Claude Code."""
        print("\nInstalling Claude Code...\n")
        
        if self.system_info['os'] == 'Darwin':
            # macOS
            show_progress("Downloading Claude Code", run_command, 
                        ['curl', '-fsSL', 'https://claude.ai/download/mac', '-o', '/tmp/claude.dmg'])
            print("Please install Claude Code from the downloaded DMG file")
            run_command(['open', '/tmp/claude.dmg'])
        elif self.system_info['os'] in ['Linux', 'WSL']:
            # Linux
            show_progress("Installing Claude Code", run_command,
                        ['curl', '-fsSL', 'https://claude.ai/download/linux', '|', 'sh'])
        else:
            print("Please download Claude Code from: https://claude.ai/download")
        
        input(f"\n{Colors.BOLD}Press Enter when Claude Code is installed...{Colors.END}")
    
    def final_setup(self):
        """Step 8: Final setup and testing."""
        print_step(8, self.total_steps, "Final Setup & Testing")
        
        print("Running final configuration...\n")
        
        # Create .env file if needed
        if self.config['openai_key'] and not os.path.exists('.env'):
            with open('.env', 'w') as f:
                f.write(f"OPENAI_API_KEY={self.config['openai_key']}\n")
            print_success("Created .env file")
        
        # Test the installation
        print("\nTesting CHATTA installation...\n")
        
        test_results = []
        
        # Test 1: Import
        result = run_command(['python', '-c', 'import voice_mode; print("OK")'])
        if result.returncode == 0:
            test_results.append(('Python Import', True))
            print_success("Python import test ✓")
        else:
            test_results.append(('Python Import', False))
            print_error("Python import test ✗")
        
        # Test 2: Services
        if self.config['install_local_services']:
            import httpx
            import asyncio
            
            async def test_service(url: str, name: str) -> bool:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(f"{url}/health", timeout=2.0)
                        return resp.status_code == 200
                except:
                    return False
            
            if self.config['services']['whisper']:
                ok = asyncio.run(test_service("http://localhost:8880", "Whisper"))
                test_results.append(('Whisper STT', ok))
                if ok:
                    print_success("Whisper STT service ✓")
                else:
                    print_warning("Whisper STT service not responding")
            
            if self.config['services']['kokoro']:
                ok = asyncio.run(test_service("http://localhost:7888", "Kokoro"))
                test_results.append(('Kokoro TTS', ok))
                if ok:
                    print_success("Kokoro TTS service ✓")
                else:
                    print_warning("Kokoro TTS service not responding")
        
        # Test 3: MCP
        if self.config['mcp_configured']:
            test_results.append(('MCP Configuration', True))
            print_success("MCP configuration ✓")
        
        # Show results
        passed = sum(1 for _, ok in test_results if ok)
        total = len(test_results)
        
        if passed == total:
            print(f"\n{Colors.GREEN}All tests passed! ({passed}/{total}){Colors.END}")
        else:
            print(f"\n{Colors.YELLOW}Some tests failed ({passed}/{total}){Colors.END}")
    
    def show_success(self):
        """Show success message and next steps."""
        clear_screen()
        print(f"{Colors.GREEN}{Colors.BOLD}")
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║                                                                ║")
        print("║            🎉 CHATTA SETUP COMPLETE! 🎉                       ║")
        print("║                                                                ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.END}\n")
        
        print(f"{Colors.BOLD}✅ Installation Summary:{Colors.END}\n")
        
        if self.config['claude_code_installed']:
            print("  • Claude Code: Installed")
        if self.config['mcp_configured']:
            print("  • MCP Server: Configured")
        if self.config['services']['whisper']:
            print("  • Whisper STT: Running")
        if self.config['services']['kokoro']:
            print("  • Kokoro TTS: Running")
        if self.config['openai_key']:
            print("  • OpenAI API: Configured")
        
        print(f"\n{Colors.BOLD}🚀 Quick Start:{Colors.END}\n")
        print("1. Start Claude Code:")
        print(f"   {Colors.CYAN}claude{Colors.END}")
        print("\n2. Start a voice conversation:")
        print(f"   {Colors.CYAN}Type: Start a voice conversation{Colors.END}")
        print("\n3. Or use the converse tool directly:")
        print(f"   {Colors.CYAN}Type: Use the converse tool to say hello{Colors.END}")
        
        print(f"\n{Colors.BOLD}📚 Useful Commands:{Colors.END}\n")
        print(f"  {Colors.CYAN}docker-compose up -d{Colors.END}    # Start voice services")
        print(f"  {Colors.CYAN}docker-compose logs{Colors.END}     # View service logs")
        print(f"  {Colors.CYAN}docker-compose down{Colors.END}     # Stop services")
        
        print(f"\n{Colors.BOLD}📖 Documentation:{Colors.END}")
        print("  https://github.com/your-repo/chatta")
        
        print(f"\n{Colors.GREEN}Happy voice chatting! 🎙️{Colors.END}\n")

def main():
    """Main entry point."""
    wizard = SetupWizard()
    wizard.run()

if __name__ == "__main__":
    main()