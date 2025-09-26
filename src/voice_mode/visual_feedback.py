#!/usr/bin/env python3
"""
Visual feedback indicators for voice mode interactions.

This module provides visual feedback components including:
- Voice activity indicators
- Connection status displays
- Progress indicators
- State visualizations
- Error notifications
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import threading
from collections import deque
import logging

logger = logging.getLogger(__name__)


class IndicatorState(Enum):
    """Visual indicator states."""
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    ERROR = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()


class AnimationStyle(Enum):
    """Animation styles for indicators."""
    PULSE = auto()
    SPIN = auto()
    WAVE = auto()
    DOTS = auto()
    BAR = auto()
    RING = auto()


@dataclass
class IndicatorConfig:
    """Configuration for visual indicators."""
    style: AnimationStyle = AnimationStyle.PULSE
    color_scheme: Dict[IndicatorState, str] = field(default_factory=lambda: {
        IndicatorState.IDLE: "#808080",
        IndicatorState.LISTENING: "#4CAF50",
        IndicatorState.PROCESSING: "#2196F3",
        IndicatorState.SPEAKING: "#9C27B0",
        IndicatorState.ERROR: "#F44336",
        IndicatorState.CONNECTING: "#FF9800",
        IndicatorState.CONNECTED: "#4CAF50",
        IndicatorState.DISCONNECTED: "#9E9E9E"
    })
    animation_speed: float = 1.0
    show_text: bool = True
    show_timer: bool = True
    show_level_meter: bool = True


class VoiceActivityIndicator:
    """Visual indicator for voice activity."""
    
    def __init__(self, config: Optional[IndicatorConfig] = None):
        """Initialize voice activity indicator.
        
        Args:
            config: Indicator configuration
        """
        self.config = config or IndicatorConfig()
        self.state = IndicatorState.IDLE
        self.audio_level = 0.0
        self.state_start_time = time.time()
        self._lock = threading.Lock()
        self._animation_frame = 0
        self._animation_thread: Optional[threading.Thread] = None
        self._stop_animation = threading.Event()
        
    def set_state(self, state: IndicatorState):
        """Set indicator state.
        
        Args:
            state: New indicator state
        """
        with self._lock:
            if self.state != state:
                self.state = state
                self.state_start_time = time.time()
                logger.debug(f"Voice indicator state: {state.name}")
    
    def set_audio_level(self, level: float):
        """Update audio level for visualization.
        
        Args:
            level: Audio level (0.0 to 1.0)
        """
        with self._lock:
            self.audio_level = max(0.0, min(1.0, level))
    
    def get_display_text(self) -> str:
        """Get current display text.
        
        Returns:
            Display text for current state
        """
        state_text = {
            IndicatorState.IDLE: "Ready",
            IndicatorState.LISTENING: "Listening...",
            IndicatorState.PROCESSING: "Processing...",
            IndicatorState.SPEAKING: "Speaking...",
            IndicatorState.ERROR: "Error",
            IndicatorState.CONNECTING: "Connecting...",
            IndicatorState.CONNECTED: "Connected",
            IndicatorState.DISCONNECTED: "Disconnected"
        }
        
        text = state_text.get(self.state, "Unknown")
        
        if self.config.show_timer and self.state not in [IndicatorState.IDLE, IndicatorState.ERROR]:
            elapsed = time.time() - self.state_start_time
            text += f" ({elapsed:.1f}s)"
        
        return text
    
    def get_animation_frame(self) -> str:
        """Get current animation frame.
        
        Returns:
            ASCII animation frame
        """
        if self.config.style == AnimationStyle.PULSE:
            frames = ["◯", "◉", "●", "◉"]
        elif self.config.style == AnimationStyle.SPIN:
            frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        elif self.config.style == AnimationStyle.WAVE:
            frames = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"]
        elif self.config.style == AnimationStyle.DOTS:
            frames = ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"]
        elif self.config.style == AnimationStyle.BAR:
            frames = ["▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
        else:  # RING
            frames = ["○", "◔", "◑", "◕", "●", "◕", "◑", "◔"]
        
        with self._lock:
            frame = frames[self._animation_frame % len(frames)]
            self._animation_frame += 1
            
        return frame
    
    def get_level_meter(self) -> str:
        """Get audio level meter visualization.
        
        Returns:
            Level meter string
        """
        if not self.config.show_level_meter:
            return ""
        
        with self._lock:
            level = self.audio_level
        
        # Create level meter with 10 segments
        filled = int(level * 10)
        meter = "▮" * filled + "▯" * (10 - filled)
        
        return f"[{meter}]"
    
    def start_animation(self):
        """Start animation thread."""
        if self._animation_thread and self._animation_thread.is_alive():
            return
        
        self._stop_animation.clear()
        self._animation_thread = threading.Thread(target=self._animate)
        self._animation_thread.daemon = True
        self._animation_thread.start()
    
    def stop_animation(self):
        """Stop animation thread."""
        self._stop_animation.set()
        if self._animation_thread:
            self._animation_thread.join(timeout=1.0)
    
    def _animate(self):
        """Animation loop."""
        frame_delay = 0.1 / self.config.animation_speed
        
        while not self._stop_animation.is_set():
            self._animation_frame += 1
            time.sleep(frame_delay)


class ConnectionStatusDisplay:
    """Display for connection status."""
    
    def __init__(self):
        """Initialize connection status display."""
        self.connected = False
        self.latency_ms = 0
        self.signal_strength = 0  # 0-4 bars
        self.service_name = "Unknown"
        self.error_message: Optional[str] = None
        self._lock = threading.Lock()
    
    def update_status(
        self,
        connected: bool,
        latency_ms: int = 0,
        signal_strength: int = 0,
        service_name: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Update connection status.
        
        Args:
            connected: Connection state
            latency_ms: Connection latency in milliseconds
            signal_strength: Signal strength (0-4)
            service_name: Name of connected service
            error: Error message if any
        """
        with self._lock:
            self.connected = connected
            self.latency_ms = latency_ms
            self.signal_strength = max(0, min(4, signal_strength))
            if service_name:
                self.service_name = service_name
            self.error_message = error
    
    def get_status_text(self) -> str:
        """Get status text.
        
        Returns:
            Formatted status text
        """
        with self._lock:
            if self.error_message:
                return f"❌ {self.error_message}"
            
            if not self.connected:
                return "🔴 Disconnected"
            
            # Signal strength bars
            bars = "▁▂▃▄"
            signal = "".join(bars[:self.signal_strength])
            
            status = f"🟢 {self.service_name}"
            
            if self.latency_ms > 0:
                status += f" ({self.latency_ms}ms)"
            
            if self.signal_strength > 0:
                status += f" {signal}"
            
            return status
    
    def get_status_icon(self) -> str:
        """Get status icon.
        
        Returns:
            Status icon
        """
        with self._lock:
            if self.error_message:
                return "❌"
            elif not self.connected:
                return "🔴"
            elif self.latency_ms > 200:
                return "🟡"
            else:
                return "🟢"


