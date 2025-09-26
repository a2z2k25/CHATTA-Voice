#!/usr/bin/env python3
"""Real-time audio processing pipeline for voice mode.

This module provides a comprehensive audio processing pipeline with:
- Real-time audio streaming
- Multi-stage processing (filters, effects, enhancement)
- Buffer management and flow control
- Parallel processing support
"""

import asyncio
import logging
import time
import numpy as np
from typing import Optional, List, Dict, Any, Callable, Union, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor
import queue

logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """Audio processing stages."""
    INPUT = "input"
    PRE_PROCESS = "pre_process"
    NOISE_REDUCTION = "noise_reduction"
    GAIN_CONTROL = "gain_control"
    ENHANCEMENT = "enhancement"
    POST_PROCESS = "post_process"
    OUTPUT = "output"


class AudioFormat(Enum):
    """Supported audio formats."""
    PCM_S16 = "pcm_s16"  # 16-bit signed PCM
    PCM_F32 = "pcm_f32"  # 32-bit float PCM
    MP3 = "mp3"
    WAV = "wav"
    OPUS = "opus"


@dataclass
class AudioChunk:
    """Single audio chunk in the pipeline."""
    data: bytes
    timestamp: float = field(default_factory=time.time)
    sample_rate: int = 16000
    channels: int = 1
    format: AudioFormat = AudioFormat.PCM_S16
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Calculate chunk duration in seconds."""
        if self.format == AudioFormat.PCM_S16:
            bytes_per_sample = 2
        elif self.format == AudioFormat.PCM_F32:
            bytes_per_sample = 4
        else:
            return 0.0  # Unknown for compressed formats
        
        num_samples = len(self.data) / (bytes_per_sample * self.channels)
        return num_samples / self.sample_rate
    
    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array."""
        if self.format == AudioFormat.PCM_S16:
            arr = np.frombuffer(self.data, dtype=np.int16)
        elif self.format == AudioFormat.PCM_F32:
            arr = np.frombuffer(self.data, dtype=np.float32)
        else:
            raise ValueError(f"Cannot convert {self.format} to numpy")
        
        if self.channels > 1:
            arr = arr.reshape(-1, self.channels)
        
        return arr
    
    @classmethod
    def from_numpy(
        cls,
        arr: np.ndarray,
        sample_rate: int = 16000,
        format: AudioFormat = AudioFormat.PCM_S16
    ) -> "AudioChunk":
        """Create from numpy array."""
        if format == AudioFormat.PCM_S16:
            if arr.dtype != np.int16:
                arr = (arr * 32767).astype(np.int16)
            data = arr.tobytes()
        elif format == AudioFormat.PCM_F32:
            if arr.dtype != np.float32:
                arr = arr.astype(np.float32)
            data = arr.tobytes()
        else:
            raise ValueError(f"Cannot create {format} from numpy")
        
        channels = arr.shape[1] if arr.ndim > 1 else 1
        
        return cls(
            data=data,
            sample_rate=sample_rate,
            channels=channels,
            format=format
        )


class AudioProcessor:
    """Base class for audio processors."""
    
    def __init__(self, name: str = "processor"):
        self.name = name
        self.enabled = True
        self.stats = {
            "chunks_processed": 0,
            "total_duration": 0.0,
            "processing_time": 0.0
        }
    
    async def process(self, chunk: AudioChunk) -> AudioChunk:
        """Process audio chunk."""
        if not self.enabled:
            return chunk
        
        start_time = time.time()
        result = await self._process_impl(chunk)
        
        # Update stats
        self.stats["chunks_processed"] += 1
        self.stats["total_duration"] += chunk.duration
        self.stats["processing_time"] += time.time() - start_time
        
        return result
    
    async def _process_impl(self, chunk: AudioChunk) -> AudioChunk:
        """Actual processing implementation."""
        return chunk  # Default: passthrough
    
    def reset(self):
        """Reset processor state."""
        pass


