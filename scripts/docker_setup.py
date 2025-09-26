#!/usr/bin/env python3
"""
Docker setup script for CHATTA voice services.
Reads configuration from docker.config.json and sets up Docker infrastructure.
"""

import json
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any

def load_config(config_file: str = "docker.config.json") -> Dict[str, Any]:
    """Load Docker configuration from JSON file."""
    config_path = Path(config_file)
    
    # If config doesn't exist, copy from template
    if not config_path.exists():
        template_path = Path("docker.config.template.json")
        if template_path.exists():
            print(f"Creating {config_file} from template...")
            config_path.write_text(template_path.read_text())
        else:
            print(f"Error: Neither {config_file} nor docker.config.template.json found!")
            sys.exit(1)
    
    with open(config_path, 'r') as f:
        return json.load(f)

def create_directory_structure(config: Dict[str, Any]) -> None:
    """Create necessary directories for Docker services."""
    directories = [
        config['docker']['base_path'],
        f"{config['docker']['base_path']}/whisper",
        f"{config['docker']['base_path']}/kokoro",
        f"{config['docker']['base_path']}/livekit",
        config['models']['base_path'],
        config['models']['whisper']['path'],
        config['models']['kokoro']['path'],
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {dir_path}")

def generate_docker_compose(config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate docker-compose.yml content from configuration."""
    services = config['docker']['services']
    
    compose = {
        'version': '3.8',
        'services': {},
        'networks': {
            config['docker']['network_name']: {
                'driver': 'bridge',
                'name': config['docker']['network_name']
            }
        },
        'volumes': {
            'whisper-models': {},
            'kokoro-models': {}
        }
    }
    
    # Whisper service
    compose['services']['whisper'] = {
        'build': {
            'context': services['whisper']['build_context'],
            'dockerfile': services['whisper']['dockerfile']
        },
        'container_name': services['whisper']['container_name'],
        'ports': [services['whisper']['port']],
        'volumes': [f"{services['whisper']['model_path']}:/models"],
        'environment': [
            f"{k}={v}" for k, v in services['whisper']['environment'].items()
        ],
        'restart': 'unless-stopped',
        'networks': [config['docker']['network_name']]
    }
    
    # Kokoro service
    compose['services']['kokoro'] = {
        'build': {
            'context': services['kokoro']['build_context'],
            'dockerfile': services['kokoro']['dockerfile']
        },
        'container_name': services['kokoro']['container_name'],
        'ports': [services['kokoro']['port']],
        'volumes': [f"{services['kokoro']['model_path']}:/models"],
        'environment': [
            f"{k}={v}" for k, v in services['kokoro']['environment'].items()
        ],
        'restart': 'unless-stopped',
        'networks': [config['docker']['network_name']]
    }
    
    # LiveKit service
    livekit = services['livekit']
    compose['services']['livekit'] = {
        'image': livekit['image'],
        'container_name': livekit['container_name'],
        'ports': [
            livekit['ports']['api'],
            livekit['ports']['webrtc_tcp'],
            livekit['ports']['webrtc_udp']
        ],
        'environment': [
            f"LIVEKIT_CONFIG=/etc/livekit.yaml"
        ],
        'volumes': [
            f"{livekit['config_path']}:/etc/livekit.yaml"
        ],
        'restart': 'unless-stopped',
        'networks': [config['docker']['network_name']],
        'command': '--config /etc/livekit.yaml'
    }
    
    return compose

def write_docker_compose(compose: Dict[str, Any], output_file: str = "docker-compose.yml") -> None:
    """Write docker-compose.yml file."""
    with open(output_file, 'w') as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)
    print(f"✓ Generated {output_file}")

def create_whisper_dockerfile(config: Dict[str, Any]) -> None:
    """Create Dockerfile for Whisper.cpp service."""
    dockerfile_content = """FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    cmake \\
    git \\
    wget \\
    ffmpeg \\
    && rm -rf /var/lib/apt/lists/*

# Clone and build whisper.cpp
WORKDIR /app
RUN git clone https://github.com/ggerganov/whisper.cpp.git && \\
    cd whisper.cpp && \\
    make

# Download model
WORKDIR /app/whisper.cpp
RUN bash ./models/download-ggml-model.sh base

# Create API server
WORKDIR /app/whisper.cpp
COPY server.py /app/server.py

EXPOSE 8880

CMD ["python3", "/app/server.py"]
"""
    
    dockerfile_path = Path(config['docker']['base_path']) / 'whisper' / 'Dockerfile'
    dockerfile_path.write_text(dockerfile_content)
    print(f"✓ Created Whisper Dockerfile")
    
    # Create a simple server wrapper
    server_content = """#!/usr/bin/env python3
import os
import subprocess
from flask import Flask, request, jsonify
import tempfile

app = Flask(__name__)

@app.route('/v1/audio/transcriptions', methods=['POST'])
def transcribe():
    \"\"\"OpenAI-compatible transcription endpoint.\"\"\"
    try:
        audio_file = request.files['file']
        
        # Save uploaded file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            audio_file.save(tmp.name)
            
            # Run whisper.cpp
            result = subprocess.run([
                './main',
                '-m', 'models/ggml-base.bin',
                '-f', tmp.name,
                '--output-json'
            ], capture_output=True, text=True)
            
            os.unlink(tmp.name)
            
        return jsonify({'text': result.stdout.strip()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8880)
"""
    
    server_path = Path(config['docker']['base_path']) / 'whisper' / 'server.py'
    server_path.write_text(server_content)
    print(f"✓ Created Whisper server wrapper")

def create_kokoro_dockerfile(config: Dict[str, Any]) -> None:
    """Create Dockerfile for Kokoro-FastAPI service."""
    dockerfile_content = """FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    ffmpeg \\
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \\
    kokoro-onnx \\
    fastapi \\
    uvicorn \\
    python-multipart

# Create app directory
WORKDIR /app

# Copy server code
COPY server.py /app/server.py

EXPOSE 7888

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7888"]
"""
    
    dockerfile_path = Path(config['docker']['base_path']) / 'kokoro' / 'Dockerfile'
    dockerfile_path.write_text(dockerfile_content)
    print(f"✓ Created Kokoro Dockerfile")
    
    # Create Kokoro FastAPI server
    server_content = """from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import kokoro_onnx
import io

app = FastAPI()

# Initialize Kokoro
kokoro = kokoro_onnx.Kokoro("kokoro-v0.87", "af")

class TTSRequest(BaseModel):
    input: str
    voice: str = "af"
    model: str = "tts-1"

@app.post("/v1/audio/speech")
async def text_to_speech(request: TTSRequest):
    \"\"\"OpenAI-compatible TTS endpoint.\"\"\"
    try:
        # Generate audio
        audio_data = kokoro.synthesize(request.input, voice=request.voice)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "kokoro-tts"}
"""
    
    server_path = Path(config['docker']['base_path']) / 'kokoro' / 'server.py'
    server_path.write_text(server_content)
    print(f"✓ Created Kokoro server")

def create_livekit_config(config: Dict[str, Any]) -> None:
    """Create LiveKit configuration file."""
    livekit_config = """# LiveKit configuration for CHATTA
port: 7880
bind_addresses:
  - "0.0.0.0"

rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 50100
  use_external_ip: false

keys:
  # Development keys - replace in production
  APIwJ4XQiVAkmh5v: lZkoh4BNlxBo0OkUrfKBvhwPyxEHgEBctlIHgNHjNH5

room:
  auto_create: true
  empty_timeout: 300
  max_participants: 10

webhook:
  # Optional webhook configuration
  # url: http://localhost:3000/webhook

logging:
  level: info
  sample: false
"""
    
    config_path = Path(config['docker']['base_path']) / 'livekit' / 'livekit.yaml'
    config_path.write_text(livekit_config)
    print(f"✓ Created LiveKit configuration")

def main():
    """Main setup function."""
    print("🚀 CHATTA Docker Setup")
    print("=" * 50)
    
    # Load configuration
    config = load_config()
    
    # Create directory structure
    print("\n📁 Creating directory structure...")
    create_directory_structure(config)
    
    # Generate docker-compose.yml
    print("\n🐳 Generating Docker Compose configuration...")
    compose = generate_docker_compose(config)
    write_docker_compose(compose)
    
    # Create Dockerfiles and configs
    print("\n📄 Creating service configurations...")
    create_whisper_dockerfile(config)
    create_kokoro_dockerfile(config)
    create_livekit_config(config)
    
    print("\n✅ Docker setup complete!")
    print("\nNext steps:")
    print("1. Review the generated docker-compose.yml")
    print("2. Run: docker-compose up -d")
    print("3. Test services:")
    print("   - Whisper STT: http://localhost:8880")
    print("   - Kokoro TTS: http://localhost:7888")
    print("   - LiveKit: http://localhost:7880")

if __name__ == "__main__":
    main()