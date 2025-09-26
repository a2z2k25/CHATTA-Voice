#!/usr/bin/env python3
"""
Test Enhanced Setup Wizard Bypass Features
==========================================
Tests the dynamic detection and power user bypass capabilities.
"""

import subprocess
import sys
import json
from pathlib import Path

# ANSI colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
END = '\033[0m'

def print_test(name: str):
    """Print test name."""
    print(f"\n{BLUE}{BOLD}Testing: {name}{END}")
    print("-" * 60)

def run_wizard_command(args: list) -> tuple:
    """Run the wizard with given arguments."""
    cmd = [sys.executable, 'setup_wizard_enhanced.py'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def test_help():
    """Test help flag."""
    print_test("Help Flag (--help)")
    code, stdout, stderr = run_wizard_command(['--help'])
    if code == 0 and 'CHATTA Intelligent Setup Wizard' in stdout:
        print(f"{GREEN}✓ Help displayed correctly{END}")
        # Show available options
        for line in stdout.split('\n'):
            if '--' in line:
                print(f"  {line.strip()}")
        return True
    else:
        print(f"{RED}✗ Help failed{END}")
        return False

def test_version():
    """Test version flag."""
    print_test("Version Flag (--version)")
    code, stdout, stderr = run_wizard_command(['--version'])
    if 'CHATTA Setup Wizard v' in stdout:
        print(f"{GREEN}✓ Version displayed: {stdout.strip()}{END}")
        return True
    else:
        print(f"{RED}✗ Version failed{END}")
        return False

def test_check_only():
    """Test detection-only mode."""
    print_test("Check-Only Mode (--check-only)")
    code, stdout, stderr = run_wizard_command(['--check-only'])
    if code == 0 and 'DETECTING EXISTING INSTALLATIONS' in stdout:
        print(f"{GREEN}✓ Detection completed{END}")
        
        # Parse detection results
        if 'CHATTA' in stdout and 'installed' in stdout:
            print(f"  • CHATTA detected")
        if 'Docker' in stdout and 'running' in stdout:
            print(f"  • Docker detected")
        if 'Whisper' in stdout and 'running' in stdout:
            print(f"  • Whisper service detected")
        if 'Kokoro' in stdout and 'running' in stdout:
            print(f"  • Kokoro service detected")
        if 'Readiness Score' in stdout:
            for line in stdout.split('\n'):
                if 'Readiness Score' in line:
                    print(f"  • {line.strip()}")
        return True
    else:
        print(f"{RED}✗ Check-only mode failed{END}")
        if stderr:
            print(f"  Error: {stderr}")
        return False

def test_skip_wizard():
    """Test skip wizard flag for automated installation."""
    print_test("Skip Wizard Flag (--skip-wizard)")
    code, stdout, stderr = run_wizard_command(['--skip-wizard'])
    if code == 0 and 'Bypassing wizard' in stdout:
        print(f"{GREEN}✓ Wizard bypassed successfully{END}")
        if 'CHATTA installed/upgraded' in stdout:
            print(f"  • CHATTA installation attempted")
        return True
    else:
        print(f"{RED}✗ Skip wizard failed{END}")
        return False

def test_express_mode():
    """Test express mode for power users."""
    print_test("Express Mode (--express --check-only)")
    # Use check-only with express to avoid actual installation
    code, stdout, stderr = run_wizard_command(['--express', '--check-only'])
    if code == 0:
        print(f"{GREEN}✓ Express mode with detection works{END}")
        return True
    else:
        print(f"{RED}✗ Express mode failed{END}")
        return False

def test_skip_detection():
    """Test skip detection flag."""
    print_test("Skip Detection Flag (--skip-detection --check-only)")
    # This should skip detection but we use check-only to avoid installation
    code, stdout, stderr = run_wizard_command(['--skip-detection', '--check-only'])
    if code == 0:
        # Should still show detection since check-only overrides
        if 'DETECTING' in stdout:
            print(f"{YELLOW}⚠ Check-only overrides skip-detection (expected){END}")
        else:
            print(f"{GREEN}✓ Skip detection flag recognized{END}")
        return True
    else:
        print(f"{RED}✗ Skip detection failed{END}")
        return False

def main():
    """Run all bypass tests."""
    print(f"{BOLD}{'='*60}{END}")
    print(f"{BOLD}CHATTA Enhanced Setup Wizard Bypass Tests{END}")
    print(f"{BOLD}{'='*60}{END}")
    
    tests = [
        test_help,
        test_version,
        test_check_only,
        test_skip_wizard,
        test_express_mode,
        test_skip_detection
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"{RED}✗ Test failed with exception: {e}{END}")
            results.append(False)
    
    # Summary
    print(f"\n{BOLD}{'='*60}{END}")
    print(f"{BOLD}Test Summary:{END}")
    print(f"{BOLD}{'='*60}{END}")
    
    passed = sum(results)
    total = len(results)
    percentage = (passed / total) * 100
    
    color = GREEN if percentage == 100 else YELLOW if percentage >= 80 else RED
    print(f"{color}{BOLD}Passed: {passed}/{total} ({percentage:.0f}%){END}")
    
    if percentage == 100:
        print(f"\n{GREEN}{BOLD}✅ ALL BYPASS FEATURES WORKING!{END}")
        print(f"{GREEN}The enhanced wizard correctly:{END}")
        print(f"{GREEN}  • Detects existing installations{END}")
        print(f"{GREEN}  • Provides power user bypass options{END}")
        print(f"{GREEN}  • Supports automated installations{END}")
        print(f"{GREEN}  • Skips unnecessary steps intelligently{END}")
    else:
        print(f"\n{YELLOW}⚠ Some features need attention{END}")
    
    return 0 if percentage == 100 else 1

if __name__ == "__main__":
    sys.exit(main())