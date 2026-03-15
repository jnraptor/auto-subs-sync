# Auto Subtitle Sync

A Dockerized web application for automatically synchronizing subtitle files (SRT) against video files (MP4/MKV).

## Features

- **Automatic sync**: Uses ffsubsync (primary) or alass (alternative) to synchronize subtitles with video audio
- **Manual offset**: Apply time offset or framerate conversion manually
- **Multi-audio support**: Select which audio track to sync against for multi-language videos
- **Encoding detection**: Automatically detect and convert subtitle encodings to UTF-8
- **Web interface**: Browse your media folder, select videos and subtitles, preview results
- **WebSocket progress**: Real-time progress updates during sync

## Quick Start

### Using Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/jnraptor/auto-subs-sync.git
   cd auto-subs-sync
   ```

2. Edit `docker-compose.yml` to point to your media folder:
   ```yaml
   volumes:
     - /path/to/your/media:/media:rw
   ```

3. Run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Open http://localhost:8080 in your browser

### Running Locally (Development)

1. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Install system dependencies:
   - ffmpeg (required)
   - ffprobe (required)
   - Optional: alass binary for alternative sync engine

3. Set environment variables:
   ```bash
   export MEDIA_PATH=/path/to/media
   export TEMP_DIR=/tmp/auto-subs-sync
   ```

4. Run the server:
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8080
   ```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MEDIA_PATH` | `/media` | Path to media folder (bind mount) |
| `TEMP_DIR` | `/tmp/auto-subs-sync` | Temporary directory for processing |
| `TEMP_MAX_AGE_SECONDS` | `3600` | Cleanup threshold for temp files |
| `MAX_UPLOAD_SIZE` | `10485760` | Max subtitle upload size (10MB) |

## Reverse Proxy

The app is designed to run behind a reverse proxy that handles authentication and SSL:

### Traefik Example

```yaml
labels:
  - "traefik.http.middlewares.auth.basicauth.users=admin:$$apr1$$..."
  - "traefik.http.routers.auto-subs-sync.middlewares=auth"
```

### Caddy Example

```
subs.example.com {
    basicauth * admin {hash}
    reverse_proxy auto-subs-sync:8080
}
```

## API Endpoints

### Files
- `GET /api/files?path=` - Browse media folder
- `GET /api/files/info?path=` - Get media info (duration, audio tracks)
- `GET /api/files/audio-tracks?path=` - List audio tracks
- `GET /api/files/associated-subtitles?video_path=` - Find subtitles for video

### Sync
- `GET /api/sync/engines` - List available sync engines
- `POST /api/sync` - Start sync job
- `GET /api/sync/{job_id}` - Get job status
- `DELETE /api/sync/{job_id}` - Cancel job
- `WebSocket /api/sync/{job_id}/ws` - Real-time progress

### Subtitles
- `POST /api/subtitles/upload` - Upload subtitle file
- `GET /api/subtitles/download/{job_id}` - Download synced result
- `POST /api/subtitles/save/{job_id}` - Save to media folder

### Stream
- `GET /api/stream/video?path=` - Stream video (range requests)
- `GET /api/stream/subtitle?path=` - Serve subtitle (SRT or VTT)

## Supported Formats

### Video
- MP4, MKV, AVI, WebM

### Subtitles
- SRT (primary)
- ASS/SSA (converted to SRT)

## Sync Engines

1. **ffsubsync** (primary) - Best quality, Python-based
2. **alass** (alternative) - Good for non-linear drift, fast
3. **manual** - Simple offset/framerate adjustment

## License

MIT License
