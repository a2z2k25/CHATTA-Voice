#!/usr/bin/env python3
"""Test audio quality enhancement system."""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.audio_enhancement import (
    EnhancementMode,
    CompressionType,
    EnhancementMetrics,
    AudioProfile,
    DynamicRangeCompressor,
    SpectralEnhancer,
    ParametricEqualizer,
    AudioEnhancer,
    AudioEnhancerPool,
    get_enhancer_pool,
    create_enhancer
)


def test_enhancement_metrics():
    """Test enhancement metrics creation."""
    print("\n=== Testing Enhancement Metrics ===")
    
    metrics = EnhancementMetrics(
        dynamic_range_db=8.5,
        peak_reduction_db=3.2,
        rms_level_db=2.1,
        spectral_clarity=0.85,
        processing_latency_ms=4.5,
        enhancement_applied=True
    )
    
    assert metrics.dynamic_range_db == 8.5
    assert metrics.peak_reduction_db == 3.2
    assert metrics.rms_level_db == 2.1
    assert metrics.spectral_clarity == 0.85
    assert metrics.processing_latency_ms == 4.5
    assert metrics.enhancement_applied == True
    assert metrics.timestamp > 0
    print("✓ Enhancement metrics creation working")


def test_audio_profile():
    """Test audio profile creation."""
    print("\n=== Testing Audio Profile ===")
    
    # Create basic audio profile
    freq_response = np.ones(240)  # 480//2
    profile = AudioProfile(
        frequency_response=freq_response,
        dynamic_range=20.0,
        peak_level=-6.0,
        rms_level=-20.0,
        spectral_centroid=1000.0,
        confidence=0.8
    )
    
    assert len(profile.frequency_response) == 240
    assert profile.dynamic_range == 20.0
    assert profile.peak_level == -6.0
    assert profile.rms_level == -20.0
    assert profile.spectral_centroid == 1000.0
    assert profile.confidence == 0.8
    assert profile.timestamp > 0
    print("✓ Audio profile creation working")


def test_dynamic_range_compressor():
    """Test dynamic range compression."""
    print("\n=== Testing Dynamic Range Compressor ===")
    
    compressor = DynamicRangeCompressor(compression_type=CompressionType.RMS_COMPRESSOR)
    
    # Test with loud signal
    loud_signal = np.sin(2 * np.pi * 440 * np.arange(480) / 16000) * 0.9
    compressed = compressor.compress(loud_signal)
    
    # Should reduce dynamic range
    input_rms = np.sqrt(np.mean(loud_signal ** 2))
    output_rms = np.sqrt(np.mean(compressed ** 2))
    compression_ratio = input_rms / output_rms
    
    print(f"Input RMS: {input_rms:.3f}")
    print(f"Output RMS: {output_rms:.3f}")
    print(f"Compression ratio: {compression_ratio:.2f}")
    
    assert len(compressed) == len(loud_signal)
    assert compression_ratio >= 1.0  # Should compress or maintain level
    print("✓ RMS compression working")
    
    # Test peak limiting
    peak_compressor = DynamicRangeCompressor(compression_type=CompressionType.PEAK_LIMITER)
    peak_limited = peak_compressor.compress(loud_signal)
    max_amplitude = np.max(np.abs(peak_limited))
    print(f"Peak limited max: {max_amplitude:.3f}")
    assert max_amplitude <= 1.0  # Should not exceed maximum
    print("✓ Peak limiting working")


def test_multiband_compression():
    """Test multiband compression."""
    print("\n=== Testing Multiband Compression ===")
    
    compressor = DynamicRangeCompressor(compression_type=CompressionType.MULTIBAND)
    
    # Create signal with multiple frequency components
    t = np.arange(480) / 16000
    signal = (
        np.sin(2 * np.pi * 200 * t) * 0.8 +  # Low frequency
        np.sin(2 * np.pi * 1000 * t) * 0.6 + # Mid frequency  
        np.sin(2 * np.pi * 4000 * t) * 0.4   # High frequency
    )
    
    # Apply multiband compression
    compressed = compressor.compress(signal)
    
    # Should preserve signal structure while controlling dynamics
    assert len(compressed) == len(signal)
    
    # Check that compression was applied
    input_peak = np.max(np.abs(signal))
    output_peak = np.max(np.abs(compressed))
    print(f"Input peak: {input_peak:.3f}")
    print(f"Output peak: {output_peak:.3f}")
    
    # Multiband should control peaks while preserving some dynamics
    assert output_peak <= input_peak
    print("✓ Multiband compression working")


