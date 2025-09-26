#!/usr/bin/env python3
"""
Test microphone input and recording
"""
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os
import time

print("="*60)
print("🎤 Microphone Test")
print("="*60)

# List audio devices
print("\n📊 Available Audio Devices:")
devices = sd.query_devices()
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        default = " (DEFAULT)" if i == sd.default.device[0] else ""
        print(f"   [{i}] {device['name']} - {device['max_input_channels']} channels{default}")

# Get default input device
default_device = sd.default.device[0]
print(f"\n🎤 Using device [{default_device}]: {devices[default_device]['name']}")

# Test recording
sample_rate = 16000
duration = 3

print(f"\n📍 Test 1: Recording {duration} seconds of audio...")
print("   SPEAK NOW!")

try:
    # Record audio
    recording = sd.rec(int(duration * sample_rate), 
                      samplerate=sample_rate, 
                      channels=1, 
                      dtype='float32')
    sd.wait()  # Wait for recording to complete
    
    print("   ✅ Recording complete")
    
    # Check if we got any sound
    max_amplitude = np.max(np.abs(recording))
    avg_amplitude = np.mean(np.abs(recording))
    
    print(f"\n📊 Audio Statistics:")
    print(f"   Max amplitude: {max_amplitude:.4f}")
    print(f"   Avg amplitude: {avg_amplitude:.6f}")
    
    if max_amplitude < 0.001:
        print("   ⚠️  WARNING: No audio detected! Microphone may not be working.")
        print("\n🔧 Troubleshooting:")
        print("   1. Check System Settings > Security & Privacy > Microphone")
        print("   2. Make sure Terminal/Python has microphone access")
        print("   3. Try a different microphone if available")
    else:
        print("   ✅ Audio detected successfully!")
        
        # Save to file for testing with Whisper
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav.write(f.name, sample_rate, (recording * 32767).astype(np.int16))
            audio_file = f.name
        
        print(f"\n📍 Test 2: Sending to Whisper STT...")
        
        # Test with Whisper
        import requests
        
        with open(audio_file, 'rb') as f:
            files = {'file': ('test.wav', f, 'audio/wav')}
            data = {'model': 'whisper-1'}
            
            try:
                response = requests.post(
                    'http://localhost:8880/v1/audio/transcriptions',
                    files=files,
                    data=data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    text = response.json().get('text', '').strip()
                    if text:
                        print(f"   📝 Whisper heard: '{text}'")
                        print("   ✅ Microphone and STT working!")
                    else:
                        print("   ⚠️  Whisper returned empty transcription")
                        print("   Try speaking louder or clearer")
                else:
                    print(f"   ❌ Whisper error: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Whisper connection error: {e}")
        
        # Clean up
        os.remove(audio_file)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\n🔧 This might mean:")
    print("   - Python doesn't have microphone permission")
    print("   - No microphone is connected")
    print("   - Audio drivers need updating")

print("\n" + "="*60)