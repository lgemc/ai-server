#!/usr/bin/env bash
set -euo pipefail

# Download SDXL 1.0 Base model (~6.5GB) into sd-forge models directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/models/Stable-diffusion"

mkdir -p "$MODEL_DIR"

MODEL_FILE="${MODEL_DIR}/sd_xl_base_1.0.safetensors"

if [ -f "$MODEL_FILE" ]; then
    echo "SDXL 1.0 Base already downloaded: $MODEL_FILE"
    exit 0
fi

echo "Downloading SDXL 1.0 Base (~6.5GB)..."
wget -c -O "$MODEL_FILE" \
    "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"

echo "Download complete: $MODEL_FILE"
