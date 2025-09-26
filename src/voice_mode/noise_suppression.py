#!/usr/bin/env python3
"""Advanced background noise suppression system.

This module provides sophisticated noise reduction algorithms including:
- Spectral subtraction with multi-band processing
- Wiener filtering with adaptive coefficients
- Gaussian noise modeling and estimation
- Real-time noise profile adaptation
- VAD-guided noise learning
"""

import logging
import time
import numpy as np
import threading
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import warnings

# Suppress numpy warnings for cleaner output
warnings.filterwarnings("ignore", category=RuntimeWarning)

logger = logging.getLogger(__name__)

class NoiseSuppressionMode(Enum):
    """Noise suppression operating modes."""
    MILD = "mild"           # Light suppression, preserve speech quality
    MODERATE = "moderate"   # Balanced suppression and quality
    AGGRESSIVE = "aggressive"  # Maximum suppression, may affect speech
    ADAPTIVE = "adaptive"   # Dynamic adjustment based on conditions

class NoiseType(Enum):
    """Types of background noise."""
    STATIONARY = "stationary"     # Constant noise (fans, AC)
    NON_STATIONARY = "non_stationary"  # Variable noise (keyboard, traffic)
    IMPULSIVE = "impulsive"       # Sudden noise (door slam, cough)
    BROADBAND = "broadband"       # Wide frequency range noise
    NARROWBAND = "narrowband"     # Specific frequency noise

@dataclass
class NoiseProfile:
    """Noise characteristics profile."""
    spectrum: np.ndarray = field(default_factory=lambda: np.array([]))
    power_density: float = 0.0
    spectral_centroid: float = 0.0
    spectral_rolloff: float = 0.0
    zero_crossing_rate: float = 0.0
    noise_type: NoiseType = NoiseType.STATIONARY
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    update_count: int = 0

@dataclass
class SuppressionMetrics:
    """Noise suppression performance metrics."""
    noise_reduction_db: float = 0.0
    speech_distortion: float = 0.0
    processing_latency_ms: float = 0.0
    snr_improvement_db: float = 0.0
    spectral_flatness: float = 0.0
    suppression_factor: float = 0.0
    timestamp: float = field(default_factory=time.time)

class SpectralSubtractor:
    """Spectral subtraction noise reduction."""
    
    def __init__(
        self,
        alpha: float = 2.0,
        beta: float = 0.01,
        frame_size: int = 512,
        hop_size: int = 256
    ):
        self.alpha = alpha  # Over-subtraction factor
        self.beta = beta    # Spectral floor factor
        self.frame_size = frame_size
        self.hop_size = hop_size
        
        # Initialize noise estimate
        self.noise_spectrum = None
        self.noise_update_rate = 0.1
        self.frames_processed = 0
        
        # Windowing
        self.window = np.hanning(frame_size)
        
    def update_noise_estimate(self, spectrum: np.ndarray, is_noise: bool = True):
        """Update noise spectrum estimate."""
        if self.noise_spectrum is None:
            self.noise_spectrum = np.abs(spectrum).copy()
        elif is_noise:
            # Update during noise-only periods
            rate = self.noise_update_rate
            self.noise_spectrum = (1 - rate) * self.noise_spectrum + rate * np.abs(spectrum)
    
    def suppress(self, audio_frame: np.ndarray) -> np.ndarray:
        """Apply spectral subtraction."""
        if len(audio_frame) != self.frame_size:
            # Pad or truncate to frame size
            if len(audio_frame) < self.frame_size:
                audio_frame = np.pad(audio_frame, (0, self.frame_size - len(audio_frame)))
            else:
                audio_frame = audio_frame[:self.frame_size]
        
        # Apply window
        windowed = audio_frame * self.window
        
        # FFT
        spectrum = np.fft.fft(windowed)
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)
        
        # Initialize or update noise estimate
        if self.noise_spectrum is None:
            self.noise_spectrum = magnitude.copy()
            return audio_frame  # Return original for first frame
        
        # Spectral subtraction
        suppressed_magnitude = magnitude - self.alpha * self.noise_spectrum
        
        # Apply spectral floor
        floor = self.beta * magnitude
        suppressed_magnitude = np.maximum(suppressed_magnitude, floor)
        
        # Reconstruct spectrum
        suppressed_spectrum = suppressed_magnitude * np.exp(1j * phase)
        
        # IFFT
        suppressed_audio = np.fft.ifft(suppressed_spectrum).real
        
        # Remove window
        suppressed_audio = suppressed_audio * self.window
        
        self.frames_processed += 1
        return suppressed_audio

