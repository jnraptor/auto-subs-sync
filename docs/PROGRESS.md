# Auto Subtitle Sync — Implementation Progress

Last updated: 2026-03-15

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Completed
- [!] Blocked/Issues

---

## Phase 1: Project Scaffolding & Backend Core

- [x] 1.1 Project setup
  - [x] Initialize git repo
  - [x] Create `.gitignore`
  - [x] Create directory structure
  - [x] Create `requirements.txt`

- [x] 1.2 Configuration & security
  - [x] `config.py` with environment variables
  - [x] `utils/paths.py` for path validation

- [x] 1.3 File browsing service
  - [x] `services/file_browser.py`

- [x] 1.4 Media info service
  - [x] `services/media_info.py` (ffprobe wrapper)

- [x] 1.5 FastAPI app skeleton
  - [x] `main.py` with static file serving
  - [x] `routers/files.py`

---

## Phase 2: Sync Engines

- [x] 2.1 Subtitle encoding detection
  - [x] `services/encoding.py`

- [x] 2.1b Subtitle format handling
  - [x] `services/subtitle_format.py` (ASS/SSA conversion)

- [x] 2.2 ffsubsync runner
  - [x] `services/ffsubsync_runner.py`

- [x] 2.3 alass runner
  - [x] `services/alass_runner.py`

- [x] 2.4 Manual sync
  - [x] `services/manual_sync.py`

- [x] 2.5 Sync engine orchestrator
  - [x] `services/sync_engine.py`

- [x] 2.5b Error handling strategy
  - [x] `models/errors.py`

- [x] 2.6 Job manager
  - [x] `services/job_manager.py`
  - [x] `services/temp_cleanup.py`

---

## Phase 3: API Endpoints

- [x] 3.1 Sync endpoints
  - [x] `routers/sync.py`

- [x] 3.2 Subtitle endpoints
  - [x] `routers/subtitles.py`

- [x] 3.3 Video streaming
  - [x] `routers/stream.py`

---

## Phase 4: Frontend

- [x] 4.1 Layout & styling
  - [x] `index.html`
  - [x] `css/style.css`

- [x] 4.2 File browser
  - [x] `js/file-browser.js`

- [x] 4.3 Sync controls
  - [x] `js/sync-controls.js`

- [x] 4.4 Video preview
  - [x] `js/preview.js`

- [x] 4.5 API client
  - [x] `js/api.js`
  - [x] `js/app.js`

---

## Phase 5: Docker & Deployment

- [x] 5.1 Dockerfile (multi-stage)
- [x] 5.2 docker-compose.yml
- [x] 5.3 README.md
- [x] 5.4 Reverse proxy examples

---

## Phase 6: Tests

- [x] 6.1 Unit tests
  - [x] `test_srt.py` - SRT parsing, offset, framerate
  - [x] `test_encoding.py` - Encoding detection
  - [x] `test_file_browser.py` - Directory listing, path traversal
  - [x] `test_manual_sync.py` - Manual offset and framerate
  - [x] `test_vtt.py` - SRT↔VTT conversion
  - [x] `test_subtitle_format.py` - ASS/SSA to SRT conversion
  - [x] `test_errors.py` - Error handling and codes

- [x] 6.2 Integration tests
  - [x] `test_sync_engine.py` - Sync engine (mocked)
  - [x] `test_api.py` - API endpoint tests

---

## Notes

- Backend implementation complete
- Frontend implementation complete  
- Docker configuration ready
- Tests complete

### Running Tests

```bash
cd /Users/jon/dev/auto-subs-sync
pip install -r backend/requirements.txt
pytest
```

### Files Created

**Backend:**
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/routers/files.py`
- `backend/app/routers/sync.py`
- `backend/app/routers/subtitles.py`
- `backend/app/routers/stream.py`
- `backend/app/services/file_browser.py`
- `backend/app/services/media_info.py`
- `backend/app/services/encoding.py`
- `backend/app/services/subtitle_format.py`
- `backend/app/services/ffsubsync_runner.py`
- `backend/app/services/alass_runner.py`
- `backend/app/services/manual_sync.py`
- `backend/app/services/sync_engine.py`
- `backend/app/services/job_manager.py`
- `backend/app/services/temp_cleanup.py`
- `backend/app/models/schemas.py`
- `backend/app/models/errors.py`
- `backend/app/utils/paths.py`
- `backend/app/utils/srt.py`
- `backend/app/utils/vtt.py`
- `backend/requirements.txt`

**Tests:**
- `backend/tests/__init__.py`
- `backend/tests/test_srt.py`
- `backend/tests/test_vtt.py`
- `backend/tests/test_encoding.py`
- `backend/tests/test_manual_sync.py`
- `backend/tests/test_subtitle_format.py`
- `backend/tests/test_errors.py`
- `backend/tests/test_file_browser.py`
- `backend/tests/test_sync_engine.py`
- `backend/tests/test_api.py`

**Frontend:**
- `frontend/index.html`
- `frontend/css/style.css`
- `frontend/js/app.js`
- `frontend/js/api.js`
- `frontend/js/file-browser.js`
- `frontend/js/sync-controls.js`
- `frontend/js/preview.js`

**Docker:**
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

**Docs:**
- `README.md`
- `PLAN.md`
- `PROGRESS.md`