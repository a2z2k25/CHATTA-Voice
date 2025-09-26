#!/usr/bin/env python3
import os
import subprocess
from flask import Flask, request, jsonify
import tempfile
import json

app = Flask(__name__)

# Path to whisper.cpp executable and model
WHISPER_EXEC = '/app/whisper.cpp/main'
MODEL_PATH = '/app/whisper.cpp/models/ggml-base.bin'

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'whisper-stt'})

@app.route('/v1/audio/transcriptions', methods=['POST'])
def transcribe():
    """OpenAI-compatible transcription endpoint."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        audio_file = request.files['file']
        
        # Save uploaded file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            audio_file.save(tmp.name)
            
            try:
                # Run whisper.cpp with proper paths
                result = subprocess.run([
                    WHISPER_EXEC,
                    '-m', MODEL_PATH,
                    '-f', tmp.name,
                    '-nt'  # No timestamps
                ], capture_output=True, text=True, cwd='/app/whisper.cpp')
                
                if result.returncode != 0:
                    return jsonify({'error': f'Whisper failed: {result.stderr}'}), 500
                
                # Extract the transcribed text (whisper.cpp outputs directly to stdout)
                text = result.stdout.strip()
                
                return jsonify({'text': text})
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)
                    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8880)
