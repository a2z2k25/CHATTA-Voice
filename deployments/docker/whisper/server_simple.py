#!/usr/bin/env python3
import os
import whisper
from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile

app = Flask(__name__)
CORS(app)

# Load Whisper model
print("Loading Whisper model...")
model = whisper.load_model("base")
print("Model loaded successfully!")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'whisper-stt', 'model': 'base'})

@app.route('/v1/audio/transcriptions', methods=['POST'])
def transcribe():
    """OpenAI-compatible transcription endpoint."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        audio_file = request.files['file']
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            audio_file.save(tmp.name)
            
            try:
                # Transcribe with Whisper
                result = model.transcribe(tmp.name)
                
                # Return in OpenAI format
                return jsonify({
                    'text': result['text'].strip(),
                    'language': result.get('language', 'en')
                })
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)
                    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8880, debug=False)