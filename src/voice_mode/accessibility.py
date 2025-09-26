#!/usr/bin/env python3
"""
Accessibility features for voice mode interactions.

This module provides comprehensive accessibility support including:
- Screen reader integration
- Keyboard navigation
- High contrast modes
- Voice announcements
- ARIA attributes
- Focus management
"""

import asyncio
import platform
import subprocess
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import threading
import queue
import logging

logger = logging.getLogger(__name__)


class AccessibilityLevel(Enum):
    """Accessibility support levels."""
    NONE = auto()
    BASIC = auto()
    MODERATE = auto()
    FULL = auto()


class AnnouncementPriority(Enum):
    """Announcement priority levels."""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    URGENT = auto()


class ContrastMode(Enum):
    """Contrast modes for visual elements."""
    NORMAL = auto()
    HIGH = auto()
    DARK = auto()
    DARK_HIGH = auto()


@dataclass
class AccessibilityConfig:
    """Configuration for accessibility features."""
    screen_reader_enabled: bool = True
    voice_announcements: bool = True
    keyboard_navigation: bool = True
    high_contrast: bool = False
    contrast_mode: ContrastMode = ContrastMode.NORMAL
    announcement_verbosity: int = 2  # 0=minimal, 1=normal, 2=verbose
    focus_indicators: bool = True
    audio_cues: bool = True
    motion_reduced: bool = False
    font_size_multiplier: float = 1.0


