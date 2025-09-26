#!/usr/bin/env python3
"""Generate and save chime audio files"""

import sys
import os
import numpy as np
from scipy.io.wavfile import write

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.config import SAMPLE_RATE

def generate_chime(
    frequencies: list, 
    duration: float = 0.1, 
    sample_rate: int = SAMPLE_RATE,
    leading_silence: float = 0.1,  # Shorter for pre-generated files
    trailing_silence: float = 0.1
) -> np.ndarray:
    """Generate a chime sound with given frequencies."""
    samples_per_tone = int(sample_rate * duration)
    fade_samples = int(sample_rate * 0.01)  # 10ms fade
    
    # Use moderate amplitude for pre-generated files
    amplitude = 0.15
    
    all_samples = []
    
    for freq in frequencies:
        # Generate sine wave
        t = np.linspace(0, duration, samples_per_tone, False)
        tone = amplitude * np.sin(2 * np.pi * freq * t)
        
        # Apply fade in/out to prevent clicks
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        
        tone[:fade_samples] *= fade_in
        tone[-fade_samples:] *= fade_out
        
        all_samples.append(tone)
    
    # Concatenate all tones
    chime = np.concatenate(all_samples)
    
    # Add silence padding
    silence_samples = int(sample_rate * leading_silence)
    silence = np.zeros(silence_samples)
    
    trailing_samples = int(sample_rate * trailing_silence)
    trailing_silence = np.zeros(trailing_samples)
    
    # Combine: leading silence + chime + trailing silence
    chime_with_buffer = np.concatenate([silence, chime, trailing_silence])
    
    # Convert to 16-bit integer
    chime_int16 = (chime_with_buffer * 32767).astype(np.int16)
    
    return chime_int16

def main():
    """Generate and save chime files"""
    print("Generating chime audio files...")
    
    # Create audio directory
    audio_dir = "voice_mode/audio"
    os.makedirs(audio_dir, exist_ok=True)
    
    # Generate start chime (ascending tones)
    print("Generating start chime (ascending: 800Hz → 1000Hz)...")
    start_chime = generate_chime([800, 1000])
    start_file = os.path.join(audio_dir, "start_chime.wav")
    write(start_file, SAMPLE_RATE, start_chime)
    print(f"✅ Saved: {start_file}")
    
    # Generate end chime (descending tones)
    print("Generating end chime (descending: 1000Hz → 800Hz)...")
    end_chime = generate_chime([1000, 800])
    end_file = os.path.join(audio_dir, "end_chime.wav")
    write(end_file, SAMPLE_RATE, end_chime)
    print(f"✅ Saved: {end_file}")
    
    # Generate alternate versions with longer silence for Bluetooth
    print("\nGenerating Bluetooth-friendly versions with longer silence...")
    
    # Bluetooth start chime
    bt_start_chime = generate_chime([800, 1000], leading_silence=1.0, trailing_silence=0.5)
    bt_start_file = os.path.join(audio_dir, "start_chime_bluetooth.wav")
    write(bt_start_file, SAMPLE_RATE, bt_start_chime)
    print(f"✅ Saved: {bt_start_file}")
    
    # Bluetooth end chime
    bt_end_chime = generate_chime([1000, 800], leading_silence=1.0, trailing_silence=0.5)
    bt_end_file = os.path.join(audio_dir, "end_chime_bluetooth.wav")
    write(bt_end_file, SAMPLE_RATE, bt_end_chime)
    print(f"✅ Saved: {bt_end_file}")
    
    print("\n✅ All chime files generated successfully!")
    print("\nFiles created:")
    print("  - start_chime.wav (standard)")
    print("  - end_chime.wav (standard)")
    print("  - start_chime_bluetooth.wav (with extra silence)")
    print("  - end_chime_bluetooth.wav (with extra silence)")

if __name__ == "__main__":
    main()