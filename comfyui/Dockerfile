FROM nvidia/cuda:13.0.0-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    wget \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install PyTorch 2.9.1 with CUDA 13.0 support (includes Blackwell sm_121)
RUN pip3 install --upgrade pip && \
    pip3 install torch==2.9.1 torchvision --index-url https://download.pytorch.org/whl/cu130

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /app/ComfyUI

WORKDIR /app/ComfyUI

# Install ComfyUI dependencies
RUN pip3 install -r requirements.txt

# Create directories for models, outputs, and user data
RUN mkdir -p /app/ComfyUI/models/checkpoints \
    /app/ComfyUI/models/vae \
    /app/ComfyUI/models/loras \
    /app/ComfyUI/models/controlnet \
    /app/ComfyUI/models/clip \
    /app/ComfyUI/models/text_encoders \
    /app/ComfyUI/models/diffusion_models \
    /app/ComfyUI/output \
    /app/ComfyUI/input \
    /app/ComfyUI/user/default/workflows \
    /app/ComfyUI/user/default/subgraphs

# Expose port
EXPOSE 8188

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8188/ || exit 1

# Start ComfyUI
CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
