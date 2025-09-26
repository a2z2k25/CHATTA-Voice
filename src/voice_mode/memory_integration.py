#!/usr/bin/env python3
"""Integration of memory optimization with CHATTA voice mode."""

import asyncio
import numpy as np
from typing import Dict, Any, Optional, List
import hashlib
import logging

from .memory_optimizer import (
    MemoryProfile,
    MemoryOptimizer,
    BufferManager,
    CircularBuffer,
    WeakCache,
    MemoryPool,
    MemoryMonitor,
    get_memory_optimizer
)

logger = logging.getLogger(__name__)


class AudioMemoryManager:
    """Manages audio memory for voice mode."""
    
    def __init__(self, profile: MemoryProfile = MemoryProfile.BALANCED):
        self.optimizer = get_memory_optimizer(profile)
        self.profile = profile
        
        # Create specialized pools
        self.audio_chunk_pool = self.optimizer.create_pool(
            "audio_chunks",
            factory=lambda: np.zeros(4096, dtype=np.int16),
            max_size=20 if profile == MemoryProfile.MINIMAL else 100
        )
        
        self.text_buffer_pool = self.optimizer.create_pool(
            "text_buffers",
            factory=lambda: [],
            max_size=10 if profile == MemoryProfile.MINIMAL else 50
        )
        
        # Create caches
        self.transcript_cache = self.optimizer.create_cache(
            "transcripts",
            max_strong_refs=5 if profile == MemoryProfile.MINIMAL else 20
        )
        
        self.audio_cache = self.optimizer.create_cache(
            "audio_data",
            max_strong_refs=3 if profile == MemoryProfile.MINIMAL else 10
        )
        
        # Circular buffers for streaming
        buffer_size = 16384 if profile == MemoryProfile.MINIMAL else 65536
        self.input_buffer = CircularBuffer(buffer_size)
        self.output_buffer = CircularBuffer(buffer_size)
    
    def process_audio_chunk(self, audio_data: bytes) -> np.ndarray:
        """Process audio chunk with memory optimization."""
        # Get buffer from pool
        chunk = self.audio_chunk_pool.acquire()
        
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Copy to pooled buffer
            copy_size = min(len(audio_array), len(chunk))
            chunk[:copy_size] = audio_array[:copy_size]
            
            # Process (simplified)
            processed = chunk[:copy_size].copy()
            
            return processed
            
        finally:
            # Return buffer to pool
            self.audio_chunk_pool.release(chunk)
    
    def cache_transcript(self, audio_hash: str, text: str):
        """Cache transcript with weak reference."""
        self.transcript_cache.put(audio_hash, text)
    
    def get_cached_transcript(self, audio_hash: str) -> Optional[str]:
        """Get cached transcript."""
        return self.transcript_cache.get(audio_hash)
    
    def cache_audio(self, text_hash: str, audio_data: bytes):
        """Cache audio data with weak reference."""
        self.audio_cache.put(text_hash, audio_data)
    
    def get_cached_audio(self, text_hash: str) -> Optional[bytes]:
        """Get cached audio data."""
        return self.audio_cache.get(text_hash)
    
    async def stream_audio_input(self, audio_stream):
        """Stream audio input with memory-efficient buffering."""
        async for chunk in audio_stream:
            # Convert to numpy
            audio_array = np.frombuffer(chunk, dtype=np.int16)
            
            # Write to circular buffer
            written = self.input_buffer.write(audio_array)
            
            if written < len(audio_array):
                logger.warning(f"Input buffer overflow: {len(audio_array) - written} samples dropped")
            
            # Check memory pressure
            if self.profile == MemoryProfile.MINIMAL:
                stats = self.optimizer.monitor.get_current_stats()
                if stats.percent > 70:
                    # Emergency cleanup
                    self.optimizer.optimize_memory()
    
    async def stream_audio_output(self) -> bytes:
        """Stream audio output from buffer."""
        # Read from circular buffer
        chunk_size = 2048 if self.profile == MemoryProfile.MINIMAL else 4096
        audio_data = self.output_buffer.read(chunk_size)
        
        if len(audio_data) > 0:
            return audio_data.tobytes()
        return b""
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        return {
            "profile": self.profile.value,
            "pools": {
                "audio_chunks": self.audio_chunk_pool.stats,
                "text_buffers": self.text_buffer_pool.stats
            },
            "caches": {
                "transcripts": self.transcript_cache.stats,
                "audio_data": self.audio_cache.stats
            },
            "buffers": {
                "input": self.input_buffer.stats,
                "output": self.output_buffer.stats
            },
            "system": self.optimizer.monitor.get_current_stats().to_dict()
        }
    
    def cleanup(self):
        """Clean up resources."""
        self.input_buffer.clear()
        self.output_buffer.clear()
        self.optimizer.cleanup()