class ScreenReaderInterface:
    """Interface for screen reader integration."""
    
    def __init__(self):
        """Initialize screen reader interface."""
        self.platform = platform.system()
        self._announcement_queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reader = threading.Event()
        self._is_available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if screen reader is available.
        
        Returns:
            True if screen reader is available
        """
        if self.platform == "Darwin":  # macOS
            # Check if VoiceOver is available
            try:
                result = subprocess.run(
                    ["osascript", "-e", "tell application \"System Events\" to get exists"],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except:
                return False
        elif self.platform == "Windows":
            # Check for NVDA or JAWS
            try:
                import win32api
                return True
            except ImportError:
                return False
        elif self.platform == "Linux":
            # Check for Orca
            try:
                result = subprocess.run(
                    ["which", "orca"],
                    capture_output=True
                )
                return result.returncode == 0
            except:
                return False
        return False
    
    def announce(self, text: str, priority: AnnouncementPriority = AnnouncementPriority.NORMAL):
        """Announce text via screen reader.
        
        Args:
            text: Text to announce
            priority: Announcement priority
        """
        if not self._is_available:
            logger.debug(f"Screen reader announcement: {text}")
            return
        
        self._announcement_queue.put((text, priority))
        
        if not self._reader_thread or not self._reader_thread.is_alive():
            self._start_reader_thread()
    
    def _start_reader_thread(self):
        """Start the screen reader thread."""
        self._stop_reader.clear()
        self._reader_thread = threading.Thread(target=self._reader_loop)
        self._reader_thread.daemon = True
        self._reader_thread.start()
    
    def _reader_loop(self):
        """Screen reader announcement loop."""
        while not self._stop_reader.is_set():
            try:
                text, priority = self._announcement_queue.get(timeout=0.1)
                self._speak(text, priority)
            except queue.Empty:
                continue
    
    def _speak(self, text: str, priority: AnnouncementPriority):
        """Speak text using platform-specific screen reader.
        
        Args:
            text: Text to speak
            priority: Speech priority
        """
        if self.platform == "Darwin":  # macOS VoiceOver
            # Use say command as a fallback
            subprocess.run(["say", text], capture_output=True)
        elif self.platform == "Windows":
            # Use SAPI
            try:
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(text)
            except:
                pass
        elif self.platform == "Linux":
            # Use espeak
            subprocess.run(["espeak", text], capture_output=True)
    
    def stop(self):
        """Stop screen reader interface."""
        self._stop_reader.set()
        if self._reader_thread:
            self._reader_thread.join(timeout=1.0)


class KeyboardNavigator:
    """Manages keyboard navigation for voice mode."""
    
    def __init__(self):
        """Initialize keyboard navigator."""
        self.focus_stack: List[str] = []
        self.focus_index = 0
        self.key_bindings: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._register_default_bindings()
    
    def _register_default_bindings(self):
        """Register default key bindings."""
        self.key_bindings = {
            "Tab": self.next_focus,
            "Shift+Tab": self.previous_focus,
            "Enter": self.activate_focused,
            "Space": self.toggle_focused,
            "Escape": self.cancel_operation,
            "F1": self.show_help,
            "Ctrl+L": self.start_listening,
            "Ctrl+S": self.stop_listening,
            "Ctrl+M": self.toggle_mute,
            "Ctrl+Plus": self.increase_volume,
            "Ctrl+Minus": self.decrease_volume,
        }
    
    def register_binding(self, key: str, callback: Callable):
        """Register a key binding.
        
        Args:
            key: Key combination
            callback: Function to call
        """
        with self._lock:
            self.key_bindings[key] = callback
            logger.debug(f"Registered key binding: {key}")
    
    def handle_key(self, key: str) -> bool:
        """Handle keyboard input.
        
        Args:
            key: Key combination pressed
            
        Returns:
            True if handled
        """
        with self._lock:
            if key in self.key_bindings:
                try:
                    self.key_bindings[key]()
                    return True
                except Exception as e:
                    logger.error(f"Key handler error for {key}: {e}")
        return False
    
    def add_focusable(self, element_id: str):
        """Add focusable element.
        
        Args:
            element_id: Element identifier
        """
        with self._lock:
            if element_id not in self.focus_stack:
                self.focus_stack.append(element_id)
    
    def remove_focusable(self, element_id: str):
        """Remove focusable element.
        
        Args:
            element_id: Element identifier
        """
        with self._lock:
            if element_id in self.focus_stack:
                self.focus_stack.remove(element_id)
                if self.focus_index >= len(self.focus_stack):
                    self.focus_index = max(0, len(self.focus_stack) - 1)
    
    def get_focused(self) -> Optional[str]:
        """Get currently focused element.
        
        Returns:
            Focused element ID or None
        """
        with self._lock:
            if 0 <= self.focus_index < len(self.focus_stack):
                return self.focus_stack[self.focus_index]
        return None
    
    def next_focus(self):
        """Move focus to next element."""
        with self._lock:
            if self.focus_stack:
                self.focus_index = (self.focus_index + 1) % len(self.focus_stack)
                logger.debug(f"Focus moved to: {self.focus_stack[self.focus_index]}")
    
    def previous_focus(self):
        """Move focus to previous element."""
        with self._lock:
            if self.focus_stack:
                self.focus_index = (self.focus_index - 1) % len(self.focus_stack)
                logger.debug(f"Focus moved to: {self.focus_stack[self.focus_index]}")
    
    # Placeholder methods for key bindings
    def activate_focused(self): pass
    def toggle_focused(self): pass
    def cancel_operation(self): pass
    def show_help(self): pass
    def start_listening(self): pass
    def stop_listening(self): pass
    def toggle_mute(self): pass
    def increase_volume(self): pass
    def decrease_volume(self): pass


class ContrastManager:
    """Manages contrast modes for accessibility."""
    
    def __init__(self):
        """Initialize contrast manager."""
        self.mode = ContrastMode.NORMAL
        self._color_schemes = self._init_color_schemes()
    
    def _init_color_schemes(self) -> Dict[ContrastMode, Dict[str, str]]:
        """Initialize color schemes for different contrast modes.
        
        Returns:
            Color schemes dictionary
        """
        return {
            ContrastMode.NORMAL: {
                "background": "#FFFFFF",
                "foreground": "#000000",
                "primary": "#007AFF",
                "secondary": "#5856D6",
                "success": "#34C759",
                "warning": "#FF9500",
                "error": "#FF3B30",
                "border": "#C6C6C8",
                "disabled": "#8E8E93"
            },
            ContrastMode.HIGH: {
                "background": "#FFFFFF",
                "foreground": "#000000",
                "primary": "#0051D5",
                "secondary": "#3634A3",
                "success": "#00843D",
                "warning": "#DD6B00",
                "error": "#D70015",
                "border": "#000000",
                "disabled": "#767676"
            },
            ContrastMode.DARK: {
                "background": "#000000",
                "foreground": "#FFFFFF",
                "primary": "#0A84FF",
                "secondary": "#5E5CE6",
                "success": "#30D158",
                "warning": "#FF9F0A",
                "error": "#FF453A",
                "border": "#38383A",
                "disabled": "#636366"
            },
            ContrastMode.DARK_HIGH: {
                "background": "#000000",
                "foreground": "#FFFFFF",
                "primary": "#409CFF",
                "secondary": "#7D7AFF",
                "success": "#30DB5B",
                "warning": "#FFB340",
                "error": "#FF6961",
                "border": "#FFFFFF",
                "disabled": "#8E8E93"
            }
        }
    
    def set_mode(self, mode: ContrastMode):
        """Set contrast mode.
        
        Args:
            mode: New contrast mode
        """
        self.mode = mode
        logger.info(f"Contrast mode set to: {mode.name}")
    
    def get_colors(self) -> Dict[str, str]:
        """Get current color scheme.
        
        Returns:
            Color scheme dictionary
        """
        return self._color_schemes[self.mode].copy()
    
    def get_color(self, element: str) -> str:
        """Get color for specific element.
        
        Args:
            element: Element name
            
        Returns:
            Color hex code
        """
        colors = self._color_schemes[self.mode]
        return colors.get(element, "#808080")
    
    def calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """Calculate contrast ratio between two colors.
        
        Args:
            color1: First color hex code
            color2: Second color hex code
            
        Returns:
            Contrast ratio
        """
        def get_luminance(hex_color: str) -> float:
            # Remove # if present
            hex_color = hex_color.lstrip("#")
            
            # Convert to RGB
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
            
            # Apply gamma correction
            r = r/12.92 if r <= 0.03928 else ((r+0.055)/1.055)**2.4
            g = g/12.92 if g <= 0.03928 else ((g+0.055)/1.055)**2.4
            b = b/12.92 if b <= 0.03928 else ((b+0.055)/1.055)**2.4
            
            # Calculate relative luminance
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        lum1 = get_luminance(color1)
        lum2 = get_luminance(color2)
        
        # Calculate contrast ratio
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    def meets_wcag_aa(self, color1: str, color2: str, large_text: bool = False) -> bool:
        """Check if color combination meets WCAG AA standards.
        
        Args:
            color1: First color
            color2: Second color
            large_text: Whether text is large (14pt bold or 18pt regular)
            
        Returns:
            True if meets AA standards
        """
        ratio = self.calculate_contrast_ratio(color1, color2)
        required_ratio = 3.0 if large_text else 4.5
        return ratio >= required_ratio


class VoiceAnnouncementSystem:
    """System for voice announcements and audio cues."""
    
    def __init__(self, config: Optional[AccessibilityConfig] = None):
        """Initialize voice announcement system.
        
        Args:
            config: Accessibility configuration
        """
        self.config = config or AccessibilityConfig()
        self.screen_reader = ScreenReaderInterface()
        self._audio_cues: Dict[str, str] = self._init_audio_cues()
        self._announcement_history: List[Tuple[str, float]] = []
        self._lock = threading.Lock()
    
    def _init_audio_cues(self) -> Dict[str, str]:
        """Initialize audio cue mappings.
        
        Returns:
            Audio cue dictionary
        """
        return {
            "start_listening": "chime_up.wav",
            "stop_listening": "chime_down.wav",
            "processing": "processing.wav",
            "success": "success.wav",
            "error": "error.wav",
            "notification": "notification.wav",
            "focus_change": "tick.wav",
            "connection_established": "connected.wav",
            "connection_lost": "disconnected.wav"
        }
    
    def announce(
        self,
        text: str,
        priority: AnnouncementPriority = AnnouncementPriority.NORMAL,
        audio_cue: Optional[str] = None
    ):
        """Make voice announcement.
        
        Args:
            text: Text to announce
            priority: Announcement priority
            audio_cue: Optional audio cue to play
        """
        if not self.config.voice_announcements:
            return
        
        # Apply verbosity filter
        if self.config.announcement_verbosity == 0 and priority < AnnouncementPriority.HIGH:
            return
        elif self.config.announcement_verbosity == 1 and priority < AnnouncementPriority.NORMAL:
            return
        
        # Play audio cue if specified
        if audio_cue and self.config.audio_cues:
            self._play_audio_cue(audio_cue)
        
        # Make announcement
        self.screen_reader.announce(text, priority)
        
        # Record in history
        import time
        with self._lock:
            self._announcement_history.append((text, time.time()))
            # Keep only last 100 announcements
            if len(self._announcement_history) > 100:
                self._announcement_history.pop(0)
    
    def _play_audio_cue(self, cue_name: str):
        """Play audio cue.
        
        Args:
            cue_name: Name of audio cue
        """
        if cue_name in self._audio_cues:
            # In production, this would play the actual audio file
            logger.debug(f"Playing audio cue: {cue_name}")
    
    def announce_state_change(self, old_state: str, new_state: str):
        """Announce state change.
        
        Args:
            old_state: Previous state
            new_state: New state
        """
        text = f"State changed from {old_state} to {new_state}"
        
        # Determine audio cue based on state
        audio_cue = None
        if new_state == "listening":
            audio_cue = "start_listening"
        elif old_state == "listening":
            audio_cue = "stop_listening"
        elif new_state == "processing":
            audio_cue = "processing"
        elif new_state == "error":
            audio_cue = "error"
        
        self.announce(text, AnnouncementPriority.HIGH, audio_cue)
    
    def announce_progress(self, percentage: int, message: str = ""):
        """Announce progress update.
        
        Args:
            percentage: Progress percentage
            message: Optional message
        """
        if self.config.announcement_verbosity < 2:
            # Only announce at key milestones in non-verbose mode
            if percentage not in [25, 50, 75, 100]:
                return
        
        text = f"{percentage}% complete"
        if message:
            text += f": {message}"
        
        self.announce(text, AnnouncementPriority.LOW)
    
    def get_announcement_history(self) -> List[str]:
        """Get recent announcement history.
        
        Returns:
            List of recent announcements
        """
        with self._lock:
            return [text for text, _ in self._announcement_history[-10:]]


class ARIAAttributeManager:
    """Manages ARIA attributes for web interfaces."""
    
    def __init__(self):
        """Initialize ARIA attribute manager."""
        self.attributes: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()
    
    def set_attributes(self, element_id: str, **attributes):
        """Set ARIA attributes for element.
        
        Args:
            element_id: Element identifier
            **attributes: ARIA attributes to set
        """
        with self._lock:
            if element_id not in self.attributes:
                self.attributes[element_id] = {}
            
            self.attributes[element_id].update(attributes)
            logger.debug(f"Updated ARIA attributes for {element_id}: {attributes}")
    
    def get_attributes(self, element_id: str) -> Dict[str, str]:
        """Get ARIA attributes for element.
        
        Args:
            element_id: Element identifier
            
        Returns:
            ARIA attributes dictionary
        """
        with self._lock:
            return self.attributes.get(element_id, {}).copy()
    
    def set_live_region(
        self,
        element_id: str,
        politeness: str = "polite",
        atomic: bool = True,
        relevant: str = "additions text"
    ):
        """Configure element as ARIA live region.
        
        Args:
            element_id: Element identifier
            politeness: assertive or polite
            atomic: Whether to announce entire region
            relevant: What changes to announce
        """
        self.set_attributes(
            element_id,
            aria_live=politeness,
            aria_atomic=str(atomic).lower(),
            aria_relevant=relevant
        )
    
    def set_role(self, element_id: str, role: str):
        """Set ARIA role for element.
        
        Args:
            element_id: Element identifier
            role: ARIA role
        """
        self.set_attributes(element_id, role=role)
    
    def set_label(self, element_id: str, label: str):
        """Set ARIA label for element.
        
        Args:
            element_id: Element identifier
            label: Accessible label
        """
        self.set_attributes(element_id, aria_label=label)
    
    def set_description(self, element_id: str, description: str):
        """Set ARIA description for element.
        
        Args:
            element_id: Element identifier
            description: Accessible description
        """
        self.set_attributes(element_id, aria_describedby=description)


class AccessibilityManager:
    """Main accessibility manager integrating all features."""
    
    def __init__(self, config: Optional[AccessibilityConfig] = None):
        """Initialize accessibility manager.
        
        Args:
            config: Accessibility configuration
        """
        self.config = config or AccessibilityConfig()
        self.screen_reader = ScreenReaderInterface()
        self.keyboard_nav = KeyboardNavigator()
        self.contrast_mgr = ContrastManager()
        self.voice_system = VoiceAnnouncementSystem(self.config)
        self.aria_mgr = ARIAAttributeManager()
        
        # Apply initial configuration
        self._apply_config()
    
    def _apply_config(self):
        """Apply accessibility configuration."""
        # Set contrast mode
        if self.config.high_contrast:
            if self.config.contrast_mode in [ContrastMode.DARK, ContrastMode.DARK_HIGH]:
                self.contrast_mgr.set_mode(ContrastMode.DARK_HIGH)
            else:
                self.contrast_mgr.set_mode(ContrastMode.HIGH)
        else:
            self.contrast_mgr.set_mode(self.config.contrast_mode)
        
        logger.info(f"Accessibility configured: {self.config}")
    
    def update_config(self, **kwargs):
        """Update accessibility configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        self._apply_config()
    
    def announce(self, text: str, priority: AnnouncementPriority = AnnouncementPriority.NORMAL):
        """Make accessibility announcement.
        
        Args:
            text: Text to announce
            priority: Announcement priority
        """
        self.voice_system.announce(text, priority)
    
    def register_element(
        self,
        element_id: str,
        role: str,
        label: str,
        focusable: bool = True
    ):
        """Register UI element for accessibility.
        
        Args:
            element_id: Element identifier
            role: ARIA role
            label: Accessible label
            focusable: Whether element is focusable
        """
        # Set ARIA attributes
        self.aria_mgr.set_role(element_id, role)
        self.aria_mgr.set_label(element_id, label)
        
        # Add to keyboard navigation if focusable
        if focusable and self.config.keyboard_navigation:
            self.keyboard_nav.add_focusable(element_id)
        
        logger.debug(f"Registered accessible element: {element_id}")
    
    def get_accessibility_info(self) -> Dict[str, Any]:
        """Get accessibility information.
        
        Returns:
            Accessibility status and configuration
        """
        return {
            "config": {
                "screen_reader": self.config.screen_reader_enabled,
                "voice_announcements": self.config.voice_announcements,
                "keyboard_navigation": self.config.keyboard_navigation,
                "high_contrast": self.config.high_contrast,
                "contrast_mode": self.config.contrast_mode.name,
                "verbosity": self.config.announcement_verbosity,
                "motion_reduced": self.config.motion_reduced,
                "font_size": self.config.font_size_multiplier
            },
            "status": {
                "screen_reader_available": self.screen_reader._is_available,
                "focused_element": self.keyboard_nav.get_focused(),
                "num_focusable": len(self.keyboard_nav.focus_stack),
                "contrast_ratio": self.contrast_mgr.calculate_contrast_ratio(
                    self.contrast_mgr.get_color("foreground"),
                    self.contrast_mgr.get_color("background")
                )
            },
            "colors": self.contrast_mgr.get_colors(),
            "announcement_history": self.voice_system.get_announcement_history()
        }
    
    def check_wcag_compliance(self) -> Dict[str, bool]:
        """Check WCAG compliance.
        
        Returns:
            Compliance status dictionary
        """
        colors = self.contrast_mgr.get_colors()
        
        return {
            "text_contrast_aa": self.contrast_mgr.meets_wcag_aa(
                colors["foreground"],
                colors["background"]
            ),
            "large_text_contrast_aa": self.contrast_mgr.meets_wcag_aa(
                colors["foreground"],
                colors["background"],
                large_text=True
            ),
            "keyboard_accessible": self.config.keyboard_navigation,
            "screen_reader_compatible": self.config.screen_reader_enabled,
            "focus_indicators": self.config.focus_indicators,
            "motion_reduced": self.config.motion_reduced
        }
    
    def shutdown(self):
        """Shutdown accessibility manager."""
        self.screen_reader.stop()
        logger.info("Accessibility manager shutdown")


# Export main components
__all__ = [
    "AccessibilityLevel",
    "AnnouncementPriority",
    "ContrastMode",
    "AccessibilityConfig",
    "ScreenReaderInterface",
    "KeyboardNavigator",
    "ContrastManager",
    "VoiceAnnouncementSystem",
    "ARIAAttributeManager",
    "AccessibilityManager"
]