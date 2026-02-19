# Whisper Transcription API

A Docker-based API for transcribing audio and video files using OpenAI's Whisper model.

## Quick Start

### Build and Run (CPU)

```bash
docker-compose up -d --build
```

### Build and Run (GPU - NVIDIA)

Edit `docker-compose.yml` to uncomment the GPU service, then:

```bash
docker-compose up -d --build whisper-api-gpu
```

## API Usage

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/transcribe` | POST | Transcribe audio/video file |
| `/docs` | GET | Swagger UI documentation |

### Transcribe a File

```bash
# Basic transcription (English)
curl -X POST "http://localhost:8000/transcribe" \
  -F "file=@video.mp4"

# Specify language (Spanish)
curl -X POST "http://localhost:8000/transcribe" \
  -F "file=@video.mp4" \
  -F "language=es"

# Translate to English
curl -X POST "http://localhost:8000/transcribe" \
  -F "file=@video.mp4" \
  -F "language=es" \
  -F "task=translate"
```

### Response Format

```json
{
  "success": true,
  "filename": "video.mp4",
  "language": "en",
  "task": "transcribe",
  "text": "Full transcription text...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 2.5,
      "text": "Segment text..."
    }
  ]
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `large` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |

### Model Sizes

| Model | Parameters | VRAM | Relative Speed |
|-------|------------|------|----------------|
| tiny | 39M | ~1GB | ~32x |
| base | 74M | ~1GB | ~16x |
| small | 244M | ~2GB | ~6x |
| medium | 769M | ~5GB | ~2x |
| large | 1550M | ~10GB | 1x |

## Supported Languages

Whisper supports 99+ languages. Common codes:
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `zh` - Chinese
- `ja` - Japanese
- `ko` - Korean
- `ru` - Russian

## Supported File Formats

- Audio: mp3, wav, m4a, flac, ogg, wma
- Video: mp4, mkv, avi, mov, webm, wmv