class VoiceMemoryOptimizer:
    """Voice-specific memory optimizations."""
    
    def __init__(self, profile: MemoryProfile = MemoryProfile.BALANCED):
        self.profile = profile
        self.audio_manager = AudioMemoryManager(profile)
        self.optimizer = get_memory_optimizer(profile)
        
        # Track active sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_pool = self.optimizer.create_pool(
            "sessions",
            factory=lambda: {"audio": [], "text": [], "timestamp": 0},
            max_size=5 if profile == MemoryProfile.MINIMAL else 20
        )
    
    def create_session(self, session_id: str) -> Dict[str, Any]:
        """Create a new session with pooled resources."""
        session = self.session_pool.acquire()
        session["audio"] = []
        session["text"] = []
        session["timestamp"] = asyncio.get_event_loop().time()
        self.sessions[session_id] = session
        return session
    
    def close_session(self, session_id: str):
        """Close session and return resources to pool."""
        if session_id in self.sessions:
            session = self.sessions.pop(session_id)
            # Clear session data
            session["audio"].clear()
            session["text"].clear()
            # Return to pool
            self.session_pool.release(session)
    
    def optimize_for_voice_mode(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize configuration for voice mode based on memory profile."""
        optimized = config.copy()
        
        if self.profile == MemoryProfile.MINIMAL:
            # Minimize memory usage
            optimized.update({
                "chunk_size": 2048,
                "buffer_size": 8192,
                "max_audio_length": 30,  # seconds
                "cache_enabled": False,
                "streaming": True,
                "compression": "opus",  # Better compression
                "sample_rate": 16000,  # Lower sample rate
                "channels": 1  # Mono
            })
        elif self.profile == MemoryProfile.BALANCED:
            # Balance memory and performance
            optimized.update({
                "chunk_size": 4096,
                "buffer_size": 16384,
                "max_audio_length": 60,
                "cache_enabled": True,
                "cache_size": 20,
                "streaming": True,
                "compression": "aac",
                "sample_rate": 24000,
                "channels": 1
            })
        else:  # PERFORMANCE
            # Prioritize performance
            optimized.update({
                "chunk_size": 8192,
                "buffer_size": 65536,
                "max_audio_length": 120,
                "cache_enabled": True,
                "cache_size": 100,
                "streaming": False,  # Buffer everything
                "compression": None,  # No compression
                "sample_rate": 48000,
                "channels": 2
            })
        
        return optimized
    
    async def process_voice_input(self, audio_data: bytes) -> str:
        """Process voice input with memory optimization."""
        # Hash audio for caching
        audio_hash = hashlib.md5(audio_data).hexdigest()
        
        # Check cache
        cached = self.audio_manager.get_cached_transcript(audio_hash)
        if cached:
            return cached
        
        # Process with memory-efficient chunking
        processed = self.audio_manager.process_audio_chunk(audio_data)
        
        # Simulate STT (would be actual STT call)
        transcript = f"Processed {len(processed)} samples"
        
        # Cache result
        self.audio_manager.cache_transcript(audio_hash, transcript)
        
        # Monitor memory
        if self.profile == MemoryProfile.MINIMAL:
            self._check_memory_pressure()
        
        return transcript
    
    async def generate_voice_output(self, text: str) -> bytes:
        """Generate voice output with memory optimization."""
        # Hash text for caching
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Check cache
        cached = self.audio_manager.get_cached_audio(text_hash)
        if cached:
            return cached
        
        # Generate audio (simplified)
        # In reality, this would call TTS
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
        
        # Cache result
        self.audio_manager.cache_audio(text_hash, audio_data)
        
        return audio_data
    
    def _check_memory_pressure(self):
        """Check and respond to memory pressure."""
        stats = self.optimizer.monitor.get_current_stats()
        
        if stats.percent > 80:
            # Critical - aggressive cleanup
            logger.warning(f"Critical memory pressure: {stats.percent:.1f}%")
            self.optimizer.optimize_memory()
            
            # Clear caches
            self.audio_manager.transcript_cache.clear()
            self.audio_manager.audio_cache.clear()
            
            # Close old sessions
            if self.sessions:
                oldest = min(self.sessions.items(), 
                           key=lambda x: x[1].get("timestamp", 0))
                self.close_session(oldest[0])
        
        elif stats.percent > 60:
            # Warning - moderate cleanup
            logger.info(f"Memory pressure: {stats.percent:.1f}%")
            self.optimizer.optimize_memory()
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get memory optimization report."""
        return {
            "profile": self.profile.value,
            "active_sessions": len(self.sessions),
            "memory_stats": self.audio_manager.get_memory_stats(),
            "suggestions": self.optimizer.get_optimization_suggestions(),
            "trend": self.optimizer.monitor.get_trend()
        }


class StreamingMemoryBuffer:
    """Memory-efficient streaming buffer for real-time audio."""
    
    def __init__(self, max_duration_seconds: int = 30, sample_rate: int = 16000):
        self.max_samples = max_duration_seconds * sample_rate
        self.sample_rate = sample_rate
        self.chunks: List[np.ndarray] = []
        self.total_samples = 0
        self._lock = asyncio.Lock()
    
    async def add_chunk(self, audio_chunk: np.ndarray):
        """Add audio chunk with automatic trimming."""
        async with self._lock:
            self.chunks.append(audio_chunk)
            self.total_samples += len(audio_chunk)
            
            # Trim old chunks if exceeding max duration
            while self.total_samples > self.max_samples and self.chunks:
                removed = self.chunks.pop(0)
                self.total_samples -= len(removed)
    
    async def get_audio(self) -> np.ndarray:
        """Get concatenated audio."""
        async with self._lock:
            if not self.chunks:
                return np.array([], dtype=np.int16)
            return np.concatenate(self.chunks)
    
    async def clear(self):
        """Clear buffer."""
        async with self._lock:
            self.chunks.clear()
            self.total_samples = 0
    
    @property
    async def duration_seconds(self) -> float:
        """Get current buffer duration in seconds."""
        async with self._lock:
            return self.total_samples / self.sample_rate
    
    @property
    async def memory_usage_mb(self) -> float:
        """Get memory usage in MB."""
        async with self._lock:
            # Each sample is 2 bytes (int16)
            return (self.total_samples * 2) / (1024 * 1024)


def integrate_memory_optimization(voice_mode_instance, 
                                 profile: MemoryProfile = MemoryProfile.BALANCED):
    """Integrate memory optimization with voice mode instance."""
    
    # Create optimizer
    memory_optimizer = VoiceMemoryOptimizer(profile)
    
    # Store original methods
    original_process_audio = voice_mode_instance.process_audio
    original_generate_audio = voice_mode_instance.generate_audio
    
    # Wrap methods with memory optimization
    async def optimized_process_audio(audio_data: bytes) -> str:
        """Process audio with memory optimization."""
        result = await memory_optimizer.process_voice_input(audio_data)
        
        # Call original if needed
        if hasattr(voice_mode_instance, '_use_original') and voice_mode_instance._use_original:
            result = await original_process_audio(audio_data)
        
        return result
    
    async def optimized_generate_audio(text: str) -> bytes:
        """Generate audio with memory optimization."""
        result = await memory_optimizer.generate_voice_output(text)
        
        # Call original if needed
        if hasattr(voice_mode_instance, '_use_original') and voice_mode_instance._use_original:
            result = await original_generate_audio(text)
        
        return result
    
    # Replace methods
    voice_mode_instance.process_audio = optimized_process_audio
    voice_mode_instance.generate_audio = optimized_generate_audio
    
    # Add memory management attributes
    voice_mode_instance.memory_optimizer = memory_optimizer
    voice_mode_instance.audio_memory = memory_optimizer.audio_manager
    
    # Add utility methods
    voice_mode_instance.get_memory_stats = memory_optimizer.audio_manager.get_memory_stats
    voice_mode_instance.get_optimization_report = memory_optimizer.get_optimization_report
    voice_mode_instance.cleanup_memory = memory_optimizer.optimizer.cleanup
    
    return voice_mode_instance