"""
Adaptive streaming buffer for TTS with early playback start.

This module implements intelligent buffering that starts playback
at 35-50% of expected duration for more natural conversation flow.
"""

import asyncio
import time
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StreamingMetrics:
    """Enhanced metrics for adaptive streaming."""
    ttfa: float = 0.0
    early_start_percentage: float = 0.0
    buffer_underruns: int = 0
    playback_rate_adjustments: int = 0
    estimated_duration: float = 0.0
    actual_duration: float = 0.0
    chunks_buffered_before_start: int = 0
    total_chunks: int = 0


class AdaptiveStreamBuffer:
    """Intelligent buffer that starts playback at optimal point."""
    
    def __init__(
        self,
        target_percentage: float = 0.35,
        min_buffer_ms: int = 500,
        sample_rate: int = 24000
    ):
        """Initialize adaptive buffer.
        
        Args:
            target_percentage: Target buffering before playback (0.35 = 35%)
            min_buffer_ms: Minimum buffer in milliseconds
            sample_rate: Audio sample rate
        """
        self.target_percentage = target_percentage
        self.min_buffer_seconds = min_buffer_ms / 1000.0
        self.sample_rate = sample_rate
        
        # Buffer state
        self.chunks: List[bytes] = []
        self.chunk_durations: List[float] = []
        self.total_expected_duration: Optional[float] = None
        self.buffered_duration: float = 0.0
        self.buffered_samples: int = 0
        self.playback_started: bool = False
        self.playback_start_time: Optional[float] = None
        
        # Metrics
        self.metrics = StreamingMetrics()
        self.start_time = time.perf_counter()
        
    def add_chunk(self, chunk: bytes, chunk_duration: Optional[float] = None) -> None:
        """Add audio chunk to buffer.
        
        Args:
            chunk: Audio data bytes
            chunk_duration: Optional duration of chunk in seconds
        """
        self.chunks.append(chunk)
        
        # Calculate duration if not provided
        if chunk_duration is None:
            # Assume PCM 16-bit mono
            samples = len(chunk) // 2  # 2 bytes per sample
            chunk_duration = samples / self.sample_rate
        
        self.chunk_durations.append(chunk_duration)
        self.buffered_duration += chunk_duration
        self.buffered_samples += len(chunk) // 2
        self.metrics.total_chunks += 1
        
        if not self.playback_started:
            self.metrics.chunks_buffered_before_start += 1
    
    def should_start_playback(self) -> bool:
        """Determine if we have enough buffered to start playback.
        
        Returns:
            True if playback should start
        """
        if self.playback_started:
            return False
        
        # Check minimum buffer requirement
        if self.buffered_duration < self.min_buffer_seconds:
            return False
        
        # If we know total duration, use percentage
        if self.total_expected_duration:
            percentage = self.buffered_duration / self.total_expected_duration
            return percentage >= self.target_percentage
        
        # Fallback: start after reasonable buffer
        return self.buffered_duration >= 0.75  # 750ms default
    
    def get_buffered_percentage(self) -> float:
        """Get percentage of total duration buffered.
        
        Returns:
            Percentage buffered (0.0 to 1.0)
        """
        if self.total_expected_duration:
            return min(1.0, self.buffered_duration / self.total_expected_duration)
        return 0.0
    
    def start_playback(self) -> None:
        """Mark playback as started and record metrics."""
        if not self.playback_started:
            self.playback_started = True
            self.playback_start_time = time.perf_counter()
            self.metrics.ttfa = self.playback_start_time - self.start_time
            self.metrics.early_start_percentage = self.get_buffered_percentage()
            
            logger.info(
                f"Starting playback: TTFA={self.metrics.ttfa:.3f}s, "
                f"Buffered={self.metrics.early_start_percentage:.1%}"
            )
    
    def get_next_chunk(self) -> Optional[bytes]:
        """Get next chunk for playback.
        
        Returns:
            Next audio chunk or None if buffer empty
        """
        if self.chunks:
            return self.chunks.pop(0)
        return None
    
    def get_buffer_health(self) -> float:
        """Get buffer health as percentage.
        
        Returns:
            Buffer health (0.0 = empty, 1.0 = healthy)
        """
        # Consider buffer healthy if we have >1 second buffered
        return min(1.0, self.buffered_duration / 1.0)