class ProgressIndicator:
    """Progress indicator for long operations."""
    
    def __init__(self, total: Optional[int] = None):
        """Initialize progress indicator.
        
        Args:
            total: Total steps (None for indeterminate)
        """
        self.total = total
        self.current = 0
        self.message = ""
        self.start_time = time.time()
        self._lock = threading.Lock()
        self._spinner_frame = 0
    
    def update(self, current: Optional[int] = None, message: str = ""):
        """Update progress.
        
        Args:
            current: Current step
            message: Progress message
        """
        with self._lock:
            if current is not None:
                self.current = current
            else:
                self.current += 1
            
            if message:
                self.message = message
    
    def get_progress_bar(self, width: int = 30) -> str:
        """Get progress bar.
        
        Args:
            width: Bar width in characters
            
        Returns:
            Progress bar string
        """
        with self._lock:
            if self.total is None:
                # Indeterminate progress
                spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                self._spinner_frame = (self._spinner_frame + 1) % len(spinner)
                return f"{spinner[self._spinner_frame]} {self.message}"
            
            # Determinate progress
            progress = min(1.0, self.current / self.total)
            filled = int(progress * width)
            
            bar = "█" * filled + "░" * (width - filled)
            percentage = int(progress * 100)
            
            elapsed = time.time() - self.start_time
            
            if progress > 0 and progress < 1:
                eta = elapsed * (1 - progress) / progress
                eta_str = f" ETA: {eta:.1f}s"
            else:
                eta_str = ""
            
            return f"[{bar}] {percentage}% {self.message}{eta_str}"
    
    def is_complete(self) -> bool:
        """Check if progress is complete.
        
        Returns:
            True if complete
        """
        with self._lock:
            return self.total is not None and self.current >= self.total