class NoiseReductionProcessor(AudioProcessor):
    """Noise reduction processor."""
    
    def __init__(self, threshold: float = 0.1):
        super().__init__("noise_reduction")
        self.threshold = threshold
        self.noise_profile = None
        self.calibration_chunks = deque(maxlen=10)
    
    async def _process_impl(self, chunk: AudioChunk) -> AudioChunk:
        """Apply noise reduction."""
        # Convert to numpy for processing
        audio_data = chunk.to_numpy()
        
        # Simple spectral subtraction
        if self.noise_profile is None:
            # Calibration mode: collect noise profile
            self.calibration_chunks.append(audio_data)
            if len(self.calibration_chunks) == 10:
                # Estimate noise from quiet sections
                all_data = np.concatenate(list(self.calibration_chunks))
                self.noise_profile = np.percentile(np.abs(all_data), 10)
        else:
            # Apply noise gate
            mask = np.abs(audio_data) > self.noise_profile * (1 + self.threshold)
            audio_data = audio_data * mask
        
        return AudioChunk.from_numpy(
            audio_data,
            chunk.sample_rate,
            chunk.format
        )


class GainControlProcessor(AudioProcessor):
    """Automatic gain control processor."""
    
    def __init__(self, target_level: float = 0.7, attack: float = 0.01, release: float = 0.1):
        super().__init__("gain_control")
        self.target_level = target_level
        self.attack = attack
        self.release = release
        self.current_gain = 1.0
    
    async def _process_impl(self, chunk: AudioChunk) -> AudioChunk:
        """Apply automatic gain control."""
        audio_data = chunk.to_numpy().astype(np.float32)
        
        # Normalize to [-1, 1]
        if chunk.format == AudioFormat.PCM_S16:
            audio_data = audio_data / 32768.0
        
        # Calculate RMS
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        if rms > 0:
            # Calculate target gain
            target_gain = self.target_level / rms
            target_gain = np.clip(target_gain, 0.1, 10.0)
            
            # Smooth gain changes
            if target_gain > self.current_gain:
                self.current_gain += (target_gain - self.current_gain) * self.attack
            else:
                self.current_gain += (target_gain - self.current_gain) * self.release
        
        # Apply gain
        audio_data = audio_data * self.current_gain
        
        # Clip to prevent overflow
        audio_data = np.clip(audio_data, -1.0, 1.0)
        
        # Convert back to original format
        if chunk.format == AudioFormat.PCM_S16:
            audio_data = (audio_data * 32767).astype(np.int16)
        
        return AudioChunk.from_numpy(
            audio_data,
            chunk.sample_rate,
            chunk.format
        )


class AudioEnhancementProcessor(AudioProcessor):
    """Audio enhancement processor."""
    
    def __init__(self, bass_boost: float = 0.0, treble_boost: float = 0.0):
        super().__init__("enhancement")
        self.bass_boost = bass_boost  # -1.0 to 1.0
        self.treble_boost = treble_boost  # -1.0 to 1.0
        self.prev_sample = 0
    
    async def _process_impl(self, chunk: AudioChunk) -> AudioChunk:
        """Apply audio enhancement."""
        audio_data = chunk.to_numpy().astype(np.float32)
        
        # Normalize
        if chunk.format == AudioFormat.PCM_S16:
            audio_data = audio_data / 32768.0
        
        # Simple high-pass filter for treble
        if self.treble_boost != 0:
            filtered = np.zeros_like(audio_data)
            for i in range(len(audio_data)):
                filtered[i] = audio_data[i] - self.prev_sample
                self.prev_sample = audio_data[i] if audio_data.ndim == 1 else audio_data[i, 0]
            
            audio_data = audio_data + filtered * self.treble_boost
        
        # Simple low-pass for bass (moving average)
        if self.bass_boost != 0:
            window_size = int(chunk.sample_rate * 0.002)  # 2ms window
            if len(audio_data) > window_size:
                bass = np.convolve(audio_data, np.ones(window_size)/window_size, mode='same')
                audio_data = audio_data + bass * self.bass_boost
        
        # Normalize and convert back
        audio_data = np.clip(audio_data, -1.0, 1.0)
        
        if chunk.format == AudioFormat.PCM_S16:
            audio_data = (audio_data * 32767).astype(np.int16)
        
        return AudioChunk.from_numpy(
            audio_data,
            chunk.sample_rate,
            chunk.format
        )


