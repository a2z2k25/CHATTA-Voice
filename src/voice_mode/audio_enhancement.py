#!/usr/bin/env python3
"""
Advanced audio quality enhancement system for voice interactions.

Implements dynamic range compression, spectral enhancement, equalization,
and perceptual audio improvements to optimize voice clarity and intelligibility
in real-time conversation systems.
"""

import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from collections import deque
import logging

logger = logging.getLogger(__name__)


class EnhancementMode(Enum):
    """Audio enhancement operating modes."""
    DISABLED = "disabled"
    SUBTLE = "subtle"
    BALANCED = "balanced" 
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class CompressionType(Enum):
    """Dynamic range compression types."""
    PEAK_LIMITER = "peak_limiter"
    RMS_COMPRESSOR = "rms_compressor"
    MULTIBAND = "multiband"
    ADAPTIVE = "adaptive"


@dataclass
class EnhancementMetrics:
    """Audio enhancement performance metrics."""
    dynamic_range_db: float = 0.0
    peak_reduction_db: float = 0.0
    rms_level_db: float = 0.0
    spectral_clarity: float = 0.0
    processing_latency_ms: float = 0.0
    enhancement_applied: bool = False
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class AudioProfile:
    """Audio characteristics profile."""
    frequency_response: np.ndarray  # Magnitude response
    dynamic_range: float
    peak_level: float
    rms_level: float
    spectral_centroid: float
    confidence: float
    update_count: int = 1
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class DynamicRangeCompressor:
    """Dynamic range compressor with configurable characteristics."""
    
    def __init__(self,
                 threshold_db: float = -20.0,
                 ratio: float = 4.0,
                 attack_ms: float = 5.0,
                 release_ms: float = 50.0,
                 sample_rate: int = 16000,
                 compression_type: CompressionType = CompressionType.RMS_COMPRESSOR):
        self.threshold_db = threshold_db
        self.ratio = ratio
        self.attack_ms = attack_ms
        self.release_ms = release_ms
        self.sample_rate = sample_rate
        self.compression_type = compression_type
        
        # Convert to linear threshold
        self.threshold_linear = 10 ** (threshold_db / 20.0)
        
        # Time constants
        self.attack_coeff = np.exp(-1.0 / (attack_ms * sample_rate / 1000.0))
        self.release_coeff = np.exp(-1.0 / (release_ms * sample_rate / 1000.0))
        
        # State variables
        self.envelope = 0.0
        self.gain_reduction = 0.0
        
        # Multiband state (if using multiband compression)
        self.band_compressors = []
        if compression_type == CompressionType.MULTIBAND:
            self._init_multiband()
        
        # Statistics
        self.samples_processed = 0
        self.peak_reductions = deque(maxlen=1000)
        
    def _init_multiband(self):
        """Initialize multiband compression."""
        # Three bands: low (80-300Hz), mid (300-3000Hz), high (3000Hz+)
        band_configs = [
            {"threshold": -25.0, "ratio": 3.0, "freq_range": (80, 300)},
            {"threshold": -18.0, "ratio": 4.0, "freq_range": (300, 3000)},
            {"threshold": -15.0, "ratio": 6.0, "freq_range": (3000, 8000)}
        ]
        
        for config in band_configs:
            compressor = DynamicRangeCompressor(
                threshold_db=config["threshold"],
                ratio=config["ratio"],
                compression_type=CompressionType.RMS_COMPRESSOR
            )
            self.band_compressors.append((compressor, config["freq_range"]))
    
    def compress(self, audio_frame: np.ndarray) -> np.ndarray:
        """Apply dynamic range compression."""
        if self.compression_type == CompressionType.MULTIBAND:
            return self._compress_multiband(audio_frame)
        elif self.compression_type == CompressionType.PEAK_LIMITER:
            return self._compress_peak_limit(audio_frame)
        else:
            return self._compress_rms(audio_frame)
            
    def _compress_rms(self, audio_frame: np.ndarray) -> np.ndarray:
        """RMS-based compression."""
        compressed = np.zeros_like(audio_frame)
        
        for i, sample in enumerate(audio_frame):
            # Envelope detection (RMS-like)
            sample_squared = sample * sample
            
            if sample_squared > self.envelope:
                # Attack
                self.envelope = sample_squared + self.attack_coeff * (self.envelope - sample_squared)
            else:
                # Release  
                self.envelope = sample_squared + self.release_coeff * (self.envelope - sample_squared)
            
            # Gain calculation
            envelope_level = np.sqrt(self.envelope + 1e-10)
            
            if envelope_level > self.threshold_linear:
                # Compression needed
                target_gain = self.threshold_linear / envelope_level
                compressed_gain = target_gain ** (1.0 / self.ratio)
                gain = min(1.0, compressed_gain)
            else:
                gain = 1.0
                
            # Smooth gain changes
            gain_diff = gain - self.gain_reduction
            if gain_diff < 0:  # Gain reduction
                self.gain_reduction += gain_diff * (1.0 - self.attack_coeff)
            else:  # Gain recovery
                self.gain_reduction += gain_diff * (1.0 - self.release_coeff)
                
            compressed[i] = sample * self.gain_reduction
            
        self.samples_processed += len(audio_frame)
        
        # Track peak reduction
        input_peak = np.max(np.abs(audio_frame))
        output_peak = np.max(np.abs(compressed))
        if input_peak > 0:
            reduction_db = 20 * np.log10(output_peak / input_peak + 1e-10)
            self.peak_reductions.append(reduction_db)
            
        return compressed
        
    def _compress_peak_limit(self, audio_frame: np.ndarray) -> np.ndarray:
        """Peak limiter - hard limit at threshold."""
        limited = audio_frame.copy()
        
        # Simple peak limiting
        peak_indices = np.abs(limited) > self.threshold_linear
        limited[peak_indices] = np.sign(limited[peak_indices]) * self.threshold_linear
        
        return limited
        
    def _compress_multiband(self, audio_frame: np.ndarray) -> np.ndarray:
        """Multiband compression using FFT."""
        # Simple multiband - split into frequency bands and compress separately
        fft_data = np.fft.fft(audio_frame)
        freqs = np.fft.fftfreq(len(audio_frame), 1/self.sample_rate)
        
        compressed_fft = fft_data.copy()
        
        for compressor, (low_freq, high_freq) in self.band_compressors:
            # Find frequency band
            band_mask = (np.abs(freqs) >= low_freq) & (np.abs(freqs) <= high_freq)
            
            if np.any(band_mask):
                # Extract band
                band_fft = fft_data * band_mask
                band_audio = np.real(np.fft.ifft(band_fft))
                
                # Compress band
                compressed_band = compressor._compress_rms(band_audio)
                
                # Put back
                compressed_band_fft = np.fft.fft(compressed_band)
                compressed_fft[band_mask] = compressed_band_fft[band_mask]
        
        return np.real(np.fft.ifft(compressed_fft))
    
    def get_statistics(self) -> Dict:
        """Get compression statistics."""
        avg_reduction = np.mean(self.peak_reductions) if self.peak_reductions else 0.0
        
        return {
            "samples_processed": self.samples_processed,
            "threshold_db": self.threshold_db,
            "ratio": self.ratio,
            "avg_peak_reduction_db": avg_reduction,
            "current_gain_reduction": 1.0 - self.gain_reduction,
            "compression_type": self.compression_type.value
        }


