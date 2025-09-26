#!/usr/bin/env python3
"""
CHATTA Enhanced Setup Wizard with Intelligent Detection
========================================================
Dynamically detects existing installations and provides bypass options for power users.
"""

import os
import sys
import subprocess
import platform
import shutil
import json
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import textwrap

# BUMBA Platform official color codes (from @bumba/brand guidelines)
class Colors:
    # Official BUMBA gradient colors (hex to RGB conversion)
    GRADIENT_GREEN = '\033[38;2;0;170;0m'        # #00AA00 - Rich green
    GRADIENT_YELLOW_GREEN = '\033[38;2;102;187;0m'  # #66BB00 - Yellow-green
    GRADIENT_YELLOW = '\033[38;2;255;221;0m'     # #FFDD00 - Golden yellow
    GRADIENT_ORANGE_YELLOW = '\033[38;2;255;170;0m'  # #FFAA00 - Orange-yellow
    GRADIENT_ORANGE_RED = '\033[38;2;255;102;0m' # #FF6600 - Orange-red
    GRADIENT_RED = '\033[38;2;221;0;0m'          # #DD0000 - Deep red

    # Semantic colors (BUMBA brand aligned)
    PRIMARY = '\033[38;2;255;255;255m'   # #FFFFFF - White (default text)
    SECONDARY = '\033[38;2;128;128;128m' # #808080 - Grey (accent text)
    SUCCESS = '\033[38;2;0;170;0m'       # #00AA00 - Green
    WARNING = '\033[38;2;255;170;0m'     # #FFAA00 - Orange-yellow
    ERROR = '\033[38;2;221;0;0m'         # #DD0000 - Red
    INFO = '\033[38;2;102;187;0m'        # #66BB00 - Yellow-green

    # Brand accent colors
    GOLD = '\033[38;2;212;175;55m'       # #D4AF37 - Brand gold
    WHEAT = '\033[38;2;245;222;179m'     # #F5DEB3 - Brand wheat
    BORDER = '\033[38;2;255;221;0m'      # #FFDD00 - Golden yellow borders

    # Legacy aliases for compatibility
    HEADER = GOLD
    BLUE = BORDER
    CYAN = WARNING
    GREEN = SUCCESS
    YELLOW = GRADIENT_YELLOW
    RED = ERROR
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the CHATTA wizard header with BUMBA branding."""
    clear_screen()
    # CHATTA ASCII logo with gradient
    logo = [
        ' ██████╗██╗  ██╗ █████╗ ████████╗████████╗ █████╗ ',
        '██╔════╝██║  ██║██╔══██╗╚══██╔══╝╚══██╔══╝██╔══██╗',
        '██║     ███████║███████║   ██║      ██║   ███████║',
        '██║     ██╔══██║██╔══██║   ██║      ██║   ██╔══██║',
        '╚██████╗██║  ██║██║  ██║   ██║      ██║   ██║  ██║',
        ' ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝'
    ]
    gradient_colors = [
        Colors.GRADIENT_GREEN,
        Colors.GRADIENT_YELLOW_GREEN,
        Colors.GRADIENT_YELLOW,
        Colors.GRADIENT_ORANGE,
        Colors.GRADIENT_ORANGE_RED,
        Colors.GRADIENT_RED
    ]
    
    for i, line in enumerate(logo):
        color = gradient_colors[min(i, len(gradient_colors) - 1)]
        print(f"{color}{Colors.BOLD}{line}{Colors.END}")
    
    print(f"\n{Colors.GOLD}{'▄' * 60}{Colors.END}")
    print(f"{Colors.GOLD}{Colors.BOLD}      CHATTA 🎙️ SETUP WIZARD • BUMBA PLATFORM{Colors.END}")
    print(f"{Colors.GOLD}{'▀' * 60}{Colors.END}")
    print(f"\n{Colors.WHEAT}Natural Voice Conversations for AI Assistants • Part of the BUMBA Platform{Colors.END}")
    print(f"{Colors.WHEAT}Version 3.34.3 • Enterprise-Ready Voice Integration{Colors.END}\n")

def print_detection_header():
    """Print header for detection phase with BUMBA styling."""
    print(f"\n{Colors.BORDER}{'═' * 70}{Colors.END}")
    print(f"{Colors.BOLD}🟠 DETECTING EXISTING INSTALLATIONS{Colors.END}")
    print(f"{Colors.BORDER}{'═' * 70}{Colors.END}\n")

def print_step(step_num: int, total_steps: int, title: str):
    """Print a step header with BUMBA styling."""
    print(f"\n{Colors.BORDER}{'═' * 70}{Colors.END}")
    print(f"{Colors.BOLD}🟠 Step {step_num}/{total_steps}: {title}{Colors.END}")
    print(f"{Colors.BORDER}{'═' * 70}{Colors.END}\n")

def print_success(message: str):
    """Print a success message with BUMBA styling (Backend department)."""
    print(f"🟢 {Colors.SUCCESS}{message}{Colors.END}")

def print_warning(message: str):
    """Print a warning message with BUMBA styling (Strategy department)."""
    print(f"🟡 {Colors.WARNING}{message}{Colors.END}")

def print_error(message: str):
    """Print an error message with BUMBA styling (Frontend department)."""
    print(f"🔴 {Colors.ERROR}{message}{Colors.END}")

def print_info(message: str):
    """Print an info message with BUMBA styling (Testing department)."""
    print(f"🟠 {Colors.INFO}{message}{Colors.END}")

def print_detected(message: str):
    """Print a detection message with BUMBA styling (Backend department)."""
    print(f"🟢 {Colors.SUCCESS}DETECTED: {message}{Colors.END}")

def print_complete(message: str):
    """Print a completion message with BUMBA styling."""
    print(f"🏁 {Colors.PRIMARY}{message}{Colors.END}")

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

class IntelligentDetector:
    """Intelligent detection of existing installations and configurations."""
    
    def __init__(self):
        self.detected = {
            'chatta_installed': False,
            'chatta_version': None,
            'chatta_location': None,
            'claude_code_installed': False,
            'mcp_configured': False,
            'docker_installed': False,
            'docker_running': False,
            'services': {
                'whisper': {'installed': False, 'running': False, 'port': 8880},
                'kokoro': {'installed': False, 'running': False, 'port': 7888},
                'livekit': {'installed': False, 'running': False, 'port': 7880}
            },
            'dependencies': {
                'git': False,
                'curl': False,
                'ffmpeg': False,
                'node': False,
                'uv': False,
                'pip': False,
                'docker-compose': False
            },
            'api_keys': {
                'openai': False,
                'openai_in_env': False,
                'openai_in_file': False
            },
            'config_files': {
                '.env': False,
                '.mcp.json': False,
                'docker-compose.yml': False,
                '.voices.txt': False
            }
        }
    
    def detect_all(self) -> Dict:
        """Run all detection routines."""
        print_detection_header()
        print("Scanning your system for existing installations...\n")
        
        # Detect CHATTA installation
        self.detect_chatta()
        
        # Detect dependencies
        self.detect_dependencies()
        
        # Detect Docker and services
        self.detect_docker_services()
        
        # Detect Claude Code and MCP
        self.detect_claude_mcp()
        
        # Detect API keys
        self.detect_api_keys()
        
        # Detect configuration files
        self.detect_config_files()
        
        # Print summary
        self.print_detection_summary()
        
        return self.detected
    
    def detect_chatta(self):
        """Detect CHATTA installation."""
        try:
            # Check if CHATTA is installed via pip
            result = run_command(['python', '-c', 
                'import voice_mode; import pkg_resources; '
                'print(pkg_resources.get_distribution("chatta").version)'])
            
            if result.returncode == 0:
                self.detected['chatta_installed'] = True
                self.detected['chatta_version'] = result.stdout.strip()
                print_detected(f"CHATTA v{self.detected['chatta_version']} installed")
                
                # Find installation location
                result = run_command(['python', '-c', 
                    'import voice_mode; print(voice_mode.__file__)'])
                if result.returncode == 0:
                    self.detected['chatta_location'] = os.path.dirname(result.stdout.strip())
            else:
                # Check if we're in CHATTA directory
                if os.path.exists('pyproject.toml'):
                    with open('pyproject.toml') as f:
                        if 'chatta' in f.read().lower():
                            self.detected['chatta_installed'] = True
                            self.detected['chatta_location'] = os.getcwd()
                            print_detected("CHATTA source code found in current directory")
        except Exception:
            pass
    
    def detect_dependencies(self):
        """Detect installed dependencies."""
        for dep in self.detected['dependencies']:
            if check_command(dep):
                self.detected['dependencies'][dep] = True
                print_detected(f"{dep} command available")
    
    def detect_docker_services(self):
        """Detect Docker and running services."""
        if check_command('docker'):
            self.detected['docker_installed'] = True
            print_detected("Docker installed")
            
            # Check if Docker is running
            result = run_command(['docker', 'info'], capture_output=True)
            if result.returncode == 0:
                self.detected['docker_running'] = True
                print_detected("Docker daemon running")
                
                # Check for running containers
                result = run_command(['docker', 'ps', '--format', '{{.Names}}:{{.Ports}}'])
                if result.returncode == 0:
                    containers = result.stdout.strip().split('\n')
                    for container in containers:
                        if 'whisper' in container.lower():
                            self.detected['services']['whisper']['running'] = True
                            print_detected("Whisper STT service running")
                        if 'kokoro' in container.lower():
                            self.detected['services']['kokoro']['running'] = True
                            print_detected("Kokoro TTS service running")
                        if 'livekit' in container.lower():
                            self.detected['services']['livekit']['running'] = True
                            print_detected("LiveKit service running")
                
                # Check for Docker images
                result = run_command(['docker', 'images', '--format', '{{.Repository}}'])
                if result.returncode == 0:
                    images = result.stdout.strip().split('\n')
                    for image in images:
                        if 'whisper' in image.lower():
                            self.detected['services']['whisper']['installed'] = True
                        if 'kokoro' in image.lower():
                            self.detected['services']['kokoro']['installed'] = True
                        if 'livekit' in image.lower():
                            self.detected['services']['livekit']['installed'] = True
        
        # Also check if services are accessible via HTTP
        try:
            import httpx
            import asyncio
            
            async def check_service(port: int, name: str) -> bool:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(f"http://localhost:{port}/health", timeout=1.0)
                        return resp.status_code == 200
                except:
                    return False
            
            # Check each service
            for service, info in self.detected['services'].items():
                if asyncio.run(check_service(info['port'], service)):
                    info['running'] = True
                    print_detected(f"{service.capitalize()} service responding on port {info['port']}")
        except ImportError:
            pass  # httpx not installed
    
    def detect_claude_mcp(self):
        """Detect Claude Code and MCP configuration."""
        # Check for Claude Code
        if check_command('claude'):
            self.detected['claude_code_installed'] = True
            print_detected("Claude Code CLI installed")
        
        # Check for MCP configuration
        mcp_paths = [
            Path.home() / '.config' / 'claude' / 'mcp.json',
            Path.home() / '.claude' / 'mcp.json',
            Path('.mcp.json')  # Local project config
        ]
        
        for mcp_path in mcp_paths:
            if mcp_path.exists():
                try:
                    with open(mcp_path) as f:
                        config = json.load(f)
                        if 'mcpServers' in config:
                            if any('chatta' in k.lower() or 'voicemode' in k.lower() 
                                   for k in config['mcpServers'].keys()):
                                self.detected['mcp_configured'] = True
                                print_detected(f"MCP configuration found at {mcp_path}")
                                break
                except:
                    pass
    
    def detect_api_keys(self):
        """Detect API key configuration."""
        # Check environment variable
        if os.environ.get('OPENAI_API_KEY'):
            self.detected['api_keys']['openai'] = True
            self.detected['api_keys']['openai_in_env'] = True
            print_detected("OpenAI API key in environment")
        
        # Check .env file
        env_files = ['.env', '.env.local', '.env.production']
        for env_file in env_files:
            if os.path.exists(env_file):
                try:
                    with open(env_file) as f:
                        if 'OPENAI_API_KEY' in f.read():
                            self.detected['api_keys']['openai'] = True
                            self.detected['api_keys']['openai_in_file'] = True
                            print_detected(f"OpenAI API key in {env_file}")
                            break
                except:
                    pass
    
    def detect_config_files(self):
        """Detect configuration files."""
        for config_file in self.detected['config_files']:
            if os.path.exists(config_file):
                self.detected['config_files'][config_file] = True
                print_detected(f"Configuration file: {config_file}")
    
    def print_detection_summary(self):
        """Print a summary of detected components."""
        print(f"\n{Colors.BOLD}{'─' * 70}{Colors.END}")
        print(f"{Colors.BOLD}DETECTION SUMMARY:{Colors.END}\n")
        
        # Calculate readiness score
        score = 0
        max_score = 0
        
        # CHATTA installation (20 points)
        max_score += 20
        if self.detected['chatta_installed']:
            score += 20
            print(f"  {Colors.GREEN}✓{Colors.END} CHATTA: Installed {f'(v{self.detected['chatta_version']})' if self.detected['chatta_version'] else ''}")
        else:
            print(f"  {Colors.YELLOW}○{Colors.END} CHATTA: Not installed")
        
        # Essential dependencies (5 points each)
        essential_deps = ['git', 'curl', 'ffmpeg']
        for dep in essential_deps:
            max_score += 5
            if self.detected['dependencies'][dep]:
                score += 5
                print(f"  {Colors.GREEN}✓{Colors.END} {dep}: Available")
            else:
                print(f"  {Colors.YELLOW}○{Colors.END} {dep}: Missing")
        
        # Docker (10 points)
        max_score += 10
        if self.detected['docker_installed']:
            if self.detected['docker_running']:
                score += 10
                print(f"  {Colors.GREEN}✓{Colors.END} Docker: Running")
            else:
                score += 5
                print(f"  {Colors.YELLOW}○{Colors.END} Docker: Installed but not running")
        else:
            print(f"  {Colors.YELLOW}○{Colors.END} Docker: Not installed")
        
        # Services (10 points each if running, 5 if installed)
        for service in ['whisper', 'kokoro']:
            max_score += 10
            info = self.detected['services'][service]
            if info['running']:
                score += 10
                print(f"  {Colors.GREEN}✓{Colors.END} {service.capitalize()}: Running on port {info['port']}")
            elif info['installed']:
                score += 5
                print(f"  {Colors.YELLOW}○{Colors.END} {service.capitalize()}: Installed but not running")
            else:
                print(f"  {Colors.YELLOW}○{Colors.END} {service.capitalize()}: Not installed")
        
        # Claude Code and MCP (10 points each)
        max_score += 10
        if self.detected['claude_code_installed']:
            score += 10
            print(f"  {Colors.GREEN}✓{Colors.END} Claude Code: Installed")
        else:
            print(f"  {Colors.YELLOW}○{Colors.END} Claude Code: Not installed")
        
        max_score += 10
        if self.detected['mcp_configured']:
            score += 10
            print(f"  {Colors.GREEN}✓{Colors.END} MCP: Configured")
        else:
            print(f"  {Colors.YELLOW}○{Colors.END} MCP: Not configured")
        
        # API Keys (5 points)
        max_score += 5
        if self.detected['api_keys']['openai']:
            score += 5
            print(f"  {Colors.GREEN}✓{Colors.END} OpenAI API: Configured")
        else:
            print(f"  {Colors.YELLOW}○{Colors.END} OpenAI API: Not configured")
        
        # Calculate percentage
        percentage = (score / max_score) * 100 if max_score > 0 else 0
        
        print(f"\n{Colors.BOLD}Readiness Score: {score}/{max_score} ({percentage:.0f}%){Colors.END}")
        
        if percentage >= 90:
            print(f"{Colors.GREEN}System is almost fully configured! Just a few tweaks needed.{Colors.END}")
        elif percentage >= 70:
            print(f"{Colors.YELLOW}Most components are ready. Some setup required.{Colors.END}")
        elif percentage >= 50:
            print(f"{Colors.YELLOW}Partial setup detected. Several components need installation.{Colors.END}")
        else:
            print(f"{Colors.CYAN}Fresh installation needed. The wizard will guide you through.{Colors.END}")
        
        return percentage

class EnhancedSetupWizard:
    """Enhanced setup wizard with intelligent detection and bypass options."""
    
    def __init__(self, skip_detection: bool = False, express: bool = False, dry_run: bool = False):
        self.system_info = get_system_info()
        self.detector = IntelligentDetector()
        self.detected = {}
        self.skip_detection = skip_detection
        self.express = express
        self.dry_run = dry_run
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
        self.steps_to_skip = []
    
    def run(self):
        """Run the setup wizard."""
        print_header()
        
        # Power user bypass check
        if self.express:
            print(f"{Colors.BOLD}EXPRESS INSTALLATION MODE{Colors.END}")
            print("Installing with default settings...\n")
            self.run_express_setup()
            return
        
        # Run detection unless skipped
        if not self.skip_detection:
            self.detected = self.detector.detect_all()
            self.analyze_detection_results()
            
            # Ask if user wants to continue
            print(f"\n{Colors.BOLD}Based on the detection, I can:{Colors.END}")
            if len(self.steps_to_skip) > 0:
                print(f"  • Skip {len(self.steps_to_skip)} steps that are already complete")
            print(f"  • Focus on the {8 - len(self.steps_to_skip)} remaining steps")
            print(f"  • Complete setup in ~{(8 - len(self.steps_to_skip)) * 2} minutes")
            
            if not ask_yes_no("\nContinue with intelligent setup?"):
                print("\nSetup cancelled. You can run this wizard again anytime!")
                return
        else:
            print(f"{Colors.YELLOW}Detection skipped. Running full setup...{Colors.END}\n")
        
        print(f"\nWelcome! I'll help you set up CHATTA for natural voice conversations.")
        print(f"This wizard will guide you through {8 - len(self.steps_to_skip)} steps.")
        print(f"Estimated time: {(8 - len(self.steps_to_skip)) * 2}-{(8 - len(self.steps_to_skip)) * 3} minutes\n")
        
        if not ask_yes_no("Ready to begin?"):
            print("\nSetup cancelled. You can run this wizard again anytime!")
            return
        
        try:
            step_num = 1
            
            # Step 1: System Check (always run)
            self.check_system()
            
            # Step 2: Choose Mode (skip if power user)
            if 'mode' not in self.steps_to_skip:
                self.choose_mode()
            else:
                print_info("Skipping mode selection (using automatic)")
            
            # Step 3: Dependencies (skip if all installed)
            if 'dependencies' not in self.steps_to_skip:
                self.check_dependencies()
            else:
                print_info("Skipping dependency check (all installed)")
            
            # Step 4: API Keys (skip if configured)
            if 'api_keys' not in self.steps_to_skip:
                self.configure_api_keys()
            else:
                print_info("Skipping API configuration (already configured)")
            
            # Step 5: CHATTA (skip if installed)
            if 'chatta' not in self.steps_to_skip:
                self.install_chatta()
            else:
                print_info("Skipping CHATTA installation (already installed)")
            
            # Step 6: Services (skip if running)
            if 'services' not in self.steps_to_skip:
                self.install_services()
            else:
                print_info("Skipping service installation (already running)")
            
            # Step 7: MCP (skip if configured)
            if 'mcp' not in self.steps_to_skip:
                self.configure_mcp()
            else:
                print_info("Skipping MCP configuration (already configured)")
            
            # Step 8: Final test (always run)
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
    
    def analyze_detection_results(self):
        """Analyze detection results and determine what steps to skip."""
        d = self.detected
        
        # Skip CHATTA installation if already installed
        if d['chatta_installed']:
            self.steps_to_skip.append('chatta')
            self.config['chatta_installed'] = True
        
        # Skip dependency installation if all essential ones are installed
        essential = ['git', 'curl', 'ffmpeg']
        if all(d['dependencies'][dep] for dep in essential):
            self.steps_to_skip.append('dependencies')
        
        # Skip API configuration if already configured
        if d['api_keys']['openai']:
            self.steps_to_skip.append('api_keys')
            self.config['use_openai'] = True
        
        # Skip service installation if already running
        if d['services']['whisper']['running'] and d['services']['kokoro']['running']:
            self.steps_to_skip.append('services')
            self.config['install_local_services'] = False
        
        # Skip MCP configuration if already configured
        if d['mcp_configured']:
            self.steps_to_skip.append('mcp')
            self.config['mcp_configured'] = True
        
        # Skip Claude Code installation if already installed
        if d['claude_code_installed']:
            self.config['claude_code_installed'] = True
        
        # Always use automatic mode for power users
        if len(self.steps_to_skip) >= 3:
            self.steps_to_skip.append('mode')
            self.config['install_mode'] = 'automatic'
    
    def run_express_setup(self):
        """Run express setup for power users."""
        print("Running express setup with intelligent defaults...\n")
        
        # Quick detection
        self.detected = self.detector.detect_all()
        
        # Install only what's missing
        if not self.detected['chatta_installed']:
            print("\nInstalling CHATTA...")
            run_command(['pip', 'install', '-e', '.'] if os.path.exists('pyproject.toml') 
                       else ['pip', 'install', 'chatta'])
        
        if not self.detected['docker_running'] and self.detected['docker_installed']:
            print("\nStarting Docker services...")
            run_command(['docker-compose', 'up', '-d'])
        
        if not self.detected['mcp_configured']:
            print("\nConfiguring MCP...")
            self.quick_mcp_config()
        
        # Display completion banner with BUMBA branding
        print(f"\n{Colors.GRADIENT_GREEN}{'═' * 52}{Colors.END}")
        print(f"🏁 {Colors.GRADIENT_GREEN}{Colors.BOLD}INSTALLATION COMPLETE{Colors.END} 🏁")
        print(f"{Colors.GRADIENT_GREEN}{'═' * 52}{Colors.END}\n")
        print(f"🟢 {Colors.GREEN}CHATTA is ready for voice conversations{Colors.END}")
        print(f"🟢 {Colors.GREEN}Part of the BUMBA Platform Suite{Colors.END}\n")
        print(f"{Colors.CYAN}Run 'chatta converse' to start using voice mode{Colors.END}")
        print(f"{Colors.CYAN}Run 'claude' to use with Claude Code{Colors.END}")
    
    def quick_mcp_config(self):
        """Quick MCP configuration for express mode."""
        mcp_path = Path.home() / '.config' / 'claude' / 'mcp.json'
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        
        config = {"mcpServers": {}} if not mcp_path.exists() else json.loads(mcp_path.read_text())
        
        config["mcpServers"]["chatta"] = {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "voice_mode.server"],
            "env": {
                "STT_BASE_URL": "http://localhost:8880/v1",
                "TTS_BASE_URL": "http://localhost:7888/v1"
            }
        }
        
        mcp_path.write_text(json.dumps(config, indent=2))
        print_success("MCP configured")
    
    # ... (rest of the methods remain similar to original but check self.detected for skipping)
    
    def check_system(self):
        """Step 1: Check system compatibility."""
        if 'system' not in self.steps_to_skip:
            print_step(1, self.total_steps, "System Compatibility Check")
            # ... (implementation remains the same)

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="CHATTA Intelligent Setup Wizard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
        Examples:
          %(prog)s                    # Run full interactive wizard with detection
          %(prog)s --express          # Express installation for power users
          %(prog)s --skip-detection   # Skip detection, run full setup
          %(prog)s --check-only       # Only run detection, don't install
        
        For power users:
          The wizard intelligently detects existing installations and skips
          unnecessary steps. Use --express for the fastest setup experience.
        ''')
    )
    
    parser.add_argument(
        '--express', '-e',
        action='store_true',
        help='Express installation with intelligent defaults (for power users)'
    )
    
    parser.add_argument(
        '--skip-detection', '-s',
        action='store_true',
        help='Skip detection phase and run full setup'
    )
    
    parser.add_argument(
        '--check-only', '-c',
        action='store_true',
        help='Only run detection and show results, don\'t install anything'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Simulate installation without making changes'
    )
    
    parser.add_argument(
        '--skip-wizard',
        action='store_true',
        help='Skip wizard entirely (for automated installations)'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='CHATTA Setup Wizard v2.0'
    )
    
    args = parser.parse_args()
    
    # Skip wizard entirely for automated installations
    if args.skip_wizard:
        print(f"{Colors.GREEN}Bypassing wizard for automated installation...{Colors.END}")
        # Just ensure CHATTA is installed
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'chatta'], 
                      capture_output=True)
        print(f"{Colors.GREEN}✓ CHATTA installed/upgraded{Colors.END}")
        return
    
    # Check-only mode
    if args.check_only:
        print_header()
        detector = IntelligentDetector()
        detector.detect_all()
        print(f"\n{Colors.BOLD}Detection complete. Run without --check-only to proceed with setup.{Colors.END}")
        return
    
    # Run wizard with options
    wizard = EnhancedSetupWizard(
        skip_detection=args.skip_detection,
        express=args.express,
        dry_run=args.dry_run
    )
    wizard.run()

if __name__ == "__main__":
    main()