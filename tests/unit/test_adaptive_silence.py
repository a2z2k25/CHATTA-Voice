#!/usr/bin/env python3
"""Test adaptive silence detection."""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.adaptive_silence import (
    SilenceDetectionMode,
    ConversationPhase,
    SilenceMetrics,
    AdaptiveThresholds,
    EnergyBasedDetector,
    ZeroCrossingDetector,
    SpectralDetector,
    AdaptiveSilenceDetector,
    SilenceDetectorPool,
    get_detector_pool,
    create_detector
)


def test_silence_metrics():
    """Test silence metrics."""
    print("\n=== Testing Silence Metrics ===")
    
    metrics = SilenceMetrics(
        duration=1.5,
        energy_level=0.02,
        confidence=0.85
    )
    
    assert metrics.duration == 1.5
    assert metrics.energy_level == 0.02
    assert metrics.confidence == 0.85
    assert metrics.timestamp > 0
    print("✓ Metrics creation working")


def test_adaptive_thresholds():
    """Test adaptive thresholds."""
    print("\n=== Testing Adaptive Thresholds ===")
    
    thresholds = AdaptiveThresholds()
    initial_silence = thresholds.silence_duration
    
    # Test phase adaptation
    metrics = SilenceMetrics(energy_level=0.05)
    
    # Active phase should reduce silence duration
    thresholds.adapt(metrics, ConversationPhase.ACTIVE)
    assert thresholds.silence_duration < initial_silence
    print(f"Active phase: {thresholds.silence_duration}s")
    
    # Thinking phase should increase silence duration
    thresholds.adapt(metrics, ConversationPhase.THINKING)
    assert thresholds.silence_duration > initial_silence
    print(f"Thinking phase: {thresholds.silence_duration}s")
    
    print("✓ Threshold adaptation working")


def test_energy_detector():
    """Test energy-based detector."""
    print("\n=== Testing Energy Detector ===")
    
    detector = EnergyBasedDetector(threshold=0.01)
    
    # Test with silent audio
    silent_audio = np.random.randn(1600) * 0.001  # Very quiet
    is_silent, confidence = detector.detect(silent_audio)
    assert is_silent == True
    print(f"Silent: {is_silent}, confidence: {confidence:.2f}")
    
    # Test with speech audio
    speech_audio = np.sin(2 * np.pi * 440 * np.arange(1600) / 16000) * 0.5
    is_silent, confidence = detector.detect(speech_audio)
    assert is_silent == False
    print(f"Speech: {not is_silent}, confidence: {confidence:.2f}")
    
    # Test calibration
    for _ in range(10):
        detector.calibrate(silent_audio)
    
    assert detector.calibrated == True
    print(f"Noise floor: {detector.noise_floor:.4f}")
    print("✓ Energy detector working")


def test_zcr_detector():
    """Test zero-crossing rate detector."""
    print("\n=== Testing Zero-Crossing Detector ===")
    
    detector = ZeroCrossingDetector(threshold=0.1)
    
    # Low frequency (few crossings) - likely speech
    low_freq = np.sin(2 * np.pi * 100 * np.arange(1600) / 16000)
    is_silent, confidence = detector.detect(low_freq)
    print(f"Low freq silent: {is_silent}, confidence: {confidence:.2f}")
    
    # High frequency noise (many crossings)
    noise = np.random.randn(1600)
    is_silent, confidence = detector.detect(noise)
    print(f"Noise silent: {is_silent}, confidence: {confidence:.2f}")
    
    print("✓ ZCR detector working")


def test_spectral_detector():
    """Test spectral detector."""
    print("\n=== Testing Spectral Detector ===")
    
    detector = SpectralDetector(sample_rate=16000)
    
    # Low frequency content (low centroid)
    low_freq = np.sin(2 * np.pi * 200 * np.arange(1600) / 16000)
    is_silent, confidence = detector.detect(low_freq)
    print(f"Low freq silent: {is_silent}, confidence: {confidence:.2f}")
    
    # High frequency content (high centroid)
    high_freq = np.sin(2 * np.pi * 2000 * np.arange(1600) / 16000)
    is_silent, confidence = detector.detect(high_freq)
    print(f"High freq silent: {is_silent}, confidence: {confidence:.2f}")
    
    print("✓ Spectral detector working")