class NotificationManager:
    """Manages visual notifications."""
    
    def __init__(self, max_notifications: int = 10):
        """Initialize notification manager.
        
        Args:
            max_notifications: Maximum notifications to keep
        """
        self.notifications: deque = deque(maxlen=max_notifications)
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[str, str], None]] = []
    
    def add_notification(
        self,
        message: str,
        level: str = "info",
        duration: float = 3.0
    ):
        """Add notification.
        
        Args:
            message: Notification message
            level: Notification level (info, warning, error, success)
            duration: Display duration in seconds
        """
        notification = {
            "message": message,
            "level": level,
            "timestamp": time.time(),
            "duration": duration
        }
        
        with self._lock:
            self.notifications.append(notification)
            
            # Trigger callbacks
            for callback in self._callbacks:
                try:
                    callback(message, level)
                except Exception as e:
                    logger.error(f"Notification callback error: {e}")
    
    def register_callback(self, callback: Callable[[str, str], None]):
        """Register notification callback.
        
        Args:
            callback: Function to call on new notifications
        """
        with self._lock:
            self._callbacks.append(callback)
    
    def get_active_notifications(self) -> List[Dict[str, Any]]:
        """Get active notifications.
        
        Returns:
            List of active notifications
        """
        current_time = time.time()
        
        with self._lock:
            active = []
            for notif in self.notifications:
                if current_time - notif["timestamp"] < notif["duration"]:
                    active.append(notif.copy())
            
            return active
    
    def format_notification(self, notification: Dict[str, Any]) -> str:
        """Format notification for display.
        
        Args:
            notification: Notification dict
            
        Returns:
            Formatted notification string
        """
        icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }
        
        icon = icons.get(notification["level"], "•")
        return f"{icon} {notification['message']}"


