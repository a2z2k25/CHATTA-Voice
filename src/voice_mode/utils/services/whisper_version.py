"""Helper functions to get whisper.cpp version and capabilities."""

import subprocess
import re
from pathlib import Path
from typing import Dict, Any, Optional


def get_whisper_version_info() -> Dict[str, Any]:
    """Get version and capability information for whisper.cpp.
    
    Returns:
        Dict containing version, commit hash, Core ML support status, etc.
    """
    info = {
        "version": None,
        "commit": None,
        "coreml_supported": False,
        "metal_supported": False,
        "cuda_supported": False,
        "build_type": None
    }
    
    # Find whisper-cli binary
    whisper_dir = Path.home() / ".voicemode" / "services" / "whisper"
    whisper_cli = whisper_dir / "build" / "bin" / "whisper-cli"
    
    # Fallback to legacy location
    if not whisper_cli.exists():
        whisper_cli = whisper_dir / "main"
    
    if not whisper_cli.exists():
        return info
    
    try:
        # Get version from git if available
        if (whisper_dir / ".git").exists():
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=whisper_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                info["version"] = result.stdout.strip()
            
            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=whisper_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                info["commit"] = result.stdout.strip()
        
        # Run whisper-cli to check capabilities
        # Use a non-existent file to make it fail quickly but still show system info
        result = subprocess.run(
            [str(whisper_cli), "-h"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            output = result.stdout + result.stderr
            
            # Check for Core ML support in help text or by running with dummy input
            # Try running with minimal command to get system info
            test_result = subprocess.run(
                [str(whisper_cli), "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # The system_info line shows what's compiled in
            # We need to actually run it to see the capabilities
            # Let's try with a non-existent model to fail fast but show system info
            test_result = subprocess.run(
                [str(whisper_cli), "-m", "nonexistent.bin"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            test_output = test_result.stdout + test_result.stderr
            
            # Parse system_info line for capabilities
            if "COREML = 1" in test_output:
                info["coreml_supported"] = True
            elif "COREML = 0" in test_output:
                info["coreml_supported"] = False
                
            if "Metal" in test_output:
                info["metal_supported"] = True
                
            if "CUDA = 1" in test_output or "CUBLAS = 1" in test_output:
                info["cuda_supported"] = True
        
        # Check if this is a CMake or Make build
        if (whisper_dir / "build" / "CMakeCache.txt").exists():
            info["build_type"] = "CMake"
            
            # Parse CMake cache for feature flags
            with open(whisper_dir / "build" / "CMakeCache.txt") as f:
                cmake_content = f.read()
                if "WHISPER_COREML:BOOL=ON" in cmake_content:
                    info["coreml_supported"] = True
                if "GGML_METAL:BOOL=ON" in cmake_content or "WHISPER_METAL:BOOL=ON" in cmake_content:
                    info["metal_supported"] = True
                if "GGML_CUDA:BOOL=ON" in cmake_content or "WHISPER_CUDA:BOOL=ON" in cmake_content:
                    info["cuda_supported"] = True
        else:
            info["build_type"] = "Make"
            
    except Exception as e:
        # Silently handle errors
        pass
    
    return info


def check_coreml_model_exists(model_name: str) -> bool:
    """Check if a Core ML model exists for the given whisper model.
    
    Args:
        model_name: Name of the whisper model (e.g., "large-v3-turbo")
        
    Returns:
        True if Core ML model exists, False otherwise
    """
    whisper_dir = Path.home() / ".voicemode" / "services" / "whisper"
    coreml_model = whisper_dir / "models" / f"ggml-{model_name}-encoder.mlmodelc"
    return coreml_model.exists()