def test_spectral_enhancer():
    """Test spectral enhancement."""
    print("\n=== Testing Spectral Enhancer ===")
    
    enhancer = SpectralEnhancer(frame_size=480, enhancement_factor=2.0)
    
    # Create voice-like signal (fundamental + harmonics)
    t = np.arange(480) / 16000
    fundamental = 200  # Hz
    voice_signal = (
        np.sin(2 * np.pi * fundamental * t) * 0.6 +     # Fundamental
        np.sin(2 * np.pi * fundamental * 2 * t) * 0.3 + # 2nd harmonic
        np.sin(2 * np.pi * fundamental * 3 * t) * 0.2   # 3rd harmonic
    )
    
    # Add some noise
    noisy_voice = voice_signal + np.random.randn(480) * 0.05
    
    # Enhance spectral clarity
    enhanced = enhancer.enhance(noisy_voice)
    
    assert len(enhanced) == len(noisy_voice)
    
    # Measure spectral enhancement effect
    # Enhanced signal should have better harmonic definition
    fft_original = np.abs(np.fft.fft(noisy_voice))
    fft_enhanced = np.abs(np.fft.fft(enhanced))
    
    # Check energy in voice band (100-1000 Hz)
    voice_bins = slice(int(100 * 480 / 16000), int(1000 * 480 / 16000))
    original_voice_energy = np.sum(fft_original[voice_bins])
    enhanced_voice_energy = np.sum(fft_enhanced[voice_bins])
    
    enhancement_ratio = enhanced_voice_energy / original_voice_energy
    print(f"Spectral enhancement ratio: {enhancement_ratio:.2f}")
    
    # Should enhance voice frequencies
    assert enhancement_ratio >= 0.8  # At least maintain energy
    print("✓ Spectral enhancement working")


def test_parametric_equalizer():
    """Test parametric equalizer."""
    print("\n=== Testing Parametric Equalizer ===")
    
    equalizer = ParametricEqualizer()
    
    # Test with default EQ settings
    test_signal = np.random.randn(480) * 0.5
    
    # Apply default EQ (voice-optimized)
    equalized = equalizer.equalize(test_signal)
    
    assert len(equalized) == len(test_signal)
    
    # Measure frequency response
    fft_original = np.abs(np.fft.fft(test_signal))
    fft_equalized = np.abs(np.fft.fft(equalized))
    
    # Check that EQ was applied
    total_original_energy = np.sum(fft_original)
    total_equalized_energy = np.sum(fft_equalized)
    
    eq_effect_ratio = total_equalized_energy / total_original_energy
    print(f"EQ effect ratio: {eq_effect_ratio:.3f}")
    
    # EQ should change frequency content
    assert eq_effect_ratio > 0.5  # Significant processing applied
    print("✓ Parametric equalizer working")
    
    # Test with no EQ bands
    flat_equalizer = ParametricEqualizer()
    flat_equalizer.bands = []  # Clear all bands
    flat_output = flat_equalizer.equalize(test_signal)
    
    # Should be very close to original
    difference = np.mean((flat_output - test_signal) ** 2)
    print(f"Flat EQ difference: {difference:.6f}")
    assert difference < 0.01  # Minimal processing artifacts
    print("✓ Flat EQ response working")


def test_audio_enhancer_disabled():
    """Test disabled enhancement mode."""
    print("\n=== Testing Disabled Enhancement Mode ===")
    
    enhancer = AudioEnhancer(mode=EnhancementMode.DISABLED)
    
    test_signal = np.random.randn(480) * 0.5
    output = enhancer.enhance_audio(test_signal)
    
    # Should return input unchanged
    np.testing.assert_array_almost_equal(output, test_signal, decimal=10)
    print("✓ Disabled mode returns input unchanged")


def test_audio_enhancer_subtle():
    """Test subtle enhancement mode."""
    print("\n=== Testing Subtle Enhancement Mode ===")
    
    enhancer = AudioEnhancer(mode=EnhancementMode.SUBTLE)
    
    # Create typical speech signal
    t = np.arange(480) / 16000
    speech_signal = (
        np.sin(2 * np.pi * 150 * t) * 0.4 +  # Low voice
        np.sin(2 * np.pi * 400 * t) * 0.3 +  # Mid voice
        np.random.randn(480) * 0.05          # Background noise
    )
    
    output, metrics = enhancer.enhance_audio(speech_signal, return_metrics=True)
    
    assert len(output) == len(speech_signal)
    assert isinstance(metrics, EnhancementMetrics)
    assert metrics.processing_latency_ms > 0
    
    # Should apply gentle enhancement
    assert not np.array_equal(output, speech_signal)
    print(f"Dynamic range: {metrics.dynamic_range_db:.2f} dB")
    print(f"Peak reduction: {metrics.peak_reduction_db:.2f} dB")
    print(f"Spectral clarity: {metrics.spectral_clarity:.2f}")
    print("✓ Subtle enhancement working")


