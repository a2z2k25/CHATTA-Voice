#!/usr/bin/env python3
"""Adaptive silence detection for voice mode.

This module provides intelligent silence detection that adapts to:
- Environmental noise levels
- Speaker characteristics
- Conversation context
- Network conditions
"""

import time
import numpy as np
import logging
from typing import Optional, List, Dict, Any, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading

logger = logging.getLogger(__name__)

# Try to import webrtcvad for advanced VAD
try:
    import webrtcvad
    WEBRTC_VAD_AVAILABLE = True
except ImportError:
    WEBRTC_VAD_AVAILABLE = False
    logger.debug("WebRTC VAD not available, using fallback")


class SilenceDetectionMode(Enum):
    """Silence detection modes."""
    AGGRESSIVE = "aggressive"      # Quick to detect silence
    BALANCED = "balanced"          # Balanced detection
    PATIENT = "patient"            # Waits longer before detecting silence
    ADAPTIVE = "adaptive"          # Adapts based on context
    MANUAL = "manual"              # Manual thresholds


class ConversationPhase(Enum):
    """Conversation phases for adaptive detection."""
    INITIAL = "initial"            # Start of conversation
    ACTIVE = "active"              # Active speaking
    LISTENING = "listening"        # Listening phase
    THINKING = "thinking"          # Processing/thinking
    CONCLUDING = "concluding"      # End of conversation


@dataclass
class SilenceMetrics:
    """Metrics for silence detection."""
    duration: float = 0.0
    energy_level: float = 0.0
    zero_crossing_rate: float = 0.0
    spectral_centroid: float = 0.0
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AdaptiveThresholds:
    """Adaptive thresholds for silence detection."""
    energy_threshold: float = 0.01
    silence_duration: float = 0.8
    speech_duration: float = 0.2
    zero_crossing_threshold: float = 0.1
    confidence_threshold: float = 0.7
    
    def adapt(self, metrics: SilenceMetrics, phase: ConversationPhase):
        """Adapt thresholds based on metrics and phase."""
        # Adapt based on conversation phase
        if phase == ConversationPhase.INITIAL:
            # More patient at start
            self.silence_duration = 1.2
            self.speech_duration = 0.3
        elif phase == ConversationPhase.ACTIVE:
            # Quick detection during active conversation
            self.silence_duration = 0.6
            self.speech_duration = 0.15
        elif phase == ConversationPhase.THINKING:
            # Very patient during thinking
            self.silence_duration = 2.0
            self.speech_duration = 0.4
        elif phase == ConversationPhase.CONCLUDING:
            # Moderate patience at end
            self.silence_duration = 1.0
            self.speech_duration = 0.25
        
        # Adapt energy threshold based on noise floor
        if metrics.energy_level > 0:
            noise_factor = min(metrics.energy_level * 2, 0.5)
            self.energy_threshold = max(0.01, noise_factor)


class EnergyBasedDetector:
    """Energy-based silence detection."""
    
    def __init__(self, threshold: float = 0.01, window_size: int = 10):
        self.threshold = threshold
        self.window_size = window_size
        self.energy_history = deque(maxlen=window_size)
        self.noise_floor = 0.0
        self.calibrated = False
    
    def calibrate(self, audio_data: np.ndarray):
        """Calibrate noise floor from audio sample."""
        energy = np.sqrt(np.mean(audio_data ** 2))
        self.energy_history.append(energy)
        
        if len(self.energy_history) >= self.window_size:
            # Use 20th percentile as noise floor
            self.noise_floor = np.percentile(list(self.energy_history), 20)
            self.calibrated = True
            logger.debug(f"Calibrated noise floor: {self.noise_floor:.4f}")
    
    def detect(self, audio_data: np.ndarray) -> Tuple[bool, float]:
        """Detect silence based on energy."""
        # Calculate RMS energy
        energy = np.sqrt(np.mean(audio_data ** 2))
        self.energy_history.append(energy)
        
        # Dynamic threshold based on noise floor
        dynamic_threshold = max(
            self.threshold,
            self.noise_floor * 1.5 if self.calibrated else self.threshold
        )
        
        is_silent = energy < dynamic_threshold
        confidence = 1.0 - (energy / dynamic_threshold) if is_silent else energy / dynamic_threshold
        
        return is_silent, min(max(confidence, 0.0), 1.0)


