"""
Audio tone generation for PTT feedback.

Generates simple audio tones for PTT events without requiring
external audio files. Uses numpy to generate pure tones.
"""

import numpy as np
from typing import Tuple, Optional


def generate_sine_wave(
    frequency: float,
    duration: float,
    sample_rate: int = 44100,
    amplitude: float = 0.5
) -> np.ndarray:
    """
    Generate a sine wave tone.

    Args:
        frequency: Frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate (default: 44100 Hz)
        amplitude: Amplitude 0.0-1.0 (default: 0.5)

    Returns:
        Audio samples as int16 numpy array
    """
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)
    wave = amplitude * np.sin(2 * np.pi * frequency * t)

    # Convert to int16
    wave_int16 = (wave * 32767).astype(np.int16)

    return wave_int16


def generate_multi_tone(
    frequencies: list,
    duration: float,
    sample_rate: int = 44100,
    amplitude: float = 0.5
) -> np.ndarray:
    """
    Generate a multi-tone chord.

    Args:
        frequencies: List of frequencies in Hz
        duration: Duration in seconds
        sample_rate: Sample rate
        amplitude: Amplitude per tone (will be normalized)

    Returns:
        Audio samples as int16 numpy array
    """
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    # Generate and sum all tones
    wave = np.zeros(samples)
    for freq in frequencies:
        wave += (amplitude / len(frequencies)) * np.sin(2 * np.pi * freq * t)

    # Normalize to prevent clipping
    if np.max(np.abs(wave)) > 0:
        wave = wave / np.max(np.abs(wave)) * amplitude

    # Convert to int16
    wave_int16 = (wave * 32767).astype(np.int16)

    return wave_int16


def apply_fade(
    audio: np.ndarray,
    fade_in: float = 0.01,
    fade_out: float = 0.01,
    sample_rate: int = 44100
) -> np.ndarray:
    """
    Apply fade in/out to audio to prevent clicks.

    Args:
        audio: Audio samples
        fade_in: Fade in duration in seconds
        fade_out: Fade out duration in seconds
        sample_rate: Sample rate

    Returns:
        Audio with fades applied
    """
    audio = audio.copy()
    samples = len(audio)

    # Fade in
    fade_in_samples = int(fade_in * sample_rate)
    if fade_in_samples > 0:
        fade_in_curve = np.linspace(0, 1, min(fade_in_samples, samples))
        audio[:len(fade_in_curve)] = audio[:len(fade_in_curve)] * fade_in_curve

    # Fade out
    fade_out_samples = int(fade_out * sample_rate)
    if fade_out_samples > 0:
        fade_out_curve = np.linspace(1, 0, min(fade_out_samples, samples))
        audio[-len(fade_out_curve):] = audio[-len(fade_out_curve):] * fade_out_curve

    return audio


def generate_beep(
    frequency: float = 800,
    duration: float = 0.1,
    amplitude: float = 0.5,
    sample_rate: int = 44100
) -> np.ndarray:
    """
    Generate a simple beep tone.

    Args:
        frequency: Beep frequency (default: 800 Hz)
        duration: Duration in seconds (default: 0.1s)
        amplitude: Volume 0.0-1.0 (default: 0.5)
        sample_rate: Sample rate

    Returns:
        Beep audio samples
    """
    beep = generate_sine_wave(frequency, duration, sample_rate, amplitude)
    beep = apply_fade(beep, 0.005, 0.005, sample_rate)
    return beep


def generate_double_beep(
    frequency: float = 800,
    duration: float = 0.08,
    gap: float = 0.05,
    amplitude: float = 0.5,
    sample_rate: int = 44100
) -> np.ndarray:
    """
    Generate a double beep (beep-beep).

    Args:
        frequency: Beep frequency
        duration: Duration of each beep
        gap: Gap between beeps in seconds
        amplitude: Volume 0.0-1.0
        sample_rate: Sample rate

    Returns:
        Double beep audio samples
    """
    beep1 = generate_beep(frequency, duration, amplitude, sample_rate)
    gap_samples = np.zeros(int(gap * sample_rate), dtype=np.int16)
    beep2 = generate_beep(frequency, duration, amplitude, sample_rate)

    return np.concatenate([beep1, gap_samples, beep2])


def generate_ascending_tone(
    start_freq: float = 400,
    end_freq: float = 800,
    duration: float = 0.2,
    amplitude: float = 0.5,
    sample_rate: int = 44100
) -> np.ndarray:
    """
    Generate an ascending tone (frequency sweep up).

    Args:
        start_freq: Starting frequency in Hz
        end_freq: Ending frequency in Hz
        duration: Duration in seconds
        amplitude: Volume 0.0-1.0
        sample_rate: Sample rate

    Returns:
        Ascending tone audio samples
    """
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    # Frequency sweep (linear)
    freq_sweep = np.linspace(start_freq, end_freq, samples)

    # Generate tone with varying frequency
    phase = np.cumsum(freq_sweep) / sample_rate
    wave = amplitude * np.sin(2 * np.pi * phase)

    # Apply fade
    wave_int16 = (wave * 32767).astype(np.int16)
    wave_int16 = apply_fade(wave_int16, 0.01, 0.02, sample_rate)

    return wave_int16