class WienerFilter:
    """Wiener filtering for noise suppression."""
    
    def __init__(
        self,
        frame_size: int = 512,
        noise_estimation_time: float = 0.5
    ):
        self.frame_size = frame_size
        self.noise_estimation_frames = int(noise_estimation_time * 16000 / frame_size)
        
        # Noise and signal power estimates
        self.noise_power = None
        self.signal_power = None
        self.noise_frames = []
        
        # Smoothing parameters
        self.noise_alpha = 0.1
        self.signal_alpha = 0.3
        
    def estimate_noise_power(self, spectrum: np.ndarray):
        """Estimate noise power spectrum."""
        power = np.abs(spectrum) ** 2
        # Use only positive frequencies
        power = power[:self.frame_size // 2 + 1]
        
        if self.noise_power is None:
            self.noise_power = power.copy()
        else:
            self.noise_power = ((1 - self.noise_alpha) * self.noise_power + 
                               self.noise_alpha * power)
    
    def estimate_signal_power(self, spectrum: np.ndarray):
        """Estimate signal power spectrum."""
        power = np.abs(spectrum) ** 2
        # Use only positive frequencies
        power = power[:self.frame_size // 2 + 1]
        
        if self.signal_power is None:
            self.signal_power = power.copy()
        else:
            self.signal_power = ((1 - self.signal_alpha) * self.signal_power + 
                                self.signal_alpha * power)
    
    def compute_wiener_gain(self) -> np.ndarray:
        """Compute Wiener filter gain."""
        if self.noise_power is None or self.signal_power is None:
            return np.ones(self.frame_size // 2 + 1)
        
        # Wiener gain formula: G = S / (S + N)
        gain = self.signal_power / (self.signal_power + self.noise_power)
        
        # Clip gain to reasonable range
        gain = np.clip(gain, 0.01, 1.0)
        
        return gain
    
    def filter(self, audio_frame: np.ndarray, is_speech: bool) -> np.ndarray:
        """Apply Wiener filtering."""
        if len(audio_frame) != self.frame_size:
            # Pad or truncate
            if len(audio_frame) < self.frame_size:
                audio_frame = np.pad(audio_frame, (0, self.frame_size - len(audio_frame)))
            else:
                audio_frame = audio_frame[:self.frame_size]
        
        # FFT
        spectrum = np.fft.fft(audio_frame)
        
        # Update power estimates
        if is_speech:
            self.estimate_signal_power(spectrum)
        else:
            self.estimate_noise_power(spectrum)
        
        # Compute and apply Wiener gain
        gain = self.compute_wiener_gain()
        
        # Apply gain (only to positive frequencies)
        filtered_spectrum = spectrum.copy()
        filtered_spectrum[:len(gain)] *= gain
        if len(gain) > 1:
            # Mirror for negative frequencies (exclude DC and Nyquist)
            filtered_spectrum[-len(gain)+1:] *= gain[1:][::-1]
        
        # IFFT
        filtered_audio = np.fft.ifft(filtered_spectrum).real
        
        return filtered_audio

class NoiseProfiler:
    """Analyze and classify background noise."""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.analysis_window = 1024
        self.profiles = deque(maxlen=100)  # Keep recent profiles
        
    def analyze_noise(self, audio_frame: np.ndarray) -> NoiseProfile:
        """Analyze audio frame and create noise profile."""
        profile = NoiseProfile()
        
        # Ensure minimum frame size
        if len(audio_frame) < self.analysis_window:
            audio_frame = np.pad(audio_frame, (0, self.analysis_window - len(audio_frame)))
        
        # Spectral analysis
        spectrum = np.fft.fft(audio_frame[:self.analysis_window])
        magnitude = np.abs(spectrum)
        profile.spectrum = magnitude[:self.analysis_window // 2]
        
        # Power density
        profile.power_density = np.mean(magnitude ** 2)
        
        # Spectral centroid
        freqs = np.fft.fftfreq(self.analysis_window, 1/self.sample_rate)
        freqs = freqs[:self.analysis_window // 2]
        if np.sum(profile.spectrum) > 0:
            profile.spectral_centroid = np.sum(freqs * profile.spectrum) / np.sum(profile.spectrum)
        
        # Spectral rolloff (85% of energy)
        cumulative_energy = np.cumsum(profile.spectrum ** 2)
        total_energy = cumulative_energy[-1]
        if total_energy > 0:
            rolloff_idx = np.where(cumulative_energy >= 0.85 * total_energy)[0]
            if len(rolloff_idx) > 0:
                profile.spectral_rolloff = freqs[rolloff_idx[0]]
        
        # Zero crossing rate
        zero_crossings = np.diff(np.signbit(audio_frame))
        profile.zero_crossing_rate = np.sum(zero_crossings) / len(audio_frame)
        
        # Classify noise type
        profile.noise_type = self._classify_noise_type(profile)
        profile.confidence = self._compute_confidence(profile)
        profile.update_count = 1
        
        return profile
    
    def _classify_noise_type(self, profile: NoiseProfile) -> NoiseType:
        """Classify the type of noise based on characteristics."""
        # Simple heuristic classification
        if profile.spectral_centroid < 1000:
            if profile.zero_crossing_rate < 0.1:
                return NoiseType.STATIONARY
            else:
                return NoiseType.BROADBAND
        elif profile.spectral_centroid > 4000:
            return NoiseType.NARROWBAND
        else:
            if profile.zero_crossing_rate > 0.2:
                return NoiseType.NON_STATIONARY
            else:
                return NoiseType.STATIONARY
    
    def _compute_confidence(self, profile: NoiseProfile) -> float:
        """Compute confidence in noise classification."""
        # Simple confidence metric based on spectral consistency
        if len(profile.spectrum) == 0:
            return 0.0
        
        spectral_flatness = np.exp(np.mean(np.log(profile.spectrum + 1e-10))) / np.mean(profile.spectrum + 1e-10)
        confidence = min(1.0, spectral_flatness * 2)  # Normalize to 0-1
        return confidence
    
    def update_profile(self, new_profile: NoiseProfile):
        """Update noise profile with new measurements."""
        self.profiles.append(new_profile)
    
    def get_average_profile(self) -> Optional[NoiseProfile]:
        """Get averaged noise profile from recent measurements."""
        if not self.profiles:
            return None
        
        # Average recent profiles
        avg_profile = NoiseProfile()
        
        # Combine spectra (taking same length)
        min_len = min(len(p.spectrum) for p in self.profiles if len(p.spectrum) > 0)
        if min_len > 0:
            spectra = [p.spectrum[:min_len] for p in self.profiles if len(p.spectrum) >= min_len]
            if spectra:
                avg_profile.spectrum = np.mean(spectra, axis=0)
        
        # Average other metrics
        avg_profile.power_density = np.mean([p.power_density for p in self.profiles])
        avg_profile.spectral_centroid = np.mean([p.spectral_centroid for p in self.profiles])
        avg_profile.spectral_rolloff = np.mean([p.spectral_rolloff for p in self.profiles])
        avg_profile.zero_crossing_rate = np.mean([p.zero_crossing_rate for p in self.profiles])
        avg_profile.confidence = np.mean([p.confidence for p in self.profiles])
        avg_profile.update_count = sum(p.update_count for p in self.profiles)
        
        # Most common noise type
        noise_types = [p.noise_type for p in self.profiles]
        avg_profile.noise_type = max(set(noise_types), key=noise_types.count)
        
        return avg_profile

class AdaptiveNoiseSuppressor:
    """Main adaptive noise suppression system."""
    
    def __init__(
        self,
        mode: NoiseSuppressionMode = NoiseSuppressionMode.ADAPTIVE,
        sample_rate: int = 16000,
        frame_size: int = 512
    ):
        self.mode = mode
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        
        # Initialize components
        self.spectral_subtractor = SpectralSubtractor(frame_size=frame_size)
        self.wiener_filter = WienerFilter(frame_size=frame_size)
        self.noise_profiler = NoiseProfiler(sample_rate=sample_rate)
        
        # Adaptive parameters
        self.adaptation_rate = 0.1
        self.noise_learning_time = 2.0  # seconds
        self.frames_for_learning = int(self.noise_learning_time * sample_rate / frame_size)
        
        # State tracking
        self.is_learning = True
        self.learning_frames_count = 0
        self.current_noise_profile = None
        
        # Statistics
        self.stats = {
            "frames_processed": 0,
            "noise_frames": 0,
            "speech_frames": 0,
            "suppression_applied": 0,
            "avg_suppression_db": 0.0,
            "profile_updates": 0
        }
        
        # Threading
        self._lock = threading.Lock()
        
        logger.info(f"Adaptive noise suppressor initialized (mode={mode.value})")
    
    def set_mode(self, mode: NoiseSuppressionMode):
        """Set suppression mode."""
        with self._lock:
            self.mode = mode
            self._update_parameters()
            logger.debug(f"Suppression mode changed to {mode.value}")
    
    def _update_parameters(self):
        """Update algorithm parameters based on mode."""
        if self.mode == NoiseSuppressionMode.MILD:
            self.spectral_subtractor.alpha = 1.5
            self.spectral_subtractor.beta = 0.1
        elif self.mode == NoiseSuppressionMode.MODERATE:
            self.spectral_subtractor.alpha = 2.0
            self.spectral_subtractor.beta = 0.05
        elif self.mode == NoiseSuppressionMode.AGGRESSIVE:
            self.spectral_subtractor.alpha = 3.0
            self.spectral_subtractor.beta = 0.01
        # ADAPTIVE mode uses dynamic parameters
    
    def learn_noise(self, audio_frame: np.ndarray):
        """Learn noise characteristics during quiet periods."""
        if not self.is_learning and self.learning_frames_count < self.frames_for_learning:
            return
        
        profile = self.noise_profiler.analyze_noise(audio_frame)
        self.noise_profiler.update_profile(profile)
        
        # Update noise estimates in algorithms
        spectrum = np.fft.fft(audio_frame[:self.frame_size])
        self.spectral_subtractor.update_noise_estimate(spectrum, is_noise=True)
        self.wiener_filter.estimate_noise_power(spectrum)
        
        self.learning_frames_count += 1
        self.stats["noise_frames"] += 1
        self.stats["profile_updates"] += 1
        
        if self.learning_frames_count >= self.frames_for_learning:
            self.is_learning = False
            self.current_noise_profile = self.noise_profiler.get_average_profile()
            logger.info("Noise learning phase completed")
    
    def suppress_noise(
        self,
        audio_frame: np.ndarray,
        is_speech: bool = True,
        return_metrics: bool = False
    ) -> tuple[np.ndarray, Optional[SuppressionMetrics]]:
        """Apply noise suppression to audio frame."""
        start_time = time.time()
        metrics = SuppressionMetrics()
        
        with self._lock:
            # Learn from noise if not speech
            if not is_speech:
                self.learn_noise(audio_frame)
            
            # Skip suppression during initial learning
            if self.is_learning:
                self.stats["frames_processed"] += 1
                if return_metrics:
                    return audio_frame.copy(), metrics
                return audio_frame.copy()
            
            # Apply suppression based on mode
            if self.mode == NoiseSuppressionMode.ADAPTIVE:
                suppressed = self._adaptive_suppress(audio_frame, is_speech)
            else:
                # Use spectral subtraction as primary method
                suppressed = self.spectral_subtractor.suppress(audio_frame)
                
                # Apply Wiener filtering for moderate/aggressive modes
                if self.mode in [NoiseSuppressionMode.MODERATE, NoiseSuppressionMode.AGGRESSIVE]:
                    suppressed = self.wiener_filter.filter(suppressed, is_speech)
            
            # Calculate metrics
            metrics.processing_latency_ms = (time.time() - start_time) * 1000
            metrics.noise_reduction_db = self._calculate_noise_reduction(audio_frame, suppressed)
            metrics.suppression_factor = self._calculate_suppression_factor(audio_frame, suppressed)
            
            # Update statistics
            self.stats["frames_processed"] += 1
            if is_speech:
                self.stats["speech_frames"] += 1
            self.stats["suppression_applied"] += 1
            self.stats["avg_suppression_db"] = (
                (self.stats["avg_suppression_db"] * (self.stats["suppression_applied"] - 1) + 
                 metrics.noise_reduction_db) / self.stats["suppression_applied"]
            )
        
        if return_metrics:
            return suppressed, metrics
        return suppressed
    
    def _adaptive_suppress(self, audio_frame: np.ndarray, is_speech: bool) -> np.ndarray:
        """Apply adaptive suppression based on noise profile."""
        if self.current_noise_profile is None:
            # Fallback to spectral subtraction
            return self.spectral_subtractor.suppress(audio_frame)
        
        # Adjust parameters based on noise type
        if self.current_noise_profile.noise_type == NoiseType.STATIONARY:
            # Strong suppression for stationary noise
            self.spectral_subtractor.alpha = 2.5
            suppressed = self.spectral_subtractor.suppress(audio_frame)
        elif self.current_noise_profile.noise_type == NoiseType.NON_STATIONARY:
            # Use Wiener filtering for non-stationary noise
            suppressed = self.wiener_filter.filter(audio_frame, is_speech)
        else:
            # Combine both methods
            ss_result = self.spectral_subtractor.suppress(audio_frame)
            wf_result = self.wiener_filter.filter(audio_frame, is_speech)
            # Weighted combination
            suppressed = 0.6 * ss_result + 0.4 * wf_result
        
        return suppressed
    
    def _calculate_noise_reduction(self, original: np.ndarray, suppressed: np.ndarray) -> float:
        """Calculate noise reduction in dB."""
        original_power = np.mean(original ** 2)
        suppressed_power = np.mean(suppressed ** 2)
        
        if original_power > 0 and suppressed_power > 0:
            return 10 * np.log10(original_power / suppressed_power)
        return 0.0
    
    def _calculate_suppression_factor(self, original: np.ndarray, suppressed: np.ndarray) -> float:
        """Calculate suppression factor (0-1)."""
        original_energy = np.sum(original ** 2)
        suppressed_energy = np.sum(suppressed ** 2)
        
        if original_energy > 0:
            return 1 - (suppressed_energy / original_energy)
        return 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get suppression statistics."""
        with self._lock:
            stats = self.stats.copy()
            stats["learning_phase"] = self.is_learning
            stats["learning_progress"] = min(1.0, self.learning_frames_count / self.frames_for_learning)
            stats["current_mode"] = self.mode.value
            
            if self.current_noise_profile:
                stats["noise_type"] = self.current_noise_profile.noise_type.value
                stats["noise_confidence"] = self.current_noise_profile.confidence
                stats["spectral_centroid"] = self.current_noise_profile.spectral_centroid
            
            return stats
    
    def reset(self):
        """Reset suppressor state."""
        with self._lock:
            self.is_learning = True
            self.learning_frames_count = 0
            self.current_noise_profile = None
            
            # Reset algorithm states
            self.spectral_subtractor.noise_spectrum = None
            self.spectral_subtractor.frames_processed = 0
            self.wiener_filter.noise_power = None
            self.wiener_filter.signal_power = None
            self.noise_profiler.profiles.clear()
            
            # Reset statistics
            for key in self.stats:
                self.stats[key] = 0 if isinstance(self.stats[key], (int, float)) else 0.0
            
            logger.info("Noise suppressor reset")

class NoiseSuppressionPool:
    """Pool of noise suppressors for different contexts."""
    
    def __init__(self):
        self.suppressors: Dict[str, AdaptiveNoiseSuppressor] = {}
        self.default_suppressor = "default"
        self._lock = threading.Lock()
        
        logger.info("Noise suppression pool initialized")
    
    def create_suppressor(
        self,
        name: str,
        mode: NoiseSuppressionMode = NoiseSuppressionMode.ADAPTIVE
    ) -> AdaptiveNoiseSuppressor:
        """Create a new noise suppressor."""
        with self._lock:
            suppressor = AdaptiveNoiseSuppressor(mode=mode)
            self.suppressors[name] = suppressor
            logger.info(f"Created suppressor: {name} (mode={mode.value})")
            return suppressor
    
    def get_suppressor(self, name: str = None) -> Optional[AdaptiveNoiseSuppressor]:
        """Get suppressor by name."""
        if name is None:
            name = self.default_suppressor
        
        with self._lock:
            return self.suppressors.get(name)
    
    def set_default(self, name: str):
        """Set default suppressor."""
        with self._lock:
            if name in self.suppressors:
                self.default_suppressor = name
                logger.info(f"Default suppressor set to: {name}")
    
    def remove_suppressor(self, name: str):
        """Remove suppressor from pool."""
        with self._lock:
            if name in self.suppressors:
                del self.suppressors[name]
                logger.info(f"Removed suppressor: {name}")
    
    def reset_all(self):
        """Reset all suppressors."""
        with self._lock:
            for suppressor in self.suppressors.values():
                suppressor.reset()
            logger.info("All suppressors reset")

# Global pool instance
_suppressor_pool = None

def get_suppressor_pool() -> NoiseSuppressionPool:
    """Get global suppressor pool instance."""
    global _suppressor_pool
    if _suppressor_pool is None:
        _suppressor_pool = NoiseSuppressionPool()
    return _suppressor_pool

def create_suppressor(
    name: str = "default",
    mode: NoiseSuppressionMode = NoiseSuppressionMode.ADAPTIVE
) -> AdaptiveNoiseSuppressor:
    """Create a new noise suppressor (convenience function)."""
    pool = get_suppressor_pool()
    return pool.create_suppressor(name, mode)