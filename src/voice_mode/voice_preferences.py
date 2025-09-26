"""Voice preferences system for loading user/project voice preferences."""

import os
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("voice-mode")

# Cache for loaded preferences
_cached_preferences: Optional[List[str]] = None
_preferences_loaded = False


def find_voices_file() -> Optional[Path]:
    """
    Find the first .voices.txt file by walking up the directory tree.
    
    Looks for (in order):
    1. .voices.txt in current or parent directories
    2. .voicemode/voices.txt in current or parent directories
    3. ~/.voices.txt in user home
    4. ~/.voicemode/voices.txt in user home
    
    Returns:
        Path to .voices.txt file or None if not found
    """
    # Start from current working directory
    current_dir = Path.cwd()
    
    # Walk up directory tree
    while True:
        # Check for standalone .voices.txt first
        standalone_file = current_dir / ".voices.txt"
        if standalone_file.exists():
            logger.info(f"Found voice preferences at: {standalone_file}")
            return standalone_file
            
        # Then check .voicemode/voices.txt
        voicemode_file = current_dir / ".voicemode" / "voices.txt"
        if voicemode_file.exists():
            logger.info(f"Found voice preferences at: {voicemode_file}")
            return voicemode_file
        
        # Check if we've reached the root
        parent = current_dir.parent
        if parent == current_dir:
            break
        current_dir = parent
    
    # Check user home directory - standalone first
    home_standalone = Path.home() / ".voices.txt"
    if home_standalone.exists():
        logger.info(f"Found voice preferences at: {home_standalone}")
        return home_standalone
        
    # Then .voicemode directory
    home_voicemode = Path.home() / ".voicemode" / "voices.txt"
    if home_voicemode.exists():
        logger.info(f"Found voice preferences at: {home_voicemode}")
        return home_voicemode
    
    logger.debug("No voice preferences file found")
    return None


def load_voice_preferences() -> List[str]:
    """
    Load voice preferences from .voices.txt file.
    
    Returns:
        List of voice names in preference order, or empty list if no file found
    """
    global _cached_preferences, _preferences_loaded
    
    # Return cached preferences if already loaded
    if _preferences_loaded:
        return _cached_preferences or []
    
    _preferences_loaded = True
    
    # Find voices file
    voices_file = find_voices_file()
    if not voices_file:
        _cached_preferences = []
        return []
    
    # Load preferences
    try:
        with open(voices_file, 'r') as f:
            # Read lines, strip whitespace, skip empty lines and comments
            voices = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    voices.append(line)
        
        logger.info(f"Loaded {len(voices)} voice preferences: {', '.join(voices)}")
        _cached_preferences = voices
        return voices
        
    except Exception as e:
        logger.error(f"Error loading voice preferences from {voices_file}: {e}")
        _cached_preferences = []
        return []


def get_preferred_voices() -> List[str]:
    """
    Get the list of preferred voices, loading from file if needed.
    
    This is the main API for getting voice preferences.
    
    Returns:
        List of voice names in preference order
    """
    return load_voice_preferences()


def clear_cache():
    """Clear the preferences cache, forcing a reload on next access."""
    global _cached_preferences, _preferences_loaded
    _cached_preferences = None
    _preferences_loaded = False
    logger.debug("Voice preferences cache cleared")