def generate_descending_tone(
    start_freq: float = 800,
    end_freq: float = 400,
    duration: float = 0.2,
    amplitude: float = 0.5,
    sample_rate: int = 44100
) -> np.ndarray:
    """
    Generate a descending tone (frequency sweep down).

    Args:
        start_freq: Starting frequency in Hz
        end_freq: Ending frequency in Hz
        duration: Duration in seconds
        amplitude: Volume 0.0-1.0
        sample_rate: Sample rate

    Returns:
        Descending tone audio samples
    """
    return generate_ascending_tone(start_freq, end_freq, duration, amplitude, sample_rate)


def generate_chord(
    root_freq: float = 440,
    chord_type: str = "major",
    duration: float = 0.15,
    amplitude: float = 0.5,
    sample_rate: int = 44100
) -> np.ndarray:
    """
    Generate a musical chord.

    Args:
        root_freq: Root frequency in Hz (default: A440)
        chord_type: "major", "minor", or "perfect_fifth"
        duration: Duration in seconds
        amplitude: Volume 0.0-1.0
        sample_rate: Sample rate

    Returns:
        Chord audio samples
    """
    # Define chord intervals (in semitones from root)
    intervals = {
        "major": [0, 4, 7],           # Major triad
        "minor": [0, 3, 7],           # Minor triad
        "perfect_fifth": [0, 7],      # Perfect fifth (power chord)
        "octave": [0, 12],            # Octave
    }

    if chord_type not in intervals:
        chord_type = "major"

    # Calculate frequencies
    semitone_ratio = 2 ** (1/12)
    frequencies = [root_freq * (semitone_ratio ** interval) for interval in intervals[chord_type]]

    # Generate chord
    chord = generate_multi_tone(frequencies, duration, sample_rate, amplitude)
    chord = apply_fade(chord, 0.01, 0.02, sample_rate)

    return chord


# Preset tones for PTT events
def ptt_start_tone(amplitude: float = 0.5, sample_rate: int = 44100) -> np.ndarray:
    """
    Generate PTT recording start tone.

    Ascending major chord - positive, "let's go" feeling.

    Args:
        amplitude: Volume 0.0-1.0
        sample_rate: Sample rate

    Returns:
        Start tone audio samples
    """
    return generate_ascending_tone(
        start_freq=523,  # C5
        end_freq=784,    # G5
        duration=0.15,
        amplitude=amplitude,
        sample_rate=sample_rate
    )


def ptt_stop_tone(amplitude: float = 0.5, sample_rate: int = 44100) -> np.ndarray:
    """
    Generate PTT recording stop tone.

    Descending tone - "completion" feeling.

    Args:
        amplitude: Volume 0.0-1.0
        sample_rate: Sample rate

    Returns:
        Stop tone audio samples
    """
    return generate_descending_tone(
        start_freq=784,  # G5
        end_freq=523,    # C5
        duration=0.15,
        amplitude=amplitude,
        sample_rate=sample_rate
    )


def ptt_cancel_tone(amplitude: float = 0.5, sample_rate: int = 44100) -> np.ndarray:
    """
    Generate PTT recording cancel tone.

    Double descending beep - "cancelled" feeling.

    Args:
        amplitude: Volume 0.0-1.0
        sample_rate: Sample rate

    Returns:
        Cancel tone audio samples
    """
    beep1 = generate_descending_tone(600, 400, 0.08, amplitude, sample_rate)
    gap = np.zeros(int(0.05 * sample_rate), dtype=np.int16)
    beep2 = generate_descending_tone(500, 300, 0.08, amplitude, sample_rate)

    return np.concatenate([beep1, gap, beep2])


def ptt_waiting_tone(amplitude: float = 0.5, sample_rate: int = 44100) -> np.ndarray:
    """
    Generate PTT waiting/ready tone.

    Soft single beep - "ready" feeling.

    Args:
        amplitude: Volume 0.0-1.0
        sample_rate: Sample rate

    Returns:
        Waiting tone audio samples
    """
    return generate_beep(
        frequency=440,  # A4
        duration=0.1,
        amplitude=amplitude * 0.7,  # Slightly quieter
        sample_rate=sample_rate
    )


def ptt_error_tone(amplitude: float = 0.5, sample_rate: int = 44100) -> np.ndarray:
    """
    Generate PTT error tone.

    Triple low beep - "error/warning" feeling.

    Args:
        amplitude: Volume 0.0-1.0
        sample_rate: Sample rate

    Returns:
        Error tone audio samples
    """
    beep1 = generate_beep(300, 0.1, amplitude, sample_rate)
    gap = np.zeros(int(0.08 * sample_rate), dtype=np.int16)
    beep2 = generate_beep(300, 0.1, amplitude, sample_rate)
    gap2 = np.zeros(int(0.08 * sample_rate), dtype=np.int16)
    beep3 = generate_beep(300, 0.1, amplitude, sample_rate)

    return np.concatenate([beep1, gap, beep2, gap2, beep3])