class AudioBuffer:
    """Thread-safe audio buffer."""
    
    def __init__(self, max_size: int = 100):
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.not_empty = threading.Condition(self.lock)
        self.not_full = threading.Condition(self.lock)
        self.closed = False
    
    def put(self, chunk: AudioChunk, timeout: Optional[float] = None) -> bool:
        """Add chunk to buffer."""
        with self.not_full:
            while len(self.buffer) >= self.buffer.maxlen and not self.closed:
                if not self.not_full.wait(timeout):
                    return False
            
            if self.closed:
                return False
            
            self.buffer.append(chunk)
            self.not_empty.notify()
            return True
    
    def get(self, timeout: Optional[float] = None) -> Optional[AudioChunk]:
        """Get chunk from buffer."""
        with self.not_empty:
            while len(self.buffer) == 0 and not self.closed:
                if not self.not_empty.wait(timeout):
                    return None
            
            if len(self.buffer) == 0:
                return None
            
            chunk = self.buffer.popleft()
            self.not_full.notify()
            return chunk
    
    def close(self):
        """Close buffer."""
        with self.lock:
            self.closed = True
            self.not_empty.notify_all()
            self.not_full.notify_all()
    
    def __len__(self) -> int:
        with self.lock:
            return len(self.buffer)


class AudioPipeline:
    """Real-time audio processing pipeline."""
    
    def __init__(
        self,
        buffer_size: int = 100,
        num_workers: int = 2
    ):
        self.processors: Dict[ProcessingStage, List[AudioProcessor]] = {
            stage: [] for stage in ProcessingStage
        }
        self.buffers: Dict[str, AudioBuffer] = {}
        self.buffer_size = buffer_size
        self.num_workers = num_workers
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self.stats = {
            "total_chunks": 0,
            "total_duration": 0.0,
            "dropped_chunks": 0,
            "processing_time": 0.0
        }
    
    def add_processor(
        self,
        processor: AudioProcessor,
        stage: ProcessingStage = ProcessingStage.PRE_PROCESS
    ):
        """Add processor to pipeline."""
        self.processors[stage].append(processor)
        logger.info(f"Added {processor.name} to {stage.value} stage")
    
    def remove_processor(self, processor: AudioProcessor):
        """Remove processor from pipeline."""
        for stage_processors in self.processors.values():
            if processor in stage_processors:
                stage_processors.remove(processor)
                logger.info(f"Removed {processor.name}")
                break
    
    async def process_chunk(self, chunk: AudioChunk) -> AudioChunk:
        """Process single chunk through pipeline."""
        start_time = time.time()
        
        # Process through each stage
        for stage in ProcessingStage:
            for processor in self.processors[stage]:
                if processor.enabled:
                    chunk = await processor.process(chunk)
        
        # Update stats
        self.stats["total_chunks"] += 1
        self.stats["total_duration"] += chunk.duration
        self.stats["processing_time"] += time.time() - start_time
        
        return chunk
    
    async def process_stream(
        self,
        input_stream: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[AudioChunk]:
        """Process audio stream."""
        self.running = True
        
        try:
            async for chunk in input_stream:
                if not self.running:
                    break
                
                # Process chunk
                processed = await self.process_chunk(chunk)
                
                yield processed
                
        finally:
            self.running = False
    
    def start_parallel_processing(
        self,
        input_buffer: AudioBuffer,
        output_buffer: AudioBuffer
    ):
        """Start parallel processing workers."""
        self.running = True
        
        async def worker():
            """Processing worker."""
            while self.running:
                # Get chunk from input
                chunk = input_buffer.get(timeout=0.1)
                if chunk is None:
                    continue
                
                # Process
                try:
                    processed = await self.process_chunk(chunk)
                    
                    # Put to output
                    if not output_buffer.put(processed, timeout=0.1):
                        self.stats["dropped_chunks"] += 1
                        logger.warning("Output buffer full, dropping chunk")
                        
                except Exception as e:
                    logger.error(f"Processing error: {e}")
        
        # Start workers
        for _ in range(self.num_workers):
            task = asyncio.create_task(worker())
            self.tasks.append(task)
    
    async def stop_parallel_processing(self):
        """Stop parallel processing."""
        self.running = False
        
        # Wait for workers to finish
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        stats = self.stats.copy()
        
        # Add processor stats
        stats["processors"] = {}
        for stage, processors in self.processors.items():
            for processor in processors:
                stats["processors"][processor.name] = processor.stats.copy()
        
        # Calculate latency
        if stats["total_chunks"] > 0:
            stats["avg_latency"] = stats["processing_time"] / stats["total_chunks"]
        else:
            stats["avg_latency"] = 0
        
        return stats
    
    def reset_stats(self):
        """Reset all statistics."""
        self.stats = {
            "total_chunks": 0,
            "total_duration": 0.0,
            "dropped_chunks": 0,
            "processing_time": 0.0
        }
        
        for processors in self.processors.values():
            for processor in processors:
                processor.stats = {
                    "chunks_processed": 0,
                    "total_duration": 0.0,
                    "processing_time": 0.0
                }


class AudioPipelineManager:
    """Manages multiple audio pipelines."""
    
    def __init__(self):
        self.pipelines: Dict[str, AudioPipeline] = {}
        self.default_pipeline: Optional[str] = None
    
    def create_pipeline(
        self,
        name: str,
        buffer_size: int = 100,
        num_workers: int = 2
    ) -> AudioPipeline:
        """Create new pipeline."""
        pipeline = AudioPipeline(buffer_size, num_workers)
        self.pipelines[name] = pipeline
        
        if self.default_pipeline is None:
            self.default_pipeline = name
        
        logger.info(f"Created pipeline: {name}")
        return pipeline
    
    def get_pipeline(self, name: Optional[str] = None) -> Optional[AudioPipeline]:
        """Get pipeline by name."""
        if name is None:
            name = self.default_pipeline
        
        return self.pipelines.get(name)
    
    def delete_pipeline(self, name: str) -> bool:
        """Delete pipeline."""
        if name in self.pipelines:
            del self.pipelines[name]
            
            if self.default_pipeline == name:
                self.default_pipeline = next(iter(self.pipelines.keys()), None)
            
            logger.info(f"Deleted pipeline: {name}")
            return True
        
        return False
    
    def set_default(self, name: str) -> bool:
        """Set default pipeline."""
        if name in self.pipelines:
            self.default_pipeline = name
            logger.info(f"Set default pipeline: {name}")
            return True
        
        return False
    
    def create_standard_pipeline(self, name: str = "standard") -> AudioPipeline:
        """Create standard pipeline with common processors."""
        pipeline = self.create_pipeline(name)
        
        # Add standard processors
        pipeline.add_processor(
            NoiseReductionProcessor(threshold=0.1),
            ProcessingStage.NOISE_REDUCTION
        )
        
        pipeline.add_processor(
            GainControlProcessor(target_level=0.7),
            ProcessingStage.GAIN_CONTROL
        )
        
        pipeline.add_processor(
            AudioEnhancementProcessor(bass_boost=0.1, treble_boost=0.1),
            ProcessingStage.ENHANCEMENT
        )
        
        logger.info(f"Created standard pipeline: {name}")
        return pipeline


# Global pipeline manager
_pipeline_manager = AudioPipelineManager()


def get_pipeline_manager() -> AudioPipelineManager:
    """Get global pipeline manager."""
    return _pipeline_manager