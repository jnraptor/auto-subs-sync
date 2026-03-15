# Auto Subtitle Sync — Implementation Plan

## Overview
A Dockerized web application for automatically synchronizing subtitle files (SRT) against video files (MP4/MKV). Users browse a bind-mounted media folder to select videos, choose or upload subtitles, and run auto-sync powered by **ffsubsync** (primary) with **alass** as an alternative engine.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Browser (SPA)                                  │
│  - File browser (media folder)                  │
│  - Subtitle upload                              │
│  - Sync controls + progress                     │
│  - Video preview with subtitle overlay          │
└────────────────┬────────────────────────────────┘
                 │ REST API + WebSocket (progress)
┌────────────────▼────────────────────────────────┐
│  FastAPI Backend (Python 3.11)                  │
│  - File browsing API                            │
│  - Subtitle upload/encoding detection           │
│  - Sync job management (async subprocess)       │
│  - Video/subtitle streaming for preview         │
├─────────────────────────────────────────────────┤
│  Sync Engines                                   │
│  - ffsubsync (pip, primary — video-to-sub)      │
│  - alass (Rust binary, alt — good non-linear)   │
│  - Manual offset (built-in, fallback)           │
├─────────────────────────────────────────────────┤
│  System Dependencies                            │
│  - ffmpeg (audio extraction)                    │
│  - ffprobe (media info / audio track listing)   │
└─────────────────────────────────────────────────┘
         │
    ┌────▼────┐
    │ /media  │  ← Docker bind mount (read/write)
    └─────────┘