def test_audio_enhancer_aggressive():
    """Test aggressive enhancement mode."""
    print("\n=== Testing Aggressive Enhancement Mode ===")
    
    enhancer = AudioEnhancer(mode=EnhancementMode.AGGRESSIVE)
    
    # Create signal with dynamics issues
    loud_speech = np.sin(2 * np.pi * 400 * np.arange(480) / 16000) * 0.9
    output, metrics = enhancer.enhance_audio(loud_speech, return_metrics=True)
    
    assert len(output) == len(loud_speech)
    
    # Should apply strong compression and enhancement
    input_peak = np.max(np.abs(loud_speech))
    output_peak = np.max(np.abs(output))
    
    print(f"Input peak: {input_peak:.3f}")
    print(f"Output peak: {output_peak:.3f}")
    print(f"Dynamic range: {metrics.dynamic_range_db:.2f} dB")
    
    # Aggressive mode should control peaks
    assert output_peak <= input_peak
    assert metrics.enhancement_applied  # Should have applied enhancement
    print("✓ Aggressive enhancement working")


def test_enhancement_modes():
    """Test all enhancement modes."""
    print("\n=== Testing All Enhancement Modes ===")
    
    modes = [
        EnhancementMode.DISABLED,
        EnhancementMode.SUBTLE,
        EnhancementMode.BALANCED,
        EnhancementMode.AGGRESSIVE
    ]
    
    test_signal = np.random.randn(480) * 0.6
    
    for mode in modes:
        enhancer = AudioEnhancer(mode=mode)
        output, metrics = enhancer.enhance_audio(test_signal, return_metrics=True)
        
        assert len(output) == len(test_signal)
        print(f"{mode.value}: latency = {metrics.processing_latency_ms:.2f} ms")
        
        if mode == EnhancementMode.DISABLED:
            np.testing.assert_array_almost_equal(output, test_signal, decimal=10)
        else:
            # Should apply some processing
            assert not np.array_equal(output, test_signal)
    
    print("✓ All enhancement modes working")


def test_custom_enhancement():
    """Test custom enhancement profile."""
    print("\n=== Testing Custom Enhancement ===")
    
    # Test custom enhancement mode
    enhancer = AudioEnhancer(mode=EnhancementMode.CUSTOM)
    
    # Test with music-like signal
    t = np.arange(480) / 16000
    complex_signal = (
        np.sin(2 * np.pi * 100 * t) * 0.6 +   # Bass
        np.sin(2 * np.pi * 500 * t) * 0.4 +   # Mid
        np.sin(2 * np.pi * 2000 * t) * 0.5 +  # Upper mid
        np.sin(2 * np.pi * 6000 * t) * 0.3    # High
    )
    
    output, metrics = enhancer.enhance_audio(complex_signal, return_metrics=True)
    
    assert len(output) == len(complex_signal)
    assert not np.array_equal(output, complex_signal)
    
    print(f"Custom enhancement applied:")
    print(f"  Dynamic range: {metrics.dynamic_range_db:.2f} dB")
    print(f"  Peak reduction: {metrics.peak_reduction_db:.2f} dB")
    print(f"  RMS level: {metrics.rms_level_db:.2f} dB")
    print(f"  Spectral clarity: {metrics.spectral_clarity:.2f}")
    print("✓ Custom enhancement working")


def test_enhancer_pool():
    """Test audio enhancer pool."""
    print("\n=== Testing Audio Enhancer Pool ===")
    
    pool = get_enhancer_pool()
    
    # Create enhancers
    enhancer1 = pool.create_enhancer("voice", EnhancementMode.BALANCED)
    enhancer2 = pool.create_enhancer("music", EnhancementMode.AGGRESSIVE)
    
    assert len(pool.enhancers) >= 2
    print(f"✓ Created {len(pool.enhancers)} enhancers")
    
    # Test retrieval
    retrieved = pool.get_enhancer("voice")
    assert retrieved is enhancer1
    assert retrieved.mode == EnhancementMode.BALANCED
    print("✓ Enhancer retrieval working")
    
    # Test default
    pool.set_default("music")
    assert pool.default_enhancer == "music"
    default = pool.get_enhancer()  # Should get music enhancer
    assert default is enhancer2
    print("✓ Default enhancer working")
    
    # Test reset
    pool.reset_all()
    print("✓ Pool reset working")
    
    # Clean up
    pool.remove_enhancer("voice")
    pool.remove_enhancer("music")


