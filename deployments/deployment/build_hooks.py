"""Build hooks for compiling the frontend during Python package build."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Custom build hook to compile the Next.js frontend."""
    
    PLUGIN_NAME = "custom"
    
    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """Initialize the build hook and compile frontend if needed."""
        super().initialize(version, build_data)
        
        # Only build frontend for wheel builds (not sdist)
        if self.target_name != "wheel":
            return
        
        frontend_dir = Path("voice_mode/frontend")
        if not frontend_dir.exists():
            print("Frontend directory not found, skipping frontend build")
            return
            
        # Check if we should build the frontend
        should_build = os.environ.get("BUILD_FRONTEND", "auto").lower()
        
        if should_build == "false":
            print("Skipping frontend build (BUILD_FRONTEND=false)")
            return
        elif should_build == "true":
            print("Building frontend (BUILD_FRONTEND=true)")
            self._build_frontend(frontend_dir)
        elif should_build == "auto":
            # Auto-detect: build if Node.js is available and no build exists
            build_dir = frontend_dir / ".next"
            if build_dir.exists():
                print("Found existing frontend build, skipping rebuild")
                return
            elif self._check_nodejs():
                print("Node.js available, building frontend automatically")
                self._build_frontend(frontend_dir)
            else:
                print("Node.js not available, including source files only")
                print("Users will need Node.js for development mode")
    
    def _check_nodejs(self) -> bool:
        """Check if Node.js is available."""
        try:
            subprocess.run(["node", "--version"], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _build_frontend(self, frontend_dir: Path) -> None:
        """Build the frontend using available package manager."""
        print("Building Next.js frontend for production...")
        
        # Change to frontend directory
        original_cwd = os.getcwd()
        try:
            os.chdir(frontend_dir)
            
            # Check if dependencies are installed
            if not (frontend_dir / "node_modules").exists():
                print("Installing frontend dependencies...")
                self._install_dependencies()
            
            # Build the frontend
            print("Compiling frontend...")
            env = os.environ.copy()
            env["BUILD_STANDALONE"] = "true"
            
            subprocess.run(
                ["npm", "run", "build:standalone"],
                check=True,
                env=env
            )
            
            print("✅ Frontend built successfully")
            
            # Verify build output
            build_dir = frontend_dir / ".next"
            if build_dir.exists():
                standalone_dir = build_dir / "standalone"
                static_dir = build_dir / "static"
                
                if standalone_dir.exists():
                    print(f"   Standalone server: {standalone_dir}")
                if static_dir.exists():
                    print(f"   Static assets: {static_dir}")
            else:
                raise RuntimeError("Build completed but .next directory not found")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Frontend build failed: {e}")
            print("   Users will need to run the frontend in development mode")
            # Don't fail the Python build, just warn
        except Exception as e:
            print(f"❌ Unexpected error during frontend build: {e}")
            # Don't fail the Python build
        finally:
            os.chdir(original_cwd)
    
    def _install_dependencies(self) -> None:
        """Install frontend dependencies using available package manager."""
        # Try package managers in order of preference
        for pm in ["pnpm", "npm", "yarn"]:
            try:
                subprocess.run([pm, "--version"], 
                             capture_output=True, check=True)
                print(f"Using {pm} to install dependencies...")
                subprocess.run([pm, "install"], check=True)
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        raise RuntimeError("No package manager found (tried pnpm, npm, yarn)")