```

### Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Backend** | FastAPI (Python 3.11) | Native ffsubsync integration, async support, fast |
| **Frontend** | Vanilla HTML/CSS/JS (single page) | No build step, minimal complexity, served by FastAPI |
| **Sync engine (primary)** | ffsubsync | Best video-to-sub sync, Python API |
| **Sync engine (alt)** | alass | Excellent non-linear correction, fast |
| **Task processing** | asyncio subprocess | Lightweight, no Celery/Redis needed for single-user app |
| **Real-time updates** | WebSocket (FastAPI) | Progress reporting during sync |
| **Containerization** | Multi-stage Dockerfile | Rust build stage for alass → Python slim final image |

---

## Project Structure

```
auto-subs-sync/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, CORS, static files, lifespan
│   │   ├── config.py            # Settings (media path, temp dir, etc.)
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── files.py         # File browsing + media info endpoints
│   │   │   ├── sync.py          # Sync job endpoints (start, status, cancel)
│   │   │   ├── subtitles.py     # Upload, download, preview subtitles
│   │   │   └── stream.py        # Video/subtitle streaming for preview
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── file_browser.py  # Media folder traversal, filtering
│   │   │   ├── media_info.py    # ffprobe wrapper (duration, audio tracks)
│   │   │   ├── sync_engine.py   # Orchestrates ffsubsync/alass/manual
│   │   │   ├── ffsubsync_runner.py  # ffsubsync subprocess wrapper
│   │   │   ├── alass_runner.py  # alass subprocess wrapper
│   │   │   ├── manual_sync.py   # Manual offset/framerate adjustment
│   │   │   ├── encoding.py      # Subtitle encoding detection + conversion
│   │   │   ├── subtitle_format.py  # ASS/SSA to SRT conversion
│   │   │   ├── job_manager.py   # Async job tracking, progress, cancellation
│   │   │   └── temp_cleanup.py  # Periodic temp file cleanup
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py       # Pydantic models for API request/response
│   │   │   └── errors.py        # Custom exception classes with error codes
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── srt.py           # SRT parsing/writing utilities
│   │       ├── vtt.py           # SRT↔VTT conversion for preview
│   │       └── paths.py         # Path validation, security (no traversal)
│   ├── requirements.txt
│   └── tests/
│       ├── __init__.py
│       ├── test_file_browser.py
│       ├── test_sync_engine.py
│       ├── test_encoding.py
│       ├── test_manual_sync.py
│       ├── test_srt.py
│       ├── test_vtt.py          # SRT↔VTT conversion
│       ├── test_subtitle_format.py  # ASS/SSA to SRT conversion
│       ├── test_errors.py       # Error handling and codes
│       └── test_api.py          # API endpoint tests with FastAPI TestClient
├── frontend/
│   ├── index.html               # Single page app
│   ├── css/
│   │   └── style.css            # Clean, responsive styling
│   └── js/
│       ├── app.js               # Main app logic, state management
│       ├── file-browser.js      # File browser component
│       ├── sync-controls.js     # Sync configuration + progress UI
│       ├── preview.js           # Video player with subtitle overlay
│       └── api.js               # API client + WebSocket handler
├── Dockerfile                   # Multi-stage (Rust build + Python runtime)
├── docker-compose.yml           # Easy deployment with volume mount
├── .dockerignore
├── .gitignore
└── README.md
```

---

## Implementation Steps

### Phase 1: Project Scaffolding & Backend Core

#### Step 1.1 — Project setup
- Initialize git repo, `.gitignore`, `README.md`
- Create directory structure
- `requirements.txt`: fastapi, uvicorn, python-multipart, ffsubsync, chardet, pysrt, pysubs2, websockets, aiofiles

#### Step 1.2 — Configuration & security
- `config.py`: Settings via environment variables
  - `MEDIA_PATH` (default: `/media`) — bind mount path
  - `TEMP_DIR` (default: `/tmp/auto-subs-sync`)
  - `TEMP_MAX_AGE_SECONDS` (default: `3600`) — cleanup threshold for temp files
  - `MAX_UPLOAD_SIZE` (default: 10MB for subtitles)
  - `ALLOWED_VIDEO_EXTENSIONS`: `.mp4`, `.mkv`, `.avi`, `.webm`
  - `ALLOWED_SUB_EXTENSIONS`: `.srt` (ASS/SSA converted to SRT on upload)
- `utils/paths.py`: Path traversal prevention — all paths resolved and validated against `MEDIA_PATH`
- Temp file lifecycle:
  - All temp files created in subdirectories under `TEMP_DIR` with unique IDs
  - Cleanup runs on app startup and periodically (every 10 min) to remove files older than `TEMP_MAX_AGE_SECONDS`
  - Job temp dirs cleaned immediately after job completion or cancellation

#### Step 1.3 — File browsing service
- `services/file_browser.py`:
  - `list_directory(path)` → list files/folders within media mount
  - Filter by video/subtitle extensions
  - Return file metadata (name, size, modified date, type)
  - Find associated subtitles for a video (same name, different extension)

#### Step 1.4 — Media info service
- `services/media_info.py`:
  - Run `ffprobe` to extract: duration, video codec, audio tracks (index, language, codec)
  - Return structured info for audio track selection UI

#### Step 1.5 — FastAPI app skeleton
- `main.py`: FastAPI app with static file serving (frontend), CORS
- `routers/files.py`:
  - `GET /api/files?path=` — browse media folder
  - `GET /api/files/info?path=` — get media info (ffprobe)

### Phase 2: Sync Engines

#### Step 2.1 — Subtitle encoding detection
- `services/encoding.py`:
  - Detect encoding using `chardet`
  - Convert to UTF-8 before processing
  - Handle BOM markers (UTF-8-BOM, UTF-16)
  - `convert_to_utf8(file_path, detected_encoding) -> str`: returns path to converted temp file

#### Step 2.1b — Subtitle format handling
- `services/subtitle_format.py`:
  - Upload process: ASS/SSA files converted to SRT using `pysubs2` library before sync
  - All sync engines work on SRT internally
  - On save: if original was ASS/SSA, offer option to convert result back or save as SRT
  - `convert_ass_to_srt(ass_path) -> srt_path`: uses pysubs2 to convert

#### Step 2.2 — ffsubsync runner
- `services/ffsubsync_runner.py`:
  - Wraps ffsubsync as async subprocess: `ffs <video> -i <sub> -o <output>`
  - Progress parsing: reads stderr line-by-line, extracts percentage from lines like `Applying offset: 100%|██████████| 5/5 [00:01<00:00, 5.00it/s]`
  - `parse_ffsubsync_progress(line: str) -> Optional[float]`: extracts 0.0-1.0 progress fraction
  - `parse_ffsubsync_error(stderr: str) -> str`: maps known error patterns to user-friendly messages
  - Supports audio track selection via `--no-fix-framerate` / framerate override
  - Returns: `SyncResult(success, output_path, error_message, logs)`
  - Error states: `VIDEO_NOT_FOUND`, `SUBTITLE_PARSE_ERROR`, `NO_AUDIO_STREAM`, `SYNC_FAILED`, `TIMEOUT`

#### Step 2.3 — alass runner
- `services/alass_runner.py`:
  - Wraps alass binary as async subprocess: `alass <video> <sub> <output>`
  - Progress parsing: alass outputs progress as `Progress: 25%` lines to stdout
  - `parse_alass_progress(line: str) -> Optional[float]`: extracts 0.0-1.0 progress fraction
  - `parse_alass_error(stderr: str) -> str`: maps error patterns to user messages
  - Returns: `SyncResult(success, output_path, error_message, logs)`

#### Step 2.4 — Manual sync
- `services/manual_sync.py`:
  - Apply constant time offset (±ms) to all subtitle entries
  - Apply framerate conversion (e.g., 23.976 → 25 fps) by scaling timestamps
  - Uses `pysrt` library for SRT manipulation
  - `apply_offset(srt_content, offset_ms) -> srt_content`
  - `convert_framerate(srt_content, source_fps, target_fps) -> srt_content`
  - `apply_both(srt_content, offset_ms, framerate_ratio) -> srt_content`

#### Step 2.5 — Sync engine orchestrator
- `services/sync_engine.py`:
  - Unified interface: `sync(video_path, sub_path, engine, options) → SyncResult`
  - Engine enum: `ffsubsync | alass | manual`
  - Options: audio track index, framerate override, manual offset
  - Handles temp file management, encoding normalization
  - Creates backup of original subtitle (`.srt.bak`)
  - `get_available_engines() -> List[str]`: checks if ffsubsync/alass are installed
  - `validate_sync_request(video_path, sub_path, options) -> ValidationResult`
  - Error propagation: wraps subprocess errors with context, never exposes internal paths

#### Step 2.5b — Error handling strategy
- `models/errors.py`: Custom exception classes with error codes
  - `SyncError(code, message, details)`: base class
  - `VideoNotFoundError`, `SubtitleParseError`, `UnsupportedFormatError`, `SyncTimeoutError`, `EngineNotAvailableError`
  - All errors return JSON with `{ "error": { "code": "...", "message": "...", "details": {} } }`
- Frontend displays user-friendly messages with retry options for transient errors

#### Step 2.6 — Job manager
- `services/job_manager.py`:
  - Track running sync jobs (id, status, progress, logs, error)
  - Support cancellation (kill subprocess, cleanup temp files)
  - Async generator for progress updates (fed to WebSocket)
  - Concurrency: maximum 1 concurrent job; additional requests return HTTP 429 with retry-after header
  - Job state in memory; persisted to `TEMP_DIR/jobs/{job_id}.json` for crash recovery
  - On startup: resume incomplete jobs from persisted state (re-run cancelled, skip completed)
  - `JobStatus`: `pending | running | completed | failed | cancelled`

### Phase 3: API Endpoints

#### Step 3.1 — Sync endpoints
- `routers/sync.py`:
  - `GET /api/sync/engines` — list available sync engines (ffsubsync may not be installed)
    ```json
    {"engines": ["ffsubsync", "alass", "manual"], "default": "ffsubsync"}
    ```
  - `POST /api/sync` — start sync job (returns 429 if job already running)
    ```json
    {
      "video_path": "Movies/movie.mkv",
      "subtitle_path": "Movies/movie.srt",
      "engine": "ffsubsync",
      "options": {
        "audio_track": 0,
        "framerate": null,
        "offset_ms": null
      }
    }
    ```
  - `GET /api/sync/{job_id}` — get job status
  - `DELETE /api/sync/{job_id}` — cancel job (kills subprocess, cleans temp)
  - `WebSocket /api/sync/{job_id}/ws` — real-time progress
    - Sends: `{"type": "progress", "percent": 0.45, "message": "..."}`
    - Sends: `{"type": "complete", "result": {...}}` or `{"type": "error", "error": {...}}`
    - Client should reconnect with exponential backoff on disconnect

#### Step 3.2 — Subtitle endpoints
- `routers/subtitles.py`:
  - `POST /api/subtitles/upload` — upload subtitle file (multipart), store in temp
  - `GET /api/subtitles/download/{job_id}` — download synced result
  - `POST /api/subtitles/save/{job_id}` — save synced result to media folder
    - Saves as `<video_name>.synced.srt` or overwrites original (user choice)
    - Always creates `.bak` backup of original

#### Step 3.3 — Video streaming
- `routers/stream.py`:
  - `GET /api/stream/video?path=` — stream video with range request support (for HTML5 player)
  - `GET /api/stream/subtitle?path=` — serve subtitle file (for video.js overlay)

### Phase 4: Frontend

#### Step 4.1 — Layout & styling
- `index.html`: Single page layout
  - Header with app name
  - Two-panel layout: file browser (left), controls + preview (right)
  - Responsive (works on tablet too)
- `css/style.css`: Clean dark theme (media apps convention), no framework

#### Step 4.2 — File browser
- `js/file-browser.js`:
  - Tree/list view of media folder
  - Click folder to navigate, click video to select
  - Icons for file types (video, subtitle, folder)
  - Shows associated subtitles next to video files
  - Breadcrumb navigation

#### Step 4.3 — Sync controls
- `js/sync-controls.js`:
  - Selected video display (with duration, audio tracks from ffprobe)
  - Subtitle source: associated file / browse media / upload
  - Engine selector: Auto (ffsubsync) | alass | Manual
  - Audio track dropdown (for multi-track MKV files)
  - Manual options (shown when Manual selected): offset slider (ms), framerate dropdown
  - "Sync" button → starts job
  - Progress bar + log output during sync
  - Result actions: Preview | Save to folder | Download | Discard

#### Step 4.4 — Video preview
- `js/preview.js`:
  - HTML5 video element with range-request streaming
  - Subtitle overlay using WebVTT track (convert SRT → VTT on-the-fly server-side)
  - Toggle between original and synced subtitles for comparison
  - Simple seek/play controls

#### Step 4.5 — API client
- `js/api.js`:
  - Fetch wrapper for REST endpoints with error parsing
  - WebSocket connection for sync progress:
    - Exponential backoff reconnection on disconnect (1s, 2s, 4s, max 30s)
    - Heartbeat: send `{"type": "ping"}` every 30s, expect `{"type": "pong"}`
    - On reconnect: fetch latest job status via REST to resync state
  - Error handling: parse error codes, display user-friendly messages

### Phase 5: Docker & Deployment

#### Step 5.1 — Dockerfile (multi-stage)
```dockerfile
# Stage 1: Build alass from source
FROM rust:1.75-slim AS alass-builder
RUN apt-get update && apt-get install -y git
RUN cargo install alass-cli

