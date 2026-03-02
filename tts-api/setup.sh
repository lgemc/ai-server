#!/bin/bash
# Setup script for Chatterbox TTS API (Blackwell GPU)
# Clones the repo and prepares the build context

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$SCRIPT_DIR/chatterbox-tts-api"

if [ -d "$REPO_DIR" ]; then
    echo "Chatterbox TTS API repo already cloned, pulling latest..."
    cd "$REPO_DIR" && git pull
else
    echo "Cloning Chatterbox TTS API..."
    git clone https://github.com/travisvn/chatterbox-tts-api.git "$REPO_DIR"
fi

echo "Done! You can now run: docker compose up -d tts-api"
