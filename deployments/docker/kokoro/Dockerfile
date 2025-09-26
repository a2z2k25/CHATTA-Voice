FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    kokoro-onnx \
    fastapi \
    uvicorn \
    python-multipart \
    numpy \
    scipy

# Create app directory
WORKDIR /app

# Download required model files
RUN wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin -O voices.bin && \
    wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx -O kokoro.onnx

# Copy server code
COPY server.py /app/server.py

EXPOSE 7888

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7888"]