class ZeroCrossingDetector:
    """Zero-crossing rate based detection."""
    
    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold
        self.zcr_history = deque(maxlen=10)
    
    def detect(self, audio_data: np.ndarray) -> Tuple[bool, float]:
        """Detect silence based on zero-crossing rate."""
        # Calculate zero-crossing rate
        signs = np.sign(audio_data)
        signs[signs == 0] = 1
        zero_crossings = np.sum(signs[:-1] != signs[1:])
        zcr = zero_crossings / len(audio_data)
        
        self.zcr_history.append(zcr)
        
        # High ZCR often indicates noise/unvoiced speech
        is_silent = zcr < self.threshold
        confidence = 1.0 - (zcr / self.threshold) if is_silent else zcr / self.threshold
        
        return is_silent, min(max(confidence, 0.0), 1.0)


class SpectralDetector:
    """Spectral feature based detection."""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.centroid_history = deque(maxlen=10)
        self.centroid_threshold = sample_rate * 0.2  # 20% of Nyquist
    
    def detect(self, audio_data: np.ndarray) -> Tuple[bool, float]:
        """Detect silence based on spectral features."""
        # Calculate spectral centroid using FFT
        fft = np.fft.rfft(audio_data)
        magnitude = np.abs(fft)
        
        # Avoid division by zero
        if np.sum(magnitude) == 0:
            return True, 1.0
        
        # Calculate spectral centroid
        freqs = np.fft.rfftfreq(len(audio_data), 1/self.sample_rate)
        centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
        
        self.centroid_history.append(centroid)
        
        # Low spectral centroid often indicates silence/low energy
        is_silent = centroid < self.centroid_threshold
        confidence = 1.0 - (centroid / self.centroid_threshold) if is_silent else 0.5
        
        return is_silent, min(max(confidence, 0.0), 1.0)


class WebRTCVADDetector:
    """WebRTC VAD based detection."""
    
    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000):
        if not WEBRTC_VAD_AVAILABLE:
            raise ImportError("WebRTC VAD not available")
        
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.frame_duration_ms = 30  # WebRTC VAD works with 10, 20, or 30ms frames
        self.frame_size = int(sample_rate * self.frame_duration_ms / 1000)
    
    def detect(self, audio_data: bytes) -> Tuple[bool, float]:
        """Detect speech using WebRTC VAD."""
        try:
            # WebRTC VAD returns True for speech, False for silence
            is_speech = self.vad.is_speech(audio_data, self.sample_rate)
            is_silent = not is_speech
            confidence = 0.9 if is_silent else 0.1  # High confidence in WebRTC VAD
            return is_silent, confidence
        except Exception as e:
            logger.warning(f"WebRTC VAD error: {e}")
            return False, 0.5


