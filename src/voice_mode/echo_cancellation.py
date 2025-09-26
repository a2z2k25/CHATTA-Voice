#!/usr/bin/env python3
"""
Advanced acoustic echo cancellation system for voice interactions.

Implements multiple echo cancellation algorithms including adaptive filtering,
delay estimation, and residual echo suppression to eliminate acoustic feedback
between speakers and microphones in voice communication systems.
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


class EchoCancellationMode(Enum):
    """Echo cancellation operating modes."""
    DISABLED = "disabled"
    BASIC = "basic"
    ADAPTIVE = "adaptive"
    AGGRESSIVE = "aggressive"


class DelayEstimationMode(Enum):
    """Delay estimation methods."""
    CROSS_CORRELATION = "cross_correlation"
    ADAPTIVE_FILTER = "adaptive_filter" 
    FREQUENCY_DOMAIN = "frequency_domain"


@dataclass
class EchoMetrics:
    """Echo cancellation performance metrics."""
    echo_return_loss_db: float = 0.0
    echo_suppression_db: float = 0.0
    delay_estimate_ms: float = 0.0
    filter_convergence: float = 0.0
    processing_latency_ms: float = 0.0
    residual_echo_db: float = 0.0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass 
class EchoProfile:
    """Acoustic echo characteristics profile."""
    room_impulse_response: np.ndarray
    delay_samples: int
    echo_path_gain: float
    reverberation_time: float
    confidence: float
    update_count: int = 1
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class DelayEstimator:
    """Estimates acoustic delay between reference and echo signals."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 max_delay_ms: float = 200.0,
                 mode: DelayEstimationMode = DelayEstimationMode.CROSS_CORRELATION):
        self.sample_rate = sample_rate
        self.max_delay_samples = int(max_delay_ms * sample_rate / 1000)
        self.mode = mode
        
        # Cross-correlation buffer
        self.reference_buffer = deque(maxlen=self.max_delay_samples * 2)
        self.echo_buffer = deque(maxlen=self.max_delay_samples * 2)
        
        # Delay tracking
        self.current_delay = 0
        self.delay_history = deque(maxlen=10)
        self.confidence = 0.0
        
        # Statistics
        self.estimates_computed = 0
        self.last_update_time = time.time()
        
    def estimate_delay(self, reference: np.ndarray, echo: np.ndarray) -> Tuple[int, float]:
        """Estimate delay between reference and echo signals."""
        self.reference_buffer.extend(reference)
        self.echo_buffer.extend(echo)
        
        if len(self.reference_buffer) < self.max_delay_samples:
            return self.current_delay, self.confidence
            
        ref_signal = np.array(list(self.reference_buffer))
        echo_signal = np.array(list(self.echo_buffer))
        
        if self.mode == DelayEstimationMode.CROSS_CORRELATION:
            delay, confidence = self._cross_correlation_delay(ref_signal, echo_signal)
        elif self.mode == DelayEstimationMode.FREQUENCY_DOMAIN:
            delay, confidence = self._frequency_domain_delay(ref_signal, echo_signal)
        else:
            delay, confidence = self._adaptive_filter_delay(ref_signal, echo_signal)
            
        # Update delay estimate with smoothing
        if confidence > 0.7:  # Only update with high confidence
            self.delay_history.append(delay)
            self.current_delay = int(np.median(self.delay_history))
            self.confidence = confidence
            
        self.estimates_computed += 1
        self.last_update_time = time.time()
        
        return self.current_delay, self.confidence
        
    def _cross_correlation_delay(self, reference: np.ndarray, echo: np.ndarray) -> Tuple[int, float]:
        """Estimate delay using cross-correlation."""
        # Normalize signals
        ref_norm = reference / (np.linalg.norm(reference) + 1e-10)
        echo_norm = echo / (np.linalg.norm(echo) + 1e-10)
        
        # Compute cross-correlation
        correlation = np.correlate(echo_norm, ref_norm, mode='full')
        
        # Find peak
        peak_idx = np.argmax(np.abs(correlation))
        delay = peak_idx - (len(ref_norm) - 1)
        
        # Confidence based on peak sharpness
        peak_value = np.abs(correlation[peak_idx])
        mean_value = np.mean(np.abs(correlation))
        confidence = min(1.0, (peak_value - mean_value) / (mean_value + 1e-10))
        
        return max(0, min(delay, self.max_delay_samples)), confidence
        
    def _frequency_domain_delay(self, reference: np.ndarray, echo: np.ndarray) -> Tuple[int, float]:
        """Estimate delay using frequency domain analysis."""
        # FFT-based delay estimation
        ref_fft = np.fft.fft(reference)
        echo_fft = np.fft.fft(echo)
        
        # Cross power spectral density
        cross_psd = echo_fft * np.conj(ref_fft)
        
        # Phase delay estimation
        phase_diff = np.angle(cross_psd)
        frequencies = np.fft.fftfreq(len(reference), 1/self.sample_rate)
        
        # Linear regression on phase vs frequency for delay
        valid_idx = (frequencies > 100) & (frequencies < self.sample_rate/4)
        if np.sum(valid_idx) < 10:
            return 0, 0.0
            
        phase_unwrapped = np.unwrap(phase_diff[valid_idx])
        freqs_valid = frequencies[valid_idx]
        
        # Slope gives delay
        slope = np.polyfit(freqs_valid * 2 * np.pi, phase_unwrapped, 1)[0]
        delay_samples = -slope
        
        # Confidence based on fit quality
        phase_pred = np.polyval([-delay_samples, 0], freqs_valid * 2 * np.pi)
        confidence = 1.0 - np.std(phase_unwrapped - phase_pred) / (np.pi + 1e-10)
        
        return max(0, min(int(delay_samples), self.max_delay_samples)), max(0, confidence)
        
    def _adaptive_filter_delay(self, reference: np.ndarray, echo: np.ndarray) -> Tuple[int, float]:
        """Estimate delay using adaptive filter convergence."""
        # Simplified LMS-based delay estimation
        best_delay = 0
        best_error = float('inf')
        
        # Test different delays
        for delay in range(0, min(len(reference)//2, self.max_delay_samples), 4):
            if delay >= len(reference):
                break
                
            delayed_ref = reference[delay:]
            echo_segment = echo[:len(delayed_ref)]
            
            if len(echo_segment) < 10:
                continue
                
            # Simple correlation coefficient
            error = np.std(echo_segment - delayed_ref * np.mean(echo_segment) / 
                          (np.mean(delayed_ref) + 1e-10))
            
            if error < best_error:
                best_error = error
                best_delay = delay
                
        confidence = 1.0 / (1.0 + best_error)
        return best_delay, confidence
        
    def get_statistics(self) -> Dict:
        """Get delay estimation statistics."""
        return {
            "current_delay_samples": self.current_delay,
            "current_delay_ms": self.current_delay * 1000.0 / self.sample_rate,
            "confidence": self.confidence,
            "estimates_computed": self.estimates_computed,
            "mode": self.mode.value,
            "max_delay_ms": self.max_delay_samples * 1000.0 / self.sample_rate,
            "delay_history_size": len(self.delay_history)
        }


class AdaptiveFilter:
    """Adaptive filter for echo cancellation using NLMS algorithm."""
    
    def __init__(self, 
                 filter_length: int = 256,
                 step_size: float = 0.1,
                 regularization: float = 1e-6):
        self.filter_length = filter_length
        self.step_size = step_size
        self.regularization = regularization
        
        # Filter coefficients
        self.weights = np.zeros(filter_length)
        self.input_buffer = np.zeros(filter_length)
        
        # Adaptation control
        self.is_adapting = True
        self.convergence_threshold = 1e-4
        self.adaptation_rate = 0.0
        
        # Statistics
        self.samples_processed = 0
        self.weight_updates = 0
        self.convergence_metric = 0.0
        
    def filter(self, input_sample: float, desired_sample: float, adapt: bool = True) -> float:
        """Process one sample through adaptive filter."""
        # Shift input buffer
        self.input_buffer[1:] = self.input_buffer[:-1]
        self.input_buffer[0] = input_sample
        
        # Filter output
        output = np.dot(self.weights, self.input_buffer)
        
        # Error signal
        error = desired_sample - output
        
        # Adaptation
        if adapt and self.is_adapting:
            # Normalized LMS update
            input_power = np.dot(self.input_buffer, self.input_buffer) + self.regularization
            step = self.step_size / input_power
            
            # Weight update
            self.weights += step * error * self.input_buffer
            self.weight_updates += 1
            
            # Convergence tracking
            weight_change = step * error * np.linalg.norm(self.input_buffer)
            self.convergence_metric = 0.9 * self.convergence_metric + 0.1 * weight_change
            
        self.samples_processed += 1
        return error
        
    def filter_block(self, input_block: np.ndarray, desired_block: np.ndarray, 
                    adapt: bool = True) -> np.ndarray:
        """Process block of samples."""
        output = np.zeros(len(input_block))
        for i, (inp, des) in enumerate(zip(input_block, desired_block)):
            output[i] = self.filter(inp, des, adapt)
        return output
        
    def reset(self):
        """Reset filter state."""
        self.weights.fill(0.0)
        self.input_buffer.fill(0.0)
        self.convergence_metric = 0.0
        self.samples_processed = 0
        self.weight_updates = 0
        
    def get_convergence(self) -> float:
        """Get filter convergence measure."""
        if self.weight_updates == 0:
            return 0.0
        return max(0.0, 1.0 - self.convergence_metric)
        
    def get_statistics(self) -> Dict:
        """Get filter statistics."""
        return {
            "samples_processed": self.samples_processed,
            "weight_updates": self.weight_updates,
            "convergence": self.get_convergence(),
            "filter_length": self.filter_length,
            "step_size": self.step_size,
            "is_adapting": self.is_adapting,
            "weight_norm": np.linalg.norm(self.weights)
        }


class ResidualEchoSuppressor:
    """Suppresses residual echo after adaptive filtering."""
    
    def __init__(self, 
                 frame_size: int = 480,
                 suppression_factor: float = 0.5):
        self.frame_size = frame_size
        self.suppression_factor = suppression_factor
        
        # Echo detection
        self.echo_threshold = 0.01
        self.echo_detected = False
        
        # Statistics
        self.frames_processed = 0
        self.echo_suppression_applied = 0
        
    def suppress(self, signal: np.ndarray, reference_level: float = 0.0) -> np.ndarray:
        """Apply residual echo suppression."""
        # Simple energy-based suppression
        signal_energy = np.mean(signal ** 2)
        
        # More sensitive echo detection - if there's both signal and reference
        if signal_energy > self.echo_threshold and reference_level > self.echo_threshold:
            # Apply suppression
            suppression_gain = max(0.1, 1.0 - self.suppression_factor)
            suppressed = signal * suppression_gain
            self.echo_suppression_applied += 1
            self.echo_detected = True
        else:
            suppressed = signal.copy()
            self.echo_detected = False
            
        self.frames_processed += 1
        return suppressed
        
    def get_statistics(self) -> Dict:
        """Get suppression statistics."""
        return {
            "frames_processed": self.frames_processed,
            "echo_suppression_applied": self.echo_suppression_applied,
            "echo_detected": self.echo_detected,
            "suppression_rate": (self.echo_suppression_applied / 
                               max(1, self.frames_processed))
        }


class EchoCanceller:
    """Main echo cancellation system combining delay estimation, adaptive filtering, and residual suppression."""
    
    def __init__(self,
                 mode: EchoCancellationMode = EchoCancellationMode.ADAPTIVE,
                 sample_rate: int = 16000,
                 frame_size: int = 480,
                 filter_length: int = 256):
        self.mode = mode
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        
        # Core components
        self.delay_estimator = DelayEstimator(sample_rate)
        self.adaptive_filter = AdaptiveFilter(filter_length)
        self.residual_suppressor = ResidualEchoSuppressor(frame_size)
        
        # Echo profile
        self.current_echo_profile: Optional[EchoProfile] = None
        
        # Processing state
        self.is_learning = True
        self.learning_frames = 0
        self.frames_for_learning = 50  # Learn for first 50 frames
        
        # Reference signal buffer (for delay compensation)
        self.reference_buffer = deque(maxlen=1000)  # ~62ms at 16kHz
        
        # Statistics
        self.frames_processed = 0
        self.echo_return_loss_sum = 0.0
        self.processing_times = deque(maxlen=100)
        
        # Thread safety
        self._lock = threading.Lock()
        
    def cancel_echo(self, microphone_signal: np.ndarray, 
                   reference_signal: np.ndarray,
                   return_metrics: bool = False) -> Union[np.ndarray, Tuple[np.ndarray, EchoMetrics]]:
        """Cancel echo from microphone signal using reference (speaker output)."""
        start_time = time.time()
        
        with self._lock:
            if self.mode == EchoCancellationMode.DISABLED:
                if return_metrics:
                    metrics = EchoMetrics()
                    return microphone_signal.copy(), metrics
                return microphone_signal.copy()
                
            # Buffer reference signal
            self.reference_buffer.extend(reference_signal)
            
            # Estimate delay if in learning phase
            if self.is_learning and len(self.reference_buffer) >= self.delay_estimator.max_delay_samples:
                delay, confidence = self.delay_estimator.estimate_delay(
                    np.array(list(self.reference_buffer)[-len(microphone_signal):]),
                    microphone_signal
                )
                self.learning_frames += 1
                
                if self.learning_frames >= self.frames_for_learning:
                    self.is_learning = False
                    logger.info(f"Echo cancellation learning complete. Delay: {delay} samples")
            
            # Get delayed reference signal
            delay_samples = self.delay_estimator.current_delay
            if len(self.reference_buffer) >= delay_samples + len(microphone_signal):
                ref_delayed = np.array(list(self.reference_buffer))[
                    -(len(microphone_signal) + delay_samples):-delay_samples if delay_samples > 0 else None
                ]
            else:
                ref_delayed = np.zeros_like(microphone_signal)
                
            # Adaptive filtering
            if self.mode in [EchoCancellationMode.ADAPTIVE, EchoCancellationMode.AGGRESSIVE]:
                adapt = not self.is_learning  # Only adapt after learning
                filtered_signal = self.adaptive_filter.filter_block(
                    ref_delayed, microphone_signal, adapt=adapt
                )
            else:  # BASIC mode
                # Simple fixed delay compensation
                if len(ref_delayed) == len(microphone_signal):
                    filtered_signal = microphone_signal - 0.3 * ref_delayed
                else:
                    filtered_signal = microphone_signal.copy()
                    
            # Residual echo suppression
            if self.mode == EchoCancellationMode.AGGRESSIVE:
                ref_level = np.mean(reference_signal ** 2) if len(reference_signal) > 0 else 0.0
                output_signal = self.residual_suppressor.suppress(filtered_signal, ref_level)
            else:
                output_signal = filtered_signal
                
            # Compute metrics
            processing_time = (time.time() - start_time) * 1000  # ms
            self.processing_times.append(processing_time)
            
            if return_metrics:
                metrics = self._compute_metrics(microphone_signal, output_signal, 
                                              reference_signal, processing_time)
            
            self.frames_processed += 1
            
            if return_metrics:
                return output_signal, metrics
            return output_signal
            
    def _compute_metrics(self, input_signal: np.ndarray, output_signal: np.ndarray,
                        reference_signal: np.ndarray, processing_time: float) -> EchoMetrics:
        """Compute echo cancellation performance metrics."""
        # Echo return loss (dB)
        input_power = np.mean(input_signal ** 2) + 1e-10
        output_power = np.mean(output_signal ** 2) + 1e-10
        echo_return_loss = 10 * np.log10(input_power / output_power)
        
        # Echo suppression (similar to return loss)
        echo_suppression = max(0, echo_return_loss)
        
        # Delay estimate
        delay_ms = self.delay_estimator.current_delay * 1000.0 / self.sample_rate
        
        # Filter convergence
        convergence = self.adaptive_filter.get_convergence()
        
        # Residual echo level
        residual_echo_db = 10 * np.log10(output_power + 1e-10)
        
        # Track statistics
        self.echo_return_loss_sum += echo_return_loss
        
        return EchoMetrics(
            echo_return_loss_db=echo_return_loss,
            echo_suppression_db=echo_suppression,
            delay_estimate_ms=delay_ms,
            filter_convergence=convergence,
            processing_latency_ms=processing_time,
            residual_echo_db=residual_echo_db
        )
        
    def set_mode(self, mode: EchoCancellationMode):
        """Set echo cancellation mode."""
        with self._lock:
            self.mode = mode
            if mode == EchoCancellationMode.DISABLED:
                self.adaptive_filter.is_adapting = False
            else:
                self.adaptive_filter.is_adapting = True
                
    def reset(self):
        """Reset echo cancellation state."""
        with self._lock:
            self.adaptive_filter.reset()
            self.delay_estimator.current_delay = 0
            self.delay_estimator.confidence = 0.0
            self.reference_buffer.clear()
            self.is_learning = True
            self.learning_frames = 0
            self.frames_processed = 0
            self.echo_return_loss_sum = 0.0
            self.processing_times.clear()
            
    def get_statistics(self) -> Dict:
        """Get comprehensive echo cancellation statistics."""
        with self._lock:
            delay_stats = self.delay_estimator.get_statistics()
            filter_stats = self.adaptive_filter.get_statistics()
            suppressor_stats = self.residual_suppressor.get_statistics()
            
            avg_processing_time = np.mean(self.processing_times) if self.processing_times else 0.0
            avg_echo_loss = (self.echo_return_loss_sum / max(1, self.frames_processed))
            
            return {
                "mode": self.mode.value,
                "frames_processed": self.frames_processed,
                "is_learning": self.is_learning,
                "learning_progress": min(1.0, self.learning_frames / self.frames_for_learning),
                "avg_echo_return_loss_db": avg_echo_loss,
                "avg_processing_time_ms": avg_processing_time,
                "delay_estimation": delay_stats,
                "adaptive_filter": filter_stats,
                "residual_suppressor": suppressor_stats
            }


class EchoCancellerPool:
    """Thread-safe pool of echo cancellers for different contexts."""
    
    def __init__(self):
        self.cancellers: Dict[str, EchoCanceller] = {}
        self.default_canceller = "main"
        self._lock = threading.Lock()
        
    def create_canceller(self, name: str, mode: EchoCancellationMode = EchoCancellationMode.ADAPTIVE,
                        **kwargs) -> EchoCanceller:
        """Create and register echo canceller."""
        with self._lock:
            canceller = EchoCanceller(mode=mode, **kwargs)
            self.cancellers[name] = canceller
            return canceller
            
    def get_canceller(self, name: Optional[str] = None) -> Optional[EchoCanceller]:
        """Get echo canceller by name."""
        with self._lock:
            if name is None:
                name = self.default_canceller
            return self.cancellers.get(name)
            
    def remove_canceller(self, name: str) -> bool:
        """Remove echo canceller."""
        with self._lock:
            if name in self.cancellers:
                del self.cancellers[name]
                return True
            return False
            
    def set_default(self, name: str):
        """Set default echo canceller."""
        with self._lock:
            if name in self.cancellers:
                self.default_canceller = name
                
    def reset_all(self):
        """Reset all echo cancellers."""
        with self._lock:
            for canceller in self.cancellers.values():
                canceller.reset()


# Global pool instance
_echo_canceller_pool: Optional[EchoCancellerPool] = None


def get_canceller_pool() -> EchoCancellerPool:
    """Get global echo canceller pool."""
    global _echo_canceller_pool
    if _echo_canceller_pool is None:
        _echo_canceller_pool = EchoCancellerPool()
    return _echo_canceller_pool


def create_canceller(name: str = "main", 
                    mode: EchoCancellationMode = EchoCancellationMode.ADAPTIVE,
                    **kwargs) -> EchoCanceller:
    """Create echo canceller in global pool."""
    pool = get_canceller_pool()
    return pool.create_canceller(name, mode, **kwargs)