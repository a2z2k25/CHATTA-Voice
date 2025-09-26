"""
Platform-specific optimizations for voice mode.

This module provides optimizations and adaptations for different
platforms (Claude Desktop vs Claude Code) to ensure optimal
performance and user experience on each.
"""

import os
import sys
import platform
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import shutil
import subprocess

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported platforms."""
    CLAUDE_DESKTOP = auto()  # Native desktop application
    CLAUDE_CODE = auto()     # MCP-based Code environment
    UNKNOWN = auto()         # Unknown platform


class AudioBackend(Enum):
    """Audio backend types."""
    PYAUDIO = auto()         # Direct microphone access
    SOUNDDEVICE = auto()     # Alternative audio library
    MCP_AUDIO = auto()       # MCP-based audio
    LIVEKIT = auto()         # WebRTC-based audio


class DisplayMode(Enum):
    """Display output modes."""
    RICH_TERMINAL = auto()   # Rich terminal UI
    PLAIN_TEXT = auto()      # Plain text output
    STRUCTURED_JSON = auto() # JSON messages
    MCP_PROTOCOL = auto()    # MCP protocol messages


@dataclass
class PlatformCapabilities:
    """Platform-specific capabilities."""
    has_terminal: bool = False
    has_direct_audio: bool = False
    has_rich_ui: bool = False
    has_file_system: bool = True
    has_network: bool = True
    supports_ansi: bool = False
    supports_threads: bool = True
    supports_async: bool = True
    max_message_size: int = 1024 * 1024  # 1MB default
    preferred_audio_backend: AudioBackend = AudioBackend.PYAUDIO
    preferred_display_mode: DisplayMode = DisplayMode.PLAIN_TEXT
    custom_features: Dict[str, Any] = field(default_factory=dict)


class PlatformDetector:
    """Detects and identifies the current platform."""
    
    @staticmethod
    def detect() -> Platform:
        """Detect the current platform.
        
        Returns:
            Detected platform type
        """
        # Check for MCP environment
        if os.getenv("MCP_SERVER_NAME"):
            return Platform.CLAUDE_CODE
        
        # Check for Claude Desktop indicators
        if os.getenv("CLAUDE_DESKTOP") or "claude-desktop" in sys.argv[0].lower():
            return Platform.CLAUDE_DESKTOP
        
        # Check process name
        try:
            import psutil
            process = psutil.Process()
            if "claude" in process.name().lower():
                if "code" in process.name().lower():
                    return Platform.CLAUDE_CODE
                else:
                    return Platform.CLAUDE_DESKTOP
        except:
            pass
        
        # Check for specific file markers
        if Path(".claude-desktop").exists():
            return Platform.CLAUDE_DESKTOP
        if Path(".claude-code").exists() or Path(".mcp.json").exists():
            return Platform.CLAUDE_CODE
        
        # Default based on terminal availability
        if sys.stdin.isatty() and sys.stdout.isatty():
            return Platform.CLAUDE_DESKTOP
        else:
            return Platform.CLAUDE_CODE
    
    @staticmethod
    def get_capabilities(platform: Platform) -> PlatformCapabilities:
        """Get capabilities for a platform.
        
        Args:
            platform: Platform type
            
        Returns:
            Platform capabilities
        """
        if platform == Platform.CLAUDE_DESKTOP:
            return PlatformCapabilities(
                has_terminal=True,
                has_direct_audio=True,
                has_rich_ui=True,
                has_file_system=True,
                has_network=True,
                supports_ansi=True,
                supports_threads=True,
                supports_async=True,
                max_message_size=10 * 1024 * 1024,  # 10MB
                preferred_audio_backend=AudioBackend.PYAUDIO,
                preferred_display_mode=DisplayMode.RICH_TERMINAL,
                custom_features={
                    "hot_reload": True,
                    "system_tray": True,
                    "notifications": True
                }
            )
        
        elif platform == Platform.CLAUDE_CODE:
            return PlatformCapabilities(
                has_terminal=False,
                has_direct_audio=False,  # Through MCP only
                has_rich_ui=False,
                has_file_system=True,
                has_network=True,
                supports_ansi=False,
                supports_threads=True,
                supports_async=True,
                max_message_size=1024 * 1024,  # 1MB
                preferred_audio_backend=AudioBackend.MCP_AUDIO,
                preferred_display_mode=DisplayMode.MCP_PROTOCOL,
                custom_features={
                    "mcp_tools": True,
                    "mcp_resources": True,
                    "mcp_prompts": True
                }
            )
        
        else:
            # Unknown platform - use safe defaults
            return PlatformCapabilities()


class PlatformOptimizer:
    """Applies platform-specific optimizations."""
    
    def __init__(self):
        """Initialize platform optimizer."""
        self.platform = PlatformDetector.detect()
        self.capabilities = PlatformDetector.get_capabilities(self.platform)
        self.optimizations: List[Callable] = []
        
        logger.info(f"Detected platform: {self.platform.name}")
        logger.info(f"Capabilities: {self.capabilities}")
    
    def optimize_audio_pipeline(self) -> Dict[str, Any]:
        """Optimize audio pipeline for platform.
        
        Returns:
            Audio configuration
        """
        config = {
            "backend": self.capabilities.preferred_audio_backend.name,
            "buffer_size": 512,
            "sample_rate": 16000,
            "channels": 1,
            "format": "int16"
        }
        
        if self.platform == Platform.CLAUDE_DESKTOP:
            # Desktop can handle larger buffers and higher quality
            config.update({
                "buffer_size": 1024,
                "sample_rate": 48000,
                "channels": 2,
                "format": "float32",
                "enable_echo_cancellation": True,
                "enable_noise_suppression": True
            })
        
        elif self.platform == Platform.CLAUDE_CODE:
            # MCP needs smaller buffers for lower latency
            config.update({
                "buffer_size": 256,
                "sample_rate": 16000,
                "channels": 1,
                "format": "int16",
                "use_compression": True,
                "optimize_for_streaming": True
            })
        
        return config
    
    def optimize_display_output(self) -> Dict[str, Any]:
        """Optimize display output for platform.
        
        Returns:
            Display configuration
        """
        config = {
            "mode": self.capabilities.preferred_display_mode.name,
            "buffer_lines": 100,
            "update_frequency": 0.1
        }
        
        if self.platform == Platform.CLAUDE_DESKTOP:
            config.update({
                "use_colors": True,
                "use_emoji": True,
                "use_rich_formatting": True,
                "enable_animations": True,
                "buffer_lines": 1000
            })
        
        elif self.platform == Platform.CLAUDE_CODE:
            config.update({
                "use_colors": False,
                "use_emoji": False,
                "use_rich_formatting": False,
                "enable_animations": False,
                "send_as_messages": True,
                "chunk_size": 4096
            })
        
        return config
    
    def optimize_network_settings(self) -> Dict[str, Any]:
        """Optimize network settings for platform.
        
        Returns:
            Network configuration
        """
        config = {
            "timeout": 30,
            "retry_count": 3,
            "connection_pool_size": 10
        }
        
        if self.platform == Platform.CLAUDE_DESKTOP:
            config.update({
                "timeout": 60,
                "retry_count": 5,
                "connection_pool_size": 20,
                "enable_http2": True,
                "enable_connection_reuse": True
            })
        
        elif self.platform == Platform.CLAUDE_CODE:
            config.update({
                "timeout": 15,
                "retry_count": 2,
                "connection_pool_size": 5,
                "enable_compression": True,
                "minimize_requests": True
            })
        
        return config
    
    def optimize_resource_usage(self) -> Dict[str, Any]:
        """Optimize resource usage for platform.
        
        Returns:
            Resource configuration
        """
        config = {
            "max_memory": "512MB",
            "max_threads": 4,
            "cache_size": "100MB"
        }
        
        if self.platform == Platform.CLAUDE_DESKTOP:
            config.update({
                "max_memory": "2GB",
                "max_threads": 8,
                "cache_size": "500MB",
                "enable_preloading": True,
                "enable_background_tasks": True
            })
        
        elif self.platform == Platform.CLAUDE_CODE:
            config.update({
                "max_memory": "256MB",
                "max_threads": 2,
                "cache_size": "50MB",
                "aggressive_gc": True,
                "minimize_allocations": True
            })
        
        return config
    
    def get_audio_backend(self) -> AudioBackend:
        """Get optimal audio backend for platform.
        
        Returns:
            Audio backend type
        """
        if not self.capabilities.has_direct_audio:
            return AudioBackend.MCP_AUDIO
        
        # Check available backends
        try:
            import pyaudio
            return AudioBackend.PYAUDIO
        except ImportError:
            pass
        
        try:
            import sounddevice
            return AudioBackend.SOUNDDEVICE
        except ImportError:
            pass
        
        return AudioBackend.MCP_AUDIO
    
    def get_display_handler(self) -> Callable:
        """Get optimal display handler for platform.
        
        Returns:
            Display handler function
        """
        mode = self.capabilities.preferred_display_mode
        
        if mode == DisplayMode.RICH_TERMINAL:
            from rich.console import Console
            console = Console()
            return console.print
        
        elif mode == DisplayMode.MCP_PROTOCOL:
            def mcp_output(text: str):
                # Send via MCP protocol
                print(f"{{\"type\": \"transcript\", \"content\": {repr(text)}}}")
            return mcp_output
        
        else:
            return print
    
    def apply_optimizations(self):
        """Apply all platform optimizations."""
        # Apply audio optimizations
        audio_config = self.optimize_audio_pipeline()
        os.environ.update({
            f"CHATTA_AUDIO_{k.upper()}": str(v)
            for k, v in audio_config.items()
        })
        
        # Apply display optimizations
        display_config = self.optimize_display_output()
        os.environ.update({
            f"CHATTA_DISPLAY_{k.upper()}": str(v)
            for k, v in display_config.items()
        })
        
        # Apply network optimizations
        network_config = self.optimize_network_settings()
        os.environ.update({
            f"CHATTA_NETWORK_{k.upper()}": str(v)
            for k, v in network_config.items()
        })
        
        # Apply resource optimizations
        resource_config = self.optimize_resource_usage()
        os.environ.update({
            f"CHATTA_RESOURCE_{k.upper()}": str(v)
            for k, v in resource_config.items()
        })
        
        logger.info("Platform optimizations applied")


class AdaptiveOptimizer:
    """Adaptive optimizer that adjusts based on runtime conditions."""
    
    def __init__(self, optimizer: PlatformOptimizer):
        """Initialize adaptive optimizer.
        
        Args:
            optimizer: Base platform optimizer
        """
        self.optimizer = optimizer
        self.metrics: Dict[str, List[float]] = {
            "latency": [],
            "cpu_usage": [],
            "memory_usage": [],
            "error_rate": []
        }
        self.adjustments_made = 0
    
    async def monitor_and_adjust(self):
        """Monitor performance and adjust optimizations."""
        while True:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()
                
                # Analyze and adjust
                if await self._should_adjust(metrics):
                    await self._apply_adjustments(metrics)
                    self.adjustments_made += 1
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Adaptive optimization error: {e}")
                await asyncio.sleep(60)
    
    async def _collect_metrics(self) -> Dict[str, float]:
        """Collect performance metrics.
        
        Returns:
            Current metrics
        """
        import psutil
        
        process = psutil.Process()
        
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "thread_count": process.num_threads(),
            "open_files": len(process.open_files())
        }
    
    async def _should_adjust(self, metrics: Dict[str, float]) -> bool:
        """Check if adjustments are needed.
        
        Args:
            metrics: Current metrics
            
        Returns:
            True if adjustments needed
        """
        # High CPU usage
        if metrics.get("cpu_percent", 0) > 80:
            return True
        
        # High memory usage
        if metrics.get("memory_mb", 0) > 500:
            return True
        
        # Too many threads
        if metrics.get("thread_count", 0) > 20:
            return True
        
        return False
    
    async def _apply_adjustments(self, metrics: Dict[str, float]):
        """Apply performance adjustments.
        
        Args:
            metrics: Current metrics
        """
        logger.info(f"Applying adaptive adjustments (#{self.adjustments_made + 1})")
        
        # Reduce quality if CPU is high
        if metrics.get("cpu_percent", 0) > 80:
            os.environ["CHATTA_AUDIO_SAMPLE_RATE"] = "16000"
            os.environ["CHATTA_AUDIO_CHANNELS"] = "1"
            logger.info("Reduced audio quality for CPU")
        
        # Reduce cache if memory is high
        if metrics.get("memory_mb", 0) > 500:
            os.environ["CHATTA_RESOURCE_CACHE_SIZE"] = "50MB"
            logger.info("Reduced cache size for memory")


# Global optimizer instance
_optimizer: Optional[PlatformOptimizer] = None


def get_optimizer() -> PlatformOptimizer:
    """Get global platform optimizer.
    
    Returns:
        Platform optimizer instance
    """
    global _optimizer
    if _optimizer is None:
        _optimizer = PlatformOptimizer()
        _optimizer.apply_optimizations()
    return _optimizer


# Example usage
def example_usage():
    """Example of using platform optimizations."""
    
    # Get optimizer
    optimizer = get_optimizer()
    
    # Get platform info
    print(f"Platform: {optimizer.platform.name}")
    print(f"Has terminal: {optimizer.capabilities.has_terminal}")
    print(f"Has direct audio: {optimizer.capabilities.has_direct_audio}")
    
    # Get optimized configurations
    audio_config = optimizer.optimize_audio_pipeline()
    print(f"Audio config: {audio_config}")
    
    display_config = optimizer.optimize_display_output()
    print(f"Display config: {display_config}")
    
    # Get appropriate handlers
    audio_backend = optimizer.get_audio_backend()
    print(f"Audio backend: {audio_backend.name}")
    
    display_handler = optimizer.get_display_handler()
    display_handler("Hello from optimized platform!")
    
    # Start adaptive optimization
    if optimizer.platform == Platform.CLAUDE_DESKTOP:
        adaptive = AdaptiveOptimizer(optimizer)
        # asyncio.run(adaptive.monitor_and_adjust())


if __name__ == "__main__":
    example_usage()