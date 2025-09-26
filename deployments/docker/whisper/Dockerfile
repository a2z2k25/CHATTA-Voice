FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    ffmpeg \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install flask

# Clone and build whisper.cpp
WORKDIR /app
RUN git clone https://github.com/ggerganov/whisper.cpp.git && \
    cd whisper.cpp && \
    make

# Download model
WORKDIR /app/whisper.cpp
RUN bash ./models/download-ggml-model.sh base

# Create API server
WORKDIR /app/whisper.cpp
COPY server.py /app/server.py

EXPOSE 8880

CMD ["python3", "/app/server.py"]