class PlaybackRateController:
    """Control playback rate to prevent buffer underrun."""
    
    def __init__(self, base_rate: float = 1.0):
        """Initialize playback controller.
        
        Args:
            base_rate: Base playback rate (1.0 = normal speed)
        """
        self.base_rate = base_rate
        self.current_rate = base_rate
        self.rate_history: List[float] = []
        self.adjustment_count = 0
        
        # Rate limits
        self.min_rate = 0.9   # 90% speed minimum
        self.max_rate = 1.1   # 110% speed maximum
        self.smooth_factor = 0.1  # Smoothing for rate changes
    
    def calculate_rate(self, buffer_health: float) -> float:
        """Calculate optimal playback rate based on buffer health.
        
        Args:
            buffer_health: Buffer health (0.0 to 1.0)
            
        Returns:
            Adjusted playback rate
        """
        target_rate = self.base_rate
        
        if buffer_health < 0.2:  # Buffer critically low
            target_rate = self.base_rate * 0.92
        elif buffer_health < 0.4:  # Buffer low
            target_rate = self.base_rate * 0.95
        elif buffer_health > 0.8:  # Buffer very healthy
            target_rate = self.base_rate * 1.02
        elif buffer_health > 0.6:  # Buffer healthy
            target_rate = self.base_rate * 1.0
        
        # Apply rate limits
        target_rate = max(self.min_rate, min(self.max_rate, target_rate))
        
        # Smooth rate changes
        if self.current_rate != self.base_rate:
            # Gradually adjust toward target
            rate_diff = target_rate - self.current_rate
            self.current_rate += rate_diff * self.smooth_factor
            self.adjustment_count += 1
        else:
            self.current_rate = target_rate
        
        self.rate_history.append(self.current_rate)
        return self.current_rate
    
    def get_average_rate(self) -> float:
        """Get average playback rate.
        
        Returns:
            Average rate over history
        """
        if self.rate_history:
            return sum(self.rate_history) / len(self.rate_history)
        return self.base_rate


def estimate_speech_duration(text: str, voice_model: str = "nova") -> float:
    """Estimate TTS duration based on text length and voice model.
    
    Args:
        text: Text to be spoken
        voice_model: TTS voice model name
        
    Returns:
        Estimated duration in seconds
    """
    # Average speaking rates (words per minute)
    WPM_RATES = {
        "nova": 180,      # Natural speed
        "alloy": 170,     # Slightly slower
        "echo": 160,      # More deliberate
        "shimmer": 175,   # Similar to nova
        "onyx": 165,      # Deeper, slower
        "fable": 170,     # British accent
        # Kokoro voices
        "af": 175,        # Default Kokoro voice
        "af_bella": 170,
        "af_nicole": 180,
        "af_sarah": 175,
        "af_sky": 185,    # Faster, energetic
        "am_adam": 165,
        "am_michael": 170,
        "bm_george": 160,
        "bm_lewis": 165,
    }
    
    # Count words (simple split)
    word_count = len(text.split())
    
    # Add adjustment for punctuation and pauses
    pause_count = text.count('.') + text.count('!') + text.count('?')
    pause_count += text.count(',') * 0.5  # Commas are shorter pauses
    
    # Get WPM rate for voice
    wpm = WPM_RATES.get(voice_model, 170)  # Default to 170 WPM
    
    # Calculate base duration
    duration_minutes = word_count / wpm
    duration_seconds = duration_minutes * 60
    
    # Add pause time (approximately 0.3s per major pause, 0.15s per comma)
    pause_time = (pause_count * 0.3)
    
    return duration_seconds + pause_time


def calculate_optimal_chunk_size(
    text_length: int,
    network_latency: Optional[float] = None
) -> int:
    """Calculate optimal chunk size based on text and network conditions.
    
    Args:
        text_length: Length of text in characters
        network_latency: Optional network latency in ms
        
    Returns:
        Optimal chunk size in bytes
    """
    # Base chunk sizes by text length
    if text_length < 100:  # Short response
        base_chunk = 2048
    elif text_length < 500:  # Medium response
        base_chunk = 4096
    elif text_length < 1000:  # Long response
        base_chunk = 6144
    else:  # Very long response
        base_chunk = 8192
    
    # Adjust for network conditions if known
    if network_latency is not None:
        if network_latency < 50:  # Excellent
            return base_chunk
        elif network_latency < 100:  # Good
            return int(base_chunk * 0.75)
        elif network_latency < 200:  # Fair
            return int(base_chunk * 0.5)
        else:  # Poor
            return int(base_chunk * 0.33)
    
    return base_chunk