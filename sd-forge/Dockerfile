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

# Clone Stable Diffusion WebUI Forge
RUN git clone https://github.com/lllyasviel/stable-diffusion-webui-forge.git /app/stable-diffusion-webui-forge

WORKDIR /app/stable-diffusion-webui-forge

# Install requirements
RUN pip3 install -r requirements_versions.txt

# Create model directories
RUN mkdir -p /app/stable-diffusion-webui-forge/models/Stable-diffusion \
    /app/stable-diffusion-webui-forge/models/VAE \
    /app/stable-diffusion-webui-forge/models/Lora \
    /app/stable-diffusion-webui-forge/models/ControlNet \
    /app/stable-diffusion-webui-forge/models/ESRGAN \
    /app/stable-diffusion-webui-forge/outputs \
    /app/stable-diffusion-webui-forge/extensions

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:7860/sdapi/v1/sd-models || exit 1

# Start Forge with API enabled
CMD ["python3", "launch.py", "--listen", "--api", "--port", "7860", "--skip-install", "--no-half-vae"]