# Stage 2: Runtime
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=alass-builder /usr/local/cargo/bin/alass-cli /usr/local/bin/alass
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
WORKDIR /app
EXPOSE 8080
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### Step 5.2 — docker-compose.yml
```yaml
version: "3.8"
services:
  auto-subs-sync:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - /path/to/media:/media:rw
    environment:
      - MEDIA_PATH=/media
    restart: unless-stopped
```

#### Step 5.3 — README.md
- Project description, quick start with docker-compose, configuration options, supported formats

#### Step 5.4 — Reverse proxy deployment
- App designed to run behind reverse proxy (Traefik, Nginx, Caddy)
- Example Traefik config with basic auth:
  ```yaml
  labels:
    - "traefik.http.middlewares.auth.basicauth.users=admin:$$apr1$$..."
    - "traefik.http.routers.auto-subs-sync.middlewares=auth"
  ```
- Example Caddy config:
  ```
  subs.example.com {
      basicauth * admin {hash}
      reverse_proxy auto-subs-sync:8080
  }
  ```
- SSL/TLS handled by reverse proxy (Let's Encrypt, Cloudflare, etc.)
- WebSocket support required in reverse proxy config

### Phase 6: Tests

#### Step 6.1 — Unit tests
- `test_srt.py`: SRT parsing, offset application, framerate conversion
- `test_encoding.py`: Encoding detection for various charset samples
- `test_file_browser.py`: Directory listing, path traversal prevention
- `test_manual_sync.py`: Manual offset and framerate adjustment accuracy

#### Step 6.2 — Integration tests
- `test_sync_engine.py`: End-to-end sync with sample files (mocked ffsubsync/alass)
- API endpoint tests with FastAPI TestClient

---

## Key Design Decisions

1. **ffsubsync as primary engine** — best video-to-subtitle sync quality, Python-native, active maintenance
2. **alass as secondary** — excellent for non-linear drift, fast, good alternative when ffsubsync struggles
3. **Manual fallback** — always available for simple offset/framerate issues
4. **No heavy task queue** — single-user app; asyncio subprocess is sufficient; 429 for concurrent requests
5. **Vanilla frontend** — no build step, minimal complexity, easy to modify
6. **SRT to VTT conversion** — HTML5 track element requires WebVTT; server converts on-the-fly for preview
7. **ASS/SSA conversion** — convert to SRT on upload for compatibility with all sync engines
8. **Backup before save** — always create `.bak` before overwriting original subtitle
9. **Encoding normalization** — detect and convert to UTF-8 before any processing
10. **Auth handled by reverse proxy** — app focuses on functionality; auth/SSL delegated to infrastructure
11. **Job persistence** — jobs persisted to temp files for crash recovery and restart resume

---

## Additional Considerations

1. **Multi-audio track selection** — MKV files often have multiple audio tracks (e.g., English, Japanese). Need to let user pick which track to sync against.
2. **Subtitle encoding issues** — Many subtitle files are not UTF-8 (Windows-1252, ISO-8859-1, etc.). Auto-detection and conversion is essential.
3. **Non-linear drift** — Sometimes subtitles don't just have a constant offset; they drift over time. Both ffsubsync and alass handle this, but it's worth knowing.
4. **Backup strategy** — Always back up the original subtitle before overwriting.
5. **Video preview with subtitle overlay** — Being able to preview the result before saving is very useful for validation.
6. **Large file handling** — Videos can be multi-GB. The app should never try to buffer them in memory; use streaming and file paths.
7. **Processing time expectations** — ffsubsync can take 1-5 minutes for a 2-hour movie. Progress feedback is important.
8. **Audio track language detection** — ffprobe can report audio track languages, helping auto-select the right track.
9. **Job crash recovery** — If container crashes mid-sync, persisted job state allows resume on restart.
10. **Network-mounted media** — For NFS/SMB mounts, expect higher latency; timeout handling should be generous.
11. **Engine availability** — ffsubsync installed via pip, alass via binary; check availability at startup and expose via API.

---

## Security Considerations

- **Authentication & SSL** — Handled by reverse proxy (e.g., Traefik, Nginx with basic auth, OAuth2 proxy); app trusts all requests from proxy
- **Path traversal prevention** — all user-supplied paths validated against MEDIA_PATH root
- **File type validation** — only allow known video/subtitle extensions
- **Upload size limits** — subtitle uploads capped at 10MB
- **No shell injection** — subprocess calls use list args, never shell=True
- **Read-only video access** — app never modifies video files, only reads them
- **Temp file isolation** — temp files created in random subdirectories, cleaned after use
- **Error message safety** — errors never expose internal paths or system details
