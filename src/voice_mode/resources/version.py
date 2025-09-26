"""Version information resource."""

from voice_mode.server import mcp
from voice_mode.version import __version__, get_git_commit_hash, is_git_repository
import platform
import sys
import os


@mcp.resource("voice-mode:version")
async def get_version_info() -> str:
    """Get detailed version information about Voice Mode.
    
    Shows version, git status, Python version, and platform details.
    """
    lines = []
    lines.append(f"Voice Mode Version: {__version__}")
    
    # Add git information if available
    if is_git_repository():
        commit = get_git_commit_hash(short=False)
        if commit:
            lines.append(f"Git Commit: {commit}")
        
        # Check if installed via pip editable
        try:
            import voice_mode
            if hasattr(voice_mode, "__file__"):
                module_path = voice_mode.__file__
                if "site-packages" not in module_path:
                    lines.append("Installation: Development (editable)")
                else:
                    lines.append("Installation: Package")
        except:
            pass
    else:
        lines.append("Installation: Package (no git)")
    
    # Add Python and platform info
    lines.append(f"Python: {sys.version.split()[0]}")
    lines.append(f"Platform: {platform.system()} {platform.release()}")
    
    # Add base directory
    base_dir = os.environ.get("VOICEMODE_BASE_DIR", "~/.voicemode")
    lines.append(f"Base Directory: {os.path.expanduser(base_dir)}")
    
    return "\n".join(lines)