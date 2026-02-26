# YouTube Download API

A FastAPI-based REST API for downloading YouTube videos using yt-dlp.

## Quick Start

```bash
docker-compose up -d --build
```

The API will be available at `http://localhost:8002`

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/info` | POST | Get video information |
| `/download` | POST | Download a video |
| `/file/{id}/{filename}` | GET | Retrieve downloaded file |
| `/file/{id}` | DELETE | Delete downloaded file |
| `/docs` | GET | Swagger UI documentation |

## Usage Examples

### Get Video Info

```bash
curl -X POST http://localhost:8002/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### Download Video

```bash
curl -X POST http://localhost:8002/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### Download Audio Only (MP3)

```bash
curl -X POST http://localhost:8002/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "audio_only": true}'
```

### Get Downloaded File

```bash
curl -O http://localhost:8002/file/{download_id}/{filename}
```

### Delete Downloaded File

```bash
curl -X DELETE http://localhost:8002/file/{download_id}
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DOWNLOAD_DIR` | `/tmp/youtube-downloads` | Directory for downloaded files |