class AdaptiveSilenceDetector:
    """Adaptive silence detection system."""
    
    def __init__(
        self,
        mode: SilenceDetectionMode = SilenceDetectionMode.ADAPTIVE,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30
    ):
        self.mode = mode
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # Initialize detectors
        self.energy_detector = EnergyBasedDetector()
        self.zcr_detector = ZeroCrossingDetector()
        self.spectral_detector = SpectralDetector(sample_rate)
        
        # Try to initialize WebRTC VAD
        self.webrtc_detector = None
        if WEBRTC_VAD_AVAILABLE:
            try:
                aggressiveness = self._get_vad_aggressiveness()
                self.webrtc_detector = WebRTCVADDetector(aggressiveness, sample_rate)
            except Exception as e:
                logger.debug(f"WebRTC VAD initialization failed: {e}")
        
        # Adaptive components
        self.thresholds = AdaptiveThresholds()
        self.phase = ConversationPhase.INITIAL
        self.metrics_history = deque(maxlen=100)
        
        # State tracking
        self.silence_start_time = None
        self.speech_start_time = None
        self.last_detection_time = time.time()
        self.is_calibrating = True
        self.calibration_frames = 0
        
        # Statistics
        self.stats = {
            "total_frames": 0,
            "silent_frames": 0,
            "speech_frames": 0,
            "phase_changes": 0,
            "threshold_adaptations": 0
        }
    
    def _get_vad_aggressiveness(self) -> int:
        """Get VAD aggressiveness based on mode."""
        if self.mode == SilenceDetectionMode.AGGRESSIVE:
            return 3
        elif self.mode == SilenceDetectionMode.PATIENT:
            return 1
        else:
            return 2  # Balanced/Adaptive
    
    def set_phase(self, phase: ConversationPhase):
        """Set conversation phase."""
        if phase != self.phase:
            self.phase = phase
            self.stats["phase_changes"] += 1
            logger.debug(f"Phase changed to: {phase.value}")
    
    def process_frame(self, audio_data: np.ndarray) -> SilenceMetrics:
        """Process single audio frame."""
        metrics = SilenceMetrics()
        
        # Energy detection
        energy_silent, energy_conf = self.energy_detector.detect(audio_data)
        metrics.energy_level = np.sqrt(np.mean(audio_data ** 2))
        
        # Zero-crossing detection
        zcr_silent, zcr_conf = self.zcr_detector.detect(audio_data)
        metrics.zero_crossing_rate = zcr_conf
        
        # Spectral detection
        spectral_silent, spectral_conf = self.spectral_detector.detect(audio_data)
        metrics.spectral_centroid = spectral_conf
        
        # WebRTC VAD if available
        webrtc_silent = False
        webrtc_conf = 0.0
        if self.webrtc_detector and len(audio_data) == self.frame_size:
            try:
                # Convert to bytes for WebRTC VAD
                if audio_data.dtype == np.float32:
                    audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
                else:
                    audio_bytes = audio_data.astype(np.int16).tobytes()
                
                webrtc_silent, webrtc_conf = self.webrtc_detector.detect(audio_bytes)
            except Exception as e:
                logger.debug(f"WebRTC VAD processing error: {e}")
        
        # Combine detections based on mode
        if self.mode == SilenceDetectionMode.AGGRESSIVE:
            # Any detector indicating silence
            is_silent = energy_silent or zcr_silent
            metrics.confidence = max(energy_conf, zcr_conf)
        elif self.mode == SilenceDetectionMode.PATIENT:
            # All detectors must agree
            is_silent = energy_silent and zcr_silent
            metrics.confidence = min(energy_conf, zcr_conf)
        else:  # BALANCED or ADAPTIVE
            # Weighted combination
            weights = [0.4, 0.2, 0.2, 0.2]  # energy, zcr, spectral, webrtc
            votes = [energy_silent, zcr_silent, spectral_silent, webrtc_silent]
            confs = [energy_conf, zcr_conf, spectral_conf, webrtc_conf]
            
            weighted_vote = sum(w * v for w, v in zip(weights, votes))
            is_silent = weighted_vote > 0.5
            metrics.confidence = sum(w * c for w, c in zip(weights, confs))
        
        # Track timing
        current_time = time.time()
        if is_silent:
            if self.silence_start_time is None:
                self.silence_start_time = current_time
            metrics.duration = current_time - self.silence_start_time
        else:
            if self.speech_start_time is None:
                self.speech_start_time = current_time
            # Don't reset silence_start_time immediately - let higher level logic decide
        
        # Update statistics
        self.stats["total_frames"] += 1
        if is_silent:
            self.stats["silent_frames"] += 1
        else:
            self.stats["speech_frames"] += 1
        
        # Store metrics
        self.metrics_history.append(metrics)
        
        return metrics
    
    def detect_silence(
        self,
        audio_data: np.ndarray,
        return_metrics: bool = False
    ) -> Union[bool, Tuple[bool, SilenceMetrics]]:
        """Detect silence in audio data."""
        # Calibration phase
        if self.is_calibrating:
            self.energy_detector.calibrate(audio_data)
            self.calibration_frames += 1
            
            if self.calibration_frames >= 10:
                self.is_calibrating = False
                logger.debug("Calibration complete")
        
        # Process frame to get initial detection
        metrics = self.process_frame(audio_data)
        
        # Adapt thresholds if in adaptive mode
        if self.mode == SilenceDetectionMode.ADAPTIVE:
            self.thresholds.adapt(metrics, self.phase)
            self.stats["threshold_adaptations"] += 1
        
        # Check if we have ongoing silence that meets duration threshold
        current_time = time.time()
        if self.silence_start_time is not None:
            silence_duration = current_time - self.silence_start_time
            is_silent = silence_duration >= self.thresholds.silence_duration
            # Update metrics duration for consistency
            metrics.duration = silence_duration
        else:
            # No ongoing silence
            is_silent = False
        
        if return_metrics:
            return is_silent, metrics
        return is_silent
    
    def reset(self):
        """Reset detector state."""
        self.silence_start_time = None
        self.speech_start_time = None
        self.is_calibrating = True
        self.calibration_frames = 0
        self.phase = ConversationPhase.INITIAL
        
        # Reset detectors
        self.energy_detector = EnergyBasedDetector()
        self.zcr_detector = ZeroCrossingDetector()
        self.spectral_detector = SpectralDetector(self.sample_rate)
        
        # Clear history
        self.metrics_history.clear()
        
        logger.debug("Detector reset")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detection statistics."""
        stats = self.stats.copy()
        
        # Calculate ratios
        if stats["total_frames"] > 0:
            stats["silence_ratio"] = stats["silent_frames"] / stats["total_frames"]
            stats["speech_ratio"] = stats["speech_frames"] / stats["total_frames"]
        else:
            stats["silence_ratio"] = 0
            stats["speech_ratio"] = 0
        
        # Add current state
        stats["current_phase"] = self.phase.value
        stats["is_calibrating"] = self.is_calibrating
        stats["mode"] = self.mode.value
        
        # Add threshold info
        stats["thresholds"] = {
            "energy": self.thresholds.energy_threshold,
            "silence_duration": self.thresholds.silence_duration,
            "speech_duration": self.thresholds.speech_duration
        }
        
        return stats


class SilenceDetectorPool:
    """Pool of silence detectors for different contexts."""
    
    def __init__(self):
        self.detectors: Dict[str, AdaptiveSilenceDetector] = {}
        self.default_detector = "default"
        self.lock = threading.Lock()
    
    def create_detector(
        self,
        name: str,
        mode: SilenceDetectionMode = SilenceDetectionMode.ADAPTIVE,
        sample_rate: int = 16000
    ) -> AdaptiveSilenceDetector:
        """Create new detector."""
        with self.lock:
            detector = AdaptiveSilenceDetector(mode, sample_rate)
            self.detectors[name] = detector
            
            if len(self.detectors) == 1:
                self.default_detector = name
            
            logger.info(f"Created detector: {name} (mode={mode.value})")
            return detector
    
    def get_detector(self, name: Optional[str] = None) -> Optional[AdaptiveSilenceDetector]:
        """Get detector by name."""
        with self.lock:
            if name is None:
                name = self.default_detector
            return self.detectors.get(name)
    
    def remove_detector(self, name: str) -> bool:
        """Remove detector."""
        with self.lock:
            if name in self.detectors:
                del self.detectors[name]
                
                if self.default_detector == name:
                    self.default_detector = next(iter(self.detectors.keys()), "default")
                
                logger.info(f"Removed detector: {name}")
                return True
            return False
    
    def reset_all(self):
        """Reset all detectors."""
        with self.lock:
            for detector in self.detectors.values():
                detector.reset()
            logger.info("All detectors reset")


# Global detector pool
_detector_pool = SilenceDetectorPool()


def get_detector_pool() -> SilenceDetectorPool:
    """Get global detector pool."""
    return _detector_pool


def create_detector(
    name: str = "default",
    mode: SilenceDetectionMode = SilenceDetectionMode.ADAPTIVE,
    sample_rate: int = 16000
) -> AdaptiveSilenceDetector:
    """Create or get silence detector."""
    pool = get_detector_pool()
    
    # Check if exists
    detector = pool.get_detector(name)
    if detector is None:
        detector = pool.create_detector(name, mode, sample_rate)
    
    return detector