def test_performance_metrics():
    """Test performance and timing."""
    print("\n=== Testing Performance Metrics ===")
    
    enhancer = AudioEnhancer(mode=EnhancementMode.BALANCED)
    
    # Test performance with realistic signal
    speech_signal = np.random.randn(480) * 0.4
    
    latencies = []
    for _ in range(50):
        start_time = time.time()
        output, metrics = enhancer.enhance_audio(speech_signal, return_metrics=True)
        processing_time = (time.time() - start_time) * 1000  # ms
        latencies.append(processing_time)
    
    avg_latency = np.mean(latencies)
    max_latency = np.max(latencies)
    
    print(f"Average latency: {avg_latency:.2f} ms")
    print(f"Maximum latency: {max_latency:.2f} ms")
    
    # Performance expectations for audio enhancement
    assert avg_latency < 10.0  # Should be under 10ms on average
    print("✓ Performance acceptable")


def test_enhancement_effectiveness():
    """Test actual enhancement effectiveness."""
    print("\n=== Testing Enhancement Effectiveness ===")
    
    enhancer = AudioEnhancer(mode=EnhancementMode.AGGRESSIVE)
    
    # Create problematic audio scenario
    # Quiet speech with loud peaks and frequency imbalance
    t = np.arange(480) / 16000
    quiet_speech = np.sin(2 * np.pi * 300 * t) * 0.2  # Very quiet
    loud_peaks = np.zeros(480)
    loud_peaks[100:110] = 0.9  # Brief loud peak
    frequency_imbalanced = (
        np.sin(2 * np.pi * 100 * t) * 0.1 +   # Too much bass
        np.sin(2 * np.pi * 5000 * t) * 0.3    # Too much treble
    )
    
    problematic_audio = quiet_speech + loud_peaks + frequency_imbalanced
    
    # Enhance the problematic audio
    enhanced, metrics = enhancer.enhance_audio(problematic_audio, return_metrics=True)
    
    # Measure improvements
    input_dynamic_range = np.max(np.abs(problematic_audio)) / (np.std(problematic_audio) + 1e-6)
    output_dynamic_range = np.max(np.abs(enhanced)) / (np.std(enhanced) + 1e-6)
    
    dynamic_range_improvement = input_dynamic_range / output_dynamic_range
    
    print(f"Dynamic range improvement: {dynamic_range_improvement:.2f}x")
    print(f"Enhancement metrics:")
    print(f"  Dynamic range: {metrics.dynamic_range_db:.2f} dB")
    print(f"  Peak reduction: {metrics.peak_reduction_db:.2f} dB")
    print(f"  RMS level: {metrics.rms_level_db:.2f} dB")
    print(f"  Spectral clarity: {metrics.spectral_clarity:.2f}")
    
    # Should improve dynamic range control
    assert dynamic_range_improvement > 1.1  # At least 10% improvement
    assert metrics.enhancement_applied  # Should have applied enhancement
    print("✓ Enhancement effectiveness verified")


def test_signal_preservation():
    """Test that enhancement preserves important signal characteristics."""
    print("\n=== Testing Signal Preservation ===")
    
    enhancer = AudioEnhancer(mode=EnhancementMode.BALANCED)
    
    # Create clean speech signal
    t = np.arange(480) / 16000
    clean_speech = np.sin(2 * np.pi * 400 * t) * 0.5  # Clear 400 Hz tone
    
    enhanced = enhancer.enhance_audio(clean_speech)
    
    # Should preserve fundamental characteristics
    # Check that the dominant frequency is maintained
    fft_original = np.abs(np.fft.fft(clean_speech))
    fft_enhanced = np.abs(np.fft.fft(enhanced))
    
    # Find peak frequencies
    original_peak_bin = np.argmax(fft_original[:240])  # First half of spectrum
    enhanced_peak_bin = np.argmax(fft_enhanced[:240])
    
    bin_difference = abs(original_peak_bin - enhanced_peak_bin)
    
    print(f"Original peak bin: {original_peak_bin} (~{original_peak_bin * 16000 / 480:.0f} Hz)")
    print(f"Enhanced peak bin: {enhanced_peak_bin} (~{enhanced_peak_bin * 16000 / 480:.0f} Hz)")
    print(f"Bin difference: {bin_difference}")
    
    # Should preserve fundamental frequency (within 2 bins tolerance)
    assert bin_difference <= 2
    print("✓ Signal characteristics preserved")


def main():
    """Run all tests."""
    print("=" * 60)
    print("AUDIO QUALITY ENHANCEMENT TESTS")
    print("=" * 60)
    
    test_enhancement_metrics()
    test_audio_profile()
    test_dynamic_range_compressor()
    test_multiband_compression()
    test_spectral_enhancer()
    test_parametric_equalizer()
    test_audio_enhancer_disabled()
    test_audio_enhancer_subtle()
    test_audio_enhancer_aggressive()
    test_enhancement_modes()
    test_custom_enhancement()
    test_enhancer_pool()
    test_performance_metrics()
    test_enhancement_effectiveness()
    test_signal_preservation()
    
    print("\n" + "=" * 60)
    print("✓ All audio enhancement tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    main()