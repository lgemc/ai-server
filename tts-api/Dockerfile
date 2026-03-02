# Chatterbox TTS API - Blackwell GB10 (CUDA 12.9, sm_121) optimized build
# Based on: https://github.com/travisvn/chatterbox-tts-api/blob/main/docker/Dockerfile.blackwell

FROM nvidia/cuda:12.9.0-devel-ubuntu22.04

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.11 and system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    git \
    wget \
    curl \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Create virtual environment
RUN uv venv --python 3.11
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install PyTorch with CUDA 12.9 support (Blackwell GB10 sm_121)
RUN uv pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu129

# Install base dependencies
RUN uv pip install setuptools fastapi uvicorn[standard] python-dotenv python-multipart requests psutil pydub sse-starlette

# Install chatterbox-tts multilingual
RUN uv pip install git+https://github.com/travisvn/chatterbox-multilingual.git@exp

# Reinstall PyTorch to ensure CUDA 12.9 version (post chatterbox deps)
RUN uv pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu129

# Copy application code from cloned repo
COPY chatterbox-tts-api/app/ ./app/
COPY chatterbox-tts-api/main.py ./
COPY chatterbox-tts-api/voice-sample.mp3 ./voice-sample.mp3

# Create directories for model cache and voice library
RUN mkdir -p /cache /voices /data/long_text_jobs

# Default environment
ENV PORT=4123
ENV HOST=0.0.0.0
ENV DEVICE=cuda
ENV MODEL_CACHE_DIR=/cache
ENV VOICE_LIBRARY_DIR=/voices
ENV EXAGGERATION=0.5
ENV CFG_WEIGHT=0.5
ENV TEMPERATURE=0.8
ENV MAX_CHUNK_LENGTH=280
ENV MAX_TOTAL_LENGTH=3000
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
# Blackwell GB10 (sm_121) JIT compilation support
ENV TORCH_CUDA_ARCH_LIST="12.0+PTX"
ENV TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas

EXPOSE 4123

HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:4123/health || exit 1

CMD ["python", "main.py"]