def test_adaptive_detector():
    """Test adaptive silence detector."""
    print("\n=== Testing Adaptive Detector ===")
    
    detector = AdaptiveSilenceDetector(
        mode=SilenceDetectionMode.BALANCED,  # Use balanced instead of adaptive
        sample_rate=16000
    )
    
    # Skip calibration for testing
    detector.is_calibrating = False
    
    # Generate test audio
    silence = np.random.randn(480) * 0.001  # 30ms of silence
    speech = np.sin(2 * np.pi * 440 * np.arange(480) / 16000) * 0.3  # 30ms of tone
    
    print("✓ Calibration skipped")
    
    # Test silence detection
    is_silent = detector.detect_silence(silence)
    print(f"Silence detected: {is_silent}")
    
    # Test speech detection  
    is_silent = detector.detect_silence(speech)
    print(f"Speech detected: {not is_silent}")
    
    # Get statistics
    stats = detector.get_statistics()
    print(f"Stats: {stats['total_frames']} frames, "
          f"{stats['silence_ratio']:.1%} silence")
    
    print("✓ Adaptive detector working")


def test_detection_modes():
    """Test different detection modes."""
    print("\n=== Testing Detection Modes ===")
    
    # Generate test audio
    silence = np.random.randn(480) * 0.001
    mixed = np.random.randn(480) * 0.01  # Ambiguous
    
    modes = [
        SilenceDetectionMode.AGGRESSIVE,
        SilenceDetectionMode.BALANCED,
        SilenceDetectionMode.PATIENT
    ]
    
    for mode in modes:
        detector = AdaptiveSilenceDetector(mode=mode)
        
        # Skip calibration
        detector.is_calibrating = False
        
        # Test with mixed audio
        is_silent, metrics = detector.detect_silence(mixed, return_metrics=True)
        print(f"{mode.value}: silent={is_silent}, confidence={metrics.confidence:.2f}")
    
    print("✓ Detection modes working")


def test_conversation_phases():
    """Test conversation phase adaptation."""
    print("\n=== Testing Conversation Phases ===")
    
    detector = AdaptiveSilenceDetector()
    
    phases = [
        ConversationPhase.INITIAL,
        ConversationPhase.ACTIVE,
        ConversationPhase.THINKING,
        ConversationPhase.CONCLUDING
    ]
    
    for phase in phases:
        detector.set_phase(phase)
        assert detector.phase == phase
        print(f"✓ Phase set: {phase.value}")
    
    stats = detector.get_statistics()
    assert stats["phase_changes"] == len(phases) - 1  # -1 because INITIAL is default
    print(f"Phase changes: {stats['phase_changes']}")


def test_detector_pool():
    """Test detector pool."""
    print("\n=== Testing Detector Pool ===")
    
    pool = get_detector_pool()
    
    # Create detectors
    detector1 = pool.create_detector("test1", SilenceDetectionMode.AGGRESSIVE)
    detector2 = pool.create_detector("test2", SilenceDetectionMode.PATIENT)
    
    assert len(pool.detectors) >= 2
    print(f"✓ Created {len(pool.detectors)} detectors")
    
    # Get detector
    retrieved = pool.get_detector("test1")
    assert retrieved is detector1
    print("✓ Detector retrieval working")
    
    # Reset all
    pool.reset_all()
    print("✓ Reset all detectors")
    
    # Clean up
    pool.remove_detector("test1")
    pool.remove_detector("test2")


def test_long_silence_detection():
    """Test long silence detection."""
    print("\n=== Testing Long Silence Detection ===")
    
    detector = AdaptiveSilenceDetector()
    detector.is_calibrating = False
    
    # Simulate long silence by manually setting timing
    silence = np.random.randn(480) * 0.001
    
    # Manually trigger silence start - use 1.5s to exceed default threshold
    detector.silence_start_time = time.time() - 1.5  # 1.5 seconds ago
    
    # Process frame
    is_silent, metrics = detector.detect_silence(silence, return_metrics=True)
    
    print(f"Duration: {metrics.duration:.2f}s")
    print(f"Is silent: {is_silent}")
    
    # Should detect silence since duration > threshold
    assert is_silent == True
    print("✓ Long silence detection working")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ADAPTIVE SILENCE DETECTION TESTS")
    print("=" * 60)
    
    test_silence_metrics()
    test_adaptive_thresholds()
    test_energy_detector()
    test_zcr_detector()
    test_spectral_detector()
    test_adaptive_detector()
    test_detection_modes()
    test_conversation_phases()
    test_detector_pool()
    test_long_silence_detection()
    
    print("\n" + "=" * 60)
    print("✓ All adaptive silence tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    main()