class SpectralEnhancer:
    """Spectral enhancement for voice clarity and intelligibility."""
    
    def __init__(self,
                 sample_rate: int = 16000,
                 frame_size: int = 512,
                 enhancement_factor: float = 1.5):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.enhancement_factor = enhancement_factor
        
        # Frequency bands for speech enhancement
        self.speech_bands = {
            "fundamental": (80, 250),      # Fundamental frequencies
            "formant1": (250, 1000),       # First formant region  
            "formant2": (1000, 3000),      # Second formant region
            "fricatives": (3000, 8000)    # Fricative sounds
        }
        
        # Enhancement gains per band
        self.band_gains = {
            "fundamental": 1.0,   # Preserve fundamental
            "formant1": 1.3,      # Boost first formant
            "formant2": 1.5,      # Boost second formant  
            "fricatives": 1.2     # Moderate fricative boost
        }
        
        # Spectral smoothing
        self.smoothing_factor = 0.8
        self.prev_magnitude = None
        
        # Statistics
        self.frames_processed = 0
        self.enhancement_applied = 0
        
    def enhance(self, audio_frame: np.ndarray) -> np.ndarray:
        """Apply spectral enhancement."""
        if len(audio_frame) != self.frame_size:
            # Pad or truncate to frame size
            if len(audio_frame) < self.frame_size:
                padded = np.zeros(self.frame_size)
                padded[:len(audio_frame)] = audio_frame
                audio_frame = padded
            else:
                audio_frame = audio_frame[:self.frame_size]
        
        # FFT analysis
        fft_data = np.fft.fft(audio_frame)
        magnitude = np.abs(fft_data)
        phase = np.angle(fft_data)
        
        # Frequency bins
        freqs = np.fft.fftfreq(self.frame_size, 1/self.sample_rate)
        freqs = np.abs(freqs[:self.frame_size//2])  # Positive frequencies only
        
        # Apply enhancement to positive frequencies
        enhanced_magnitude = magnitude.copy()
        
        for band_name, (low_freq, high_freq) in self.speech_bands.items():
            # Find frequency range
            band_mask = (freqs >= low_freq) & (freqs <= high_freq)
            
            if np.any(band_mask):
                gain = self.band_gains[band_name] * self.enhancement_factor
                
                # Apply gain with smoothing
                enhanced_magnitude[:len(band_mask)][band_mask] *= gain
                
                # Mirror for negative frequencies
                if len(enhanced_magnitude) > len(band_mask):
                    enhanced_magnitude[-len(band_mask):][band_mask[::-1]] *= gain
        
        # Spectral smoothing
        if self.prev_magnitude is not None:
            enhanced_magnitude = (self.smoothing_factor * self.prev_magnitude + 
                                (1 - self.smoothing_factor) * enhanced_magnitude)
        
        self.prev_magnitude = enhanced_magnitude.copy()
        
        # Reconstruct signal
        enhanced_fft = enhanced_magnitude * np.exp(1j * phase)
        enhanced_audio = np.real(np.fft.ifft(enhanced_fft))
        
        self.frames_processed += 1
        self.enhancement_applied += 1
        
        return enhanced_audio[:len(audio_frame)]  # Return original length
    
    def get_statistics(self) -> Dict:
        """Get enhancement statistics."""
        return {
            "frames_processed": self.frames_processed,
            "enhancement_applied": self.enhancement_applied,
            "enhancement_factor": self.enhancement_factor,
            "frame_size": self.frame_size,
            "speech_bands": len(self.speech_bands)
        }


class EqualizerBand:
    """Single equalizer band with configurable frequency response."""
    
    def __init__(self, center_freq: float, gain_db: float, q_factor: float = 1.0):
        self.center_freq = center_freq
        self.gain_db = gain_db
        self.q_factor = q_factor
        self.gain_linear = 10 ** (gain_db / 20.0)
        
    def apply_to_spectrum(self, freqs: np.ndarray, magnitude: np.ndarray) -> np.ndarray:
        """Apply band to frequency spectrum."""
        # Bell filter response
        normalized_freq = freqs / self.center_freq
        
        # Bell filter formula
        bandwidth = self.center_freq / self.q_factor
        response = 1.0 / np.sqrt(1 + ((freqs - self.center_freq) / (bandwidth/2))**2)
        
        # Apply gain
        if self.gain_db >= 0:
            # Boost
            gain_response = 1 + (self.gain_linear - 1) * response
        else:
            # Cut
            gain_response = 1 - (1 - self.gain_linear) * response
            
        return magnitude * gain_response


class ParametricEqualizer:
    """Multi-band parametric equalizer."""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.bands: List[EqualizerBand] = []
        
        # Default voice-optimized EQ
        self._setup_voice_eq()
        
        # Statistics
        self.frames_processed = 0
        
    def _setup_voice_eq(self):
        """Setup default voice enhancement EQ."""
        # Voice-optimized frequency response
        voice_bands = [
            (125, -2.0, 0.7),   # Reduce low rumble
            (250, 1.0, 1.0),    # Slight boost to warmth
            (500, 2.0, 1.2),    # Boost speech fundamentals  
            (1000, 3.0, 1.5),   # Boost speech clarity
            (2000, 2.5, 1.2),   # Boost consonant clarity
            (4000, 1.5, 1.0),   # Moderate presence boost
            (8000, -1.0, 0.8)   # Slight high-frequency roll-off
        ]
        
        for freq, gain, q in voice_bands:
            self.add_band(freq, gain, q)
    
    def add_band(self, center_freq: float, gain_db: float, q_factor: float = 1.0):
        """Add EQ band."""
        band = EqualizerBand(center_freq, gain_db, q_factor)
        self.bands.append(band)
        
    def clear_bands(self):
        """Clear all EQ bands."""
        self.bands.clear()
        
    def equalize(self, audio_frame: np.ndarray) -> np.ndarray:
        """Apply parametric equalization."""
        if len(self.bands) == 0:
            return audio_frame
            
        # FFT analysis
        fft_data = np.fft.fft(audio_frame)
        magnitude = np.abs(fft_data)
        phase = np.angle(fft_data)
        
        # Frequency bins
        freqs = np.fft.fftfreq(len(audio_frame), 1/self.sample_rate)
        freqs = np.abs(freqs)  # Use absolute frequencies
        
        # Apply all bands
        equalized_magnitude = magnitude.copy()
        
        for band in self.bands:
            equalized_magnitude = band.apply_to_spectrum(freqs, equalized_magnitude)
        
        # Reconstruct signal
        equalized_fft = equalized_magnitude * np.exp(1j * phase)
        equalized_audio = np.real(np.fft.ifft(equalized_fft))
        
        self.frames_processed += 1
        
        return equalized_audio
    
    def get_statistics(self) -> Dict:
        """Get equalizer statistics."""
        band_info = []
        for band in self.bands:
            band_info.append({
                "freq": band.center_freq,
                "gain_db": band.gain_db,
                "q": band.q_factor
            })
        
        return {
            "frames_processed": self.frames_processed,
            "num_bands": len(self.bands),
            "bands": band_info
        }


class AudioEnhancer:
    """Main audio quality enhancement system."""
    
    def __init__(self,
                 mode: EnhancementMode = EnhancementMode.BALANCED,
                 sample_rate: int = 16000,
                 frame_size: int = 480):
        self.mode = mode
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        
        # Enhancement components
        self.compressor = self._create_compressor()
        self.spectral_enhancer = SpectralEnhancer(sample_rate, frame_size)
        self.equalizer = ParametricEqualizer(sample_rate)
        
        # Processing chain order
        self.processing_chain = ["equalizer", "spectral_enhancer", "compressor"]
        
        # Audio profiling
        self.current_profile: Optional[AudioProfile] = None
        self.profile_frames = deque(maxlen=100)
        
        # Statistics
        self.frames_processed = 0
        self.processing_times = deque(maxlen=100)
        self.enhancement_effectiveness = deque(maxlen=50)
        
        # Thread safety
        self._lock = threading.Lock()
        
    def _create_compressor(self) -> DynamicRangeCompressor:
        """Create compressor based on enhancement mode."""
        if self.mode == EnhancementMode.SUBTLE:
            return DynamicRangeCompressor(
                threshold_db=-15.0, ratio=2.0, attack_ms=10.0, release_ms=100.0
            )
        elif self.mode == EnhancementMode.BALANCED:
            return DynamicRangeCompressor(
                threshold_db=-18.0, ratio=3.0, attack_ms=5.0, release_ms=50.0
            )
        elif self.mode == EnhancementMode.AGGRESSIVE:
            return DynamicRangeCompressor(
                threshold_db=-12.0, ratio=6.0, attack_ms=2.0, release_ms=25.0,
                compression_type=CompressionType.MULTIBAND
            )
        else:  # DISABLED or CUSTOM
            return DynamicRangeCompressor(
                threshold_db=-30.0, ratio=1.0  # Minimal compression
            )
    
    def enhance_audio(self, audio_frame: np.ndarray,
                     return_metrics: bool = False) -> Union[np.ndarray, Tuple[np.ndarray, EnhancementMetrics]]:
        """Apply audio quality enhancement."""
        start_time = time.time()
        
        with self._lock:
            if self.mode == EnhancementMode.DISABLED:
                if return_metrics:
                    metrics = EnhancementMetrics()
                    return audio_frame.copy(), metrics
                return audio_frame.copy()
                
            # Store original for comparison
            original_audio = audio_frame.copy()
            enhanced_audio = audio_frame.copy()
            
            # Apply processing chain
            for processor_name in self.processing_chain:
                if processor_name == "equalizer":
                    enhanced_audio = self.equalizer.equalize(enhanced_audio)
                elif processor_name == "spectral_enhancer":
                    enhanced_audio = self.spectral_enhancer.enhance(enhanced_audio)
                elif processor_name == "compressor":
                    enhanced_audio = self.compressor.compress(enhanced_audio)
                    
            # Update audio profile
            self._update_audio_profile(enhanced_audio)
            
            # Compute metrics
            processing_time = (time.time() - start_time) * 1000  # ms
            self.processing_times.append(processing_time)
            
            if return_metrics:
                metrics = self._compute_metrics(original_audio, enhanced_audio, processing_time)
                
            self.frames_processed += 1
            
            if return_metrics:
                return enhanced_audio, metrics
            return enhanced_audio
            
    def _update_audio_profile(self, audio_frame: np.ndarray):
        """Update audio characteristics profile."""
        # Basic audio analysis
        rms_level = np.sqrt(np.mean(audio_frame ** 2))
        peak_level = np.max(np.abs(audio_frame))
        
        if peak_level > 0:
            dynamic_range = 20 * np.log10(peak_level / (rms_level + 1e-10))
        else:
            dynamic_range = 0.0
            
        # Spectral analysis
        fft_data = np.fft.fft(audio_frame)
        magnitude = np.abs(fft_data[:len(audio_frame)//2])
        freqs = np.fft.fftfreq(len(audio_frame), 1/self.sample_rate)[:len(audio_frame)//2]
        
        # Spectral centroid
        if np.sum(magnitude) > 0:
            spectral_centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
        else:
            spectral_centroid = 0.0
            
        self.profile_frames.append({
            "rms": rms_level,
            "peak": peak_level,
            "dynamic_range": dynamic_range,
            "spectral_centroid": spectral_centroid,
            "magnitude": magnitude
        })
        
    def _compute_metrics(self, original: np.ndarray, enhanced: np.ndarray,
                        processing_time: float) -> EnhancementMetrics:
        """Compute enhancement performance metrics."""
        # Dynamic range comparison
        orig_rms = np.sqrt(np.mean(original ** 2))
        orig_peak = np.max(np.abs(original))
        enh_rms = np.sqrt(np.mean(enhanced ** 2))
        enh_peak = np.max(np.abs(enhanced))
        
        if orig_rms > 0:
            orig_dr = 20 * np.log10(orig_peak / orig_rms)
        else:
            orig_dr = 0.0
            
        if enh_rms > 0:
            enh_dr = 20 * np.log10(enh_peak / enh_rms)
        else:
            enh_dr = 0.0
            
        # Peak reduction
        peak_reduction = 20 * np.log10(orig_peak / (enh_peak + 1e-10))
        
        # RMS level  
        rms_level_db = 20 * np.log10(enh_rms + 1e-10)
        
        # Spectral clarity (simplified measure)
        orig_fft = np.abs(np.fft.fft(original))
        enh_fft = np.abs(np.fft.fft(enhanced))
        
        # High frequency content ratio as clarity measure
        mid_freq_orig = np.sum(orig_fft[len(orig_fft)//4:len(orig_fft)//2])
        mid_freq_enh = np.sum(enh_fft[len(enh_fft)//4:len(enh_fft)//2])
        
        if mid_freq_orig > 0:
            spectral_clarity = mid_freq_enh / mid_freq_orig
        else:
            spectral_clarity = 1.0
            
        return EnhancementMetrics(
            dynamic_range_db=enh_dr,
            peak_reduction_db=peak_reduction,
            rms_level_db=rms_level_db,
            spectral_clarity=spectral_clarity,
            processing_latency_ms=processing_time,
            enhancement_applied=True
        )
        
    def set_mode(self, mode: EnhancementMode):
        """Set enhancement mode."""
        with self._lock:
            self.mode = mode
            self.compressor = self._create_compressor()
            
            # Adjust spectral enhancer
            if mode == EnhancementMode.SUBTLE:
                self.spectral_enhancer.enhancement_factor = 1.2
            elif mode == EnhancementMode.BALANCED:
                self.spectral_enhancer.enhancement_factor = 1.5
            elif mode == EnhancementMode.AGGRESSIVE:
                self.spectral_enhancer.enhancement_factor = 2.0
            else:
                self.spectral_enhancer.enhancement_factor = 1.0
                
    def reset(self):
        """Reset enhancement state."""
        with self._lock:
            self.compressor = self._create_compressor()
            self.spectral_enhancer = SpectralEnhancer(self.sample_rate, self.frame_size)
            self.equalizer = ParametricEqualizer(self.sample_rate)
            self.profile_frames.clear()
            self.processing_times.clear()
            self.enhancement_effectiveness.clear()
            self.frames_processed = 0
            
    def get_statistics(self) -> Dict:
        """Get comprehensive enhancement statistics."""
        with self._lock:
            compressor_stats = self.compressor.get_statistics()
            enhancer_stats = self.spectral_enhancer.get_statistics()
            eq_stats = self.equalizer.get_statistics()
            
            avg_processing_time = np.mean(self.processing_times) if self.processing_times else 0.0
            
            # Audio profile summary
            if self.profile_frames:
                avg_rms = np.mean([f["rms"] for f in self.profile_frames])
                avg_peak = np.mean([f["peak"] for f in self.profile_frames])
                avg_dr = np.mean([f["dynamic_range"] for f in self.profile_frames])
                avg_centroid = np.mean([f["spectral_centroid"] for f in self.profile_frames])
            else:
                avg_rms = avg_peak = avg_dr = avg_centroid = 0.0
            
            return {
                "mode": self.mode.value,
                "frames_processed": self.frames_processed,
                "avg_processing_time_ms": avg_processing_time,
                "compressor": compressor_stats,
                "spectral_enhancer": enhancer_stats,
                "equalizer": eq_stats,
                "audio_profile": {
                    "avg_rms_level": avg_rms,
                    "avg_peak_level": avg_peak,
                    "avg_dynamic_range_db": avg_dr,
                    "avg_spectral_centroid_hz": avg_centroid
                }
            }


class AudioEnhancerPool:
    """Thread-safe pool of audio enhancers for different contexts."""
    
    def __init__(self):
        self.enhancers: Dict[str, AudioEnhancer] = {}
        self.default_enhancer = "main"
        self._lock = threading.Lock()
        
    def create_enhancer(self, name: str, mode: EnhancementMode = EnhancementMode.BALANCED,
                       **kwargs) -> AudioEnhancer:
        """Create and register audio enhancer."""
        with self._lock:
            enhancer = AudioEnhancer(mode=mode, **kwargs)
            self.enhancers[name] = enhancer
            return enhancer
            
    def get_enhancer(self, name: Optional[str] = None) -> Optional[AudioEnhancer]:
        """Get audio enhancer by name."""
        with self._lock:
            if name is None:
                name = self.default_enhancer
            return self.enhancers.get(name)
            
    def remove_enhancer(self, name: str) -> bool:
        """Remove audio enhancer."""
        with self._lock:
            if name in self.enhancers:
                del self.enhancers[name]
                return True
            return False
            
    def set_default(self, name: str):
        """Set default audio enhancer."""
        with self._lock:
            if name in self.enhancers:
                self.default_enhancer = name
                
    def reset_all(self):
        """Reset all audio enhancers."""
        with self._lock:
            for enhancer in self.enhancers.values():
                enhancer.reset()


# Global pool instance
_audio_enhancer_pool: Optional[AudioEnhancerPool] = None


def get_enhancer_pool() -> AudioEnhancerPool:
    """Get global audio enhancer pool."""
    global _audio_enhancer_pool
    if _audio_enhancer_pool is None:
        _audio_enhancer_pool = AudioEnhancerPool()
    return _audio_enhancer_pool


def create_enhancer(name: str = "main", 
                   mode: EnhancementMode = EnhancementMode.BALANCED,
                   **kwargs) -> AudioEnhancer:
    """Create audio enhancer in global pool."""
    pool = get_enhancer_pool()
    return pool.create_enhancer(name, mode, **kwargs)