class VisualFeedbackSystem:
    """Integrated visual feedback system."""
    
    def __init__(self):
        """Initialize visual feedback system."""
        self.voice_indicator = VoiceActivityIndicator()
        self.connection_display = ConnectionStatusDisplay()
        self.progress_indicator: Optional[ProgressIndicator] = None
        self.notification_manager = NotificationManager()
        
        # State tracking
        self._is_active = False
        self._lock = threading.Lock()
        
        # Update callbacks
        self._update_callbacks: List[Callable[[Dict[str, Any]], None]] = []
    
    def start(self):
        """Start visual feedback system."""
        with self._lock:
            if self._is_active:
                return
            
            self._is_active = True
            self.voice_indicator.start_animation()
            logger.info("Visual feedback system started")
    
    def stop(self):
        """Stop visual feedback system."""
        with self._lock:
            if not self._is_active:
                return
            
            self._is_active = False
            self.voice_indicator.stop_animation()
            logger.info("Visual feedback system stopped")
    
    def register_update_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register update callback.
        
        Args:
            callback: Function to call on updates
        """
        with self._lock:
            self._update_callbacks.append(callback)
    
    def update_voice_state(self, state: IndicatorState, audio_level: float = 0.0):
        """Update voice indicator state.
        
        Args:
            state: New voice state
            audio_level: Current audio level
        """
        self.voice_indicator.set_state(state)
        self.voice_indicator.set_audio_level(audio_level)
        self._trigger_update()
    
    def update_connection(
        self,
        connected: bool,
        latency_ms: int = 0,
        service_name: Optional[str] = None
    ):
        """Update connection status.
        
        Args:
            connected: Connection state
            latency_ms: Connection latency
            service_name: Service name
        """
        # Calculate signal strength from latency
        if latency_ms <= 50:
            signal = 4
        elif latency_ms <= 100:
            signal = 3
        elif latency_ms <= 200:
            signal = 2
        else:
            signal = 1
        
        self.connection_display.update_status(
            connected=connected,
            latency_ms=latency_ms,
            signal_strength=signal,
            service_name=service_name
        )
        self._trigger_update()
    
    def start_progress(self, total: Optional[int] = None, message: str = ""):
        """Start progress indicator.
        
        Args:
            total: Total steps (None for indeterminate)
            message: Initial message
        """
        self.progress_indicator = ProgressIndicator(total)
        if message:
            self.progress_indicator.message = message
        self._trigger_update()
    
    def update_progress(self, current: Optional[int] = None, message: str = ""):
        """Update progress indicator.
        
        Args:
            current: Current step
            message: Progress message
        """
        if self.progress_indicator:
            self.progress_indicator.update(current, message)
            
            if self.progress_indicator.is_complete():
                self.notification_manager.add_notification(
                    "Operation completed",
                    "success"
                )
                self.progress_indicator = None
            
            self._trigger_update()
    
    def show_notification(self, message: str, level: str = "info"):
        """Show notification.
        
        Args:
            message: Notification message
            level: Notification level
        """
        self.notification_manager.add_notification(message, level)
        self._trigger_update()
    
    def get_display_state(self) -> Dict[str, Any]:
        """Get current display state.
        
        Returns:
            Complete display state
        """
        state = {
            "voice": {
                "state": self.voice_indicator.state.name,
                "text": self.voice_indicator.get_display_text(),
                "animation": self.voice_indicator.get_animation_frame(),
                "level_meter": self.voice_indicator.get_level_meter(),
                "audio_level": self.voice_indicator.audio_level
            },
            "connection": {
                "status": self.connection_display.get_status_text(),
                "icon": self.connection_display.get_status_icon(),
                "connected": self.connection_display.connected,
                "latency": self.connection_display.latency_ms
            },
            "notifications": [
                self.notification_manager.format_notification(n)
                for n in self.notification_manager.get_active_notifications()
            ]
        }
        
        if self.progress_indicator:
            state["progress"] = {
                "bar": self.progress_indicator.get_progress_bar(),
                "current": self.progress_indicator.current,
                "total": self.progress_indicator.total,
                "message": self.progress_indicator.message
            }
        
        return state
    
    def format_display(self) -> str:
        """Format complete display as text.
        
        Returns:
            Formatted display string
        """
        state = self.get_display_state()
        lines = []
        
        # Connection status
        lines.append(f"{state['connection']['icon']} {state['connection']['status']}")
        
        # Voice activity
        voice = state["voice"]
        line = f"{voice['animation']} {voice['text']}"
        if voice["level_meter"]:
            line += f" {voice['level_meter']}"
        lines.append(line)
        
        # Progress
        if "progress" in state:
            lines.append(state["progress"]["bar"])
        
        # Notifications
        for notif in state["notifications"]:
            lines.append(notif)
        
        return "\n".join(lines)
    
    def _trigger_update(self):
        """Trigger update callbacks."""
        state = self.get_display_state()
        
        for callback in self._update_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"Update callback error: {e}")


# Export main components
__all__ = [
    "IndicatorState",
    "AnimationStyle",
    "IndicatorConfig",
    "VoiceActivityIndicator",
    "ConnectionStatusDisplay",
    "ProgressIndicator",
    "NotificationManager",
    "VisualFeedbackSystem"
]