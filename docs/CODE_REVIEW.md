# Code Review: Auto Subtitle Sync

**Reviewer:** Claude (claude-opus-4-6)
**Date:** 2026-03-15
**Scope:** Full codebase review against PLAN.md

---

## Executive Summary

The implementation follows the PLAN.md structure closely. All 52 planned files exist with the correct directory layout. The core architecture (FastAPI backend, vanilla JS frontend, Docker deployment) matches the plan. However, there are **several bugs, inconsistencies, dead code paths, and security concerns** that need to be addressed before this is production-ready.

**Severity levels:** CRITICAL (will cause runtime errors), HIGH (significant functional issues), MEDIUM (code quality / correctness concerns), LOW (style / minor issues)

---

## CRITICAL Issues

### 1. Duplicate `import Any` in `models/errors.py:2`

```python
from typing import Optional, Dict, Any, Any  # duplicate Any import
```

**File:** `backend/app/models/errors.py:2`
**Fix:** Remove the duplicate `Any`.

---

### 2. Duplicate `except` blocks in `sync_engine.py:172-177`

```python
except Exception as e:
    logs.append(f"Exception: {str(e)}")
    return False, logs
except Exception as e:        # unreachable duplicate
    logs.append(f"Exception: {str(e)}")
    return False, logs
```

**File:** `backend/app/services/sync_engine.py:172-177`
**Impact:** The second `except` block is unreachable dead code. Not a crash bug, but indicates copy-paste error.
**Fix:** Remove the duplicate `except Exception` block.

---

### 3. `job_manager.get_job()` is async but called synchronously in `sync.py`

In `routers/sync.py:51`:
```python
job = job_manager.get_job(job_id)  # missing await
```

But `job_manager.get_job()` at `services/job_manager.py:179` is defined as:
```python
async def get_job(self, job_id: str) -> Optional[JobInfo]:
```

This returns a coroutine, not the actual `JobInfo`. The WebSocket handler at `sync.py:71` also calls `job_manager.get_job(job_id)` without `await`.

**File:** `backend/app/routers/sync.py:51,71`
**Impact:** The job status endpoint and WebSocket will return coroutine objects instead of actual data, or raise errors.
**Fix:** Add `await` to all `job_manager.get_job()` calls.

---

### 4. Variable name typo in `sync-controls.js:180`

```javascript
cancelBtn.addEventListener('click', handleCancel);  // should be cancelBtnEl
```

But the variable declared on line 19 is `cancelBtnEl`. `cancelBtn` is undefined.

**File:** `frontend/js/sync-controls.js:180`
**Impact:** Runtime `ReferenceError` when cancel button is clicked.
**Fix:** Change `cancelBtn` to `cancelBtnEl`.

---

### 5. `file-browser.js:103` references undefined `event`

```javascript
event.currentTarget.classList.add('selected');
```

The `handleFileClick` function receives `file` as a parameter but references `event` which is not in scope (it's inside an arrow function that doesn't pass `event`).

**File:** `frontend/js/file-browser.js:103`
**Impact:** Runtime error when clicking a video file. The click handler on line 90 passes `file`, not `event`.
**Fix:** Either pass the event to the click handler, or find the clicked element differently (e.g., use `document.querySelector` on the current selection).

---

### 6. Two separate `JobManager` instances

In `routers/sync.py:13`:
```python
job_manager = JobManager()
```

In `services/job_manager.py:270`:
```python
job_manager = JobManager()
```

In `routers/subtitles.py:52`:
```python
from ..services.job_manager import job_manager  # imports the module-level one
```

The sync router creates its own `JobManager()` instance, while the subtitles router imports a different one from the service module. Jobs created via the sync endpoints won't be visible to the subtitle download/save endpoints.

**File:** `backend/app/routers/sync.py:13`, `backend/app/services/job_manager.py:270`, `backend/app/routers/subtitles.py:52`
**Impact:** Subtitle download/save will always return "Job not found" for jobs created through the sync API.
**Fix:** The sync router should import the singleton from `services/job_manager.py` instead of instantiating its own:
```python
from ..services.job_manager import job_manager
```

---

### 7. `create_job` returns existing job instead of raising 429

In `job_manager.py:68-71`:
```python
async def create_job(self, request: SyncRequest) -> JobInfo:
    async with self._lock:
        if self._current_job_id:
            current = self._jobs.get(self._current_job_id)
            if current:
                return current  # silently returns existing job!
```

When a job is already running, `create_job` silently returns the existing job. Then `start_job` returns `False`, and the router raises `JobAlreadyRunningError` with the **wrong job_id** (it uses the new job's id, not the running one's).

**File:** `backend/app/services/job_manager.py:68-71`, `backend/app/routers/sync.py:28-33`
**Impact:** Confusing error messages; the "current_job_id" in the error will point to the existing running job, not clearly communicating what happened. The new job also never gets persisted.
**Fix:** `create_job` should raise `JobAlreadyRunningError` directly instead of returning the existing job.

---

## HIGH Issues

### 8. WebSocket connects to wrong URL

In `api.js:2`:
```javascript
const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
```

But the backend WebSocket endpoint is at `/api/sync/{job_id}/ws`, not `/ws`. The frontend connects to a global `/ws` endpoint that doesn't exist.

**File:** `frontend/js/api.js:2`
**Impact:** WebSocket connection will fail immediately. No real-time progress updates.
**Fix:** The WebSocket URL needs to be constructed per-job: `ws://host/api/sync/{jobId}/ws`.

---

### 9. Frontend API URLs don't match backend routes

- `api.js:149`: `${API_BASE}/download?path=...` -- backend endpoint is `/api/subtitles/download/{job_id}`
- `api.js:157`: `${API_BASE}/video?path=...` -- backend endpoint is `/api/stream/video?path=...`
- `api.js:161`: `${API_BASE}/subtitle?path=...` -- backend endpoint is `/api/stream/subtitle?path=...`

**File:** `frontend/js/api.js:149,157,161`
**Impact:** Video streaming, subtitle loading, and download will all fail (404s).
**Fix:** Update URLs to match backend routes:
- Download: `${API_BASE}/subtitles/download/${jobId}`
- Video: `${API_BASE}/stream/video?path=...`
- Subtitle: `${API_BASE}/stream/subtitle?path=...&format=vtt`

---

### 10. Frontend `syncSubtitle` sends wrong JSON shape

In `sync-controls.js:128-135`, the frontend sends:
```javascript
{ videoPath, subtitlePath, engine, audioTrack, manualOffset, framerateAdjust }
```

But the backend `SyncRequest` schema expects:
```python
{ video_path, subtitle_path, engine, options: { audio_track, offset_ms, ... } }
```

**File:** `frontend/js/sync-controls.js:128-135`, `frontend/js/api.js:134-139`
**Impact:** Backend will reject sync requests with 422 validation errors.
**Fix:** Transform the frontend payload to match the Pydantic model:
```javascript
{
    video_path: options.videoPath,
    subtitle_path: options.subtitlePath,
    engine: options.engine,
    options: {
        audio_track: options.audioTrack,
        offset_ms: options.manualOffset,
        ...
    }
}
```

---

### 11. `_resume_incomplete_jobs` re-runs CANCELLED jobs

In `job_manager.py:38-40`:
```python
elif job_info.status in (JobStatus.PENDING, JobStatus.CANCELLED):
    self._jobs[job_info.id] = job_info
    await self._run_job(job_info.id)  # re-runs cancelled jobs!
```

Cancelled jobs should not be re-run on restart. Only pending jobs should be resumed.

**File:** `backend/app/services/job_manager.py:38-40`
**Fix:** Remove `JobStatus.CANCELLED` from the condition.

---

### 12. `temp_cleanup.py` doesn't store task reference

In `temp_cleanup.py:52`:
```python
async def start_cleanup_task():
    global _cleanup_task
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    asyncio.create_task(cleanup_loop())  # not assigned to _cleanup_task!
```

The created task is not stored in `_cleanup_task`, so `stop_cleanup_task()` can't cancel it (and indeed doesn't try to -- it's a no-op). The cleanup task will also be garbage-collected.

**File:** `backend/app/services/temp_cleanup.py:47-55`
**Fix:**
```python
_cleanup_task = asyncio.create_task(cleanup_loop())

async def stop_cleanup_task():
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
```

---

### 13. `sync_engine.sync()` calls blocking subprocess in async context

The `sync()` function in `sync_engine.py` is called from `job_manager._run_job()` (an async method), but `sync()` is a synchronous function that calls `subprocess.run()` (blocking) via `_run_ffsubsync` -> `run_ffsubsync_sync`. This blocks the entire event loop during sync.

**File:** `backend/app/services/sync_engine.py:220`, `backend/app/services/job_manager.py:123`
**Impact:** The server becomes unresponsive during sync operations (can't serve HTTP requests, WebSocket messages, or file browsing).
**Fix:** Either:
1. Run `sync()` in a thread executor: `await asyncio.get_event_loop().run_in_executor(None, sync, ...)`
2. Or use the already-implemented `run_ffsubsync_with_progress` async version instead of the sync wrapper.

---

### 14. `file_browser.py` has its own `FileInfo` class that shadows `models/schemas.py`

`services/file_browser.py:9` defines a `FileInfo` class with a `to_dict()` method, while `models/schemas.py:64` defines a separate Pydantic `FileInfo` model. The router uses the service's `FileInfo` with `to_dict()` rather than the Pydantic model.

**File:** `backend/app/services/file_browser.py:9-34`, `backend/app/models/schemas.py:64-70`
**Impact:** Inconsistency; the Pydantic model (with serialization, validation) is never used. The API returns raw dicts instead of validated response models.
**Fix:** Use the Pydantic `FileInfo` from schemas instead of the custom class, or remove the unused Pydantic model.

---

### 15. `JobInfo.error_message` field doesn't exist

In `job_manager.py:43`:
```python
job_info.error_message = "Job interrupted by server restart"
```

But the `JobInfo` Pydantic model in `schemas.py:43-55` has no `error_message` field. The message field is just `message`.

**File:** `backend/app/services/job_manager.py:43`
**Impact:** Pydantic validation error or the field silently ignored.
**Fix:** Use `job_info.message = "Job interrupted by server restart"`.

---

## MEDIUM Issues

### 16. No exception handler registered for `SyncError`

`errors.py:136` defines `sync_error_handler()` which converts `SyncError` to `HTTPException`, but it's not registered as a FastAPI exception handler. The routers manually catch specific errors, but any uncaught `SyncError` from service code will result in a 500 Internal Server Error.

**File:** `backend/app/main.py`
**Fix:** Register the handler:
```python
@app.exception_handler(SyncError)
async def handle_sync_error(request, exc):
    http_exc = sync_error_handler(exc)
    return JSONResponse(status_code=http_exc.status_code, content=http_exc.detail)
```

---

### 17. `validate_path` raises HTTP exceptions from a utility layer

`utils/paths.py` raises `HTTPException`, which couples the utility layer to FastAPI. This means services that import `validate_path` (like `sync_engine.py`, `ffsubsync_runner.py`) will raise HTTP exceptions from non-HTTP code, making testing harder and violating separation of concerns.

**File:** `backend/app/utils/paths.py:7-18`
**Fix:** Raise plain `ValueError` or a custom `PathValidationError`, and let the routers translate to HTTP exceptions.

---

### 18. `stream.py` returns JSON for errors instead of HTTP exceptions

In `stream.py:21`:
```python
if not full_path.is_file():
    return {"error": "Not a file"}  # returns 200 with error body!
```

**File:** `backend/app/routers/stream.py:21,70`
**Impact:** Clients get a 200 OK with an error JSON body instead of a proper 404.
**Fix:** Raise `HTTPException(status_code=404, detail="Not a file")`.

---

### 19. `stream.py` hardcodes `video/mp4` content type

In `stream.py:40,55`:
```python
media_type="video/mp4",
```

MKV files should be `video/x-matroska`, AVI should be `video/x-msvideo`, WebM should be `video/webm`.

**File:** `backend/app/routers/stream.py:40,55`
**Fix:** Detect content type from file extension:
```python
import mimetypes
media_type = mimetypes.guess_type(str(full_path))[0] or "application/octet-stream"
```

---

### 20. `subtitle_format.convert_ass_to_srt` writes next to original file

In `subtitle_format.py:7`:
```python
srt_path = ass_path.with_suffix(".srt")
```

This writes the converted file next to the original ASS file. If the original is in the media folder (read-only bind mount in some configurations), this will fail. It should write to `TEMP_DIR`.

**File:** `backend/app/services/subtitle_format.py:7`
**Fix:** Write to a temp directory instead.

---

### 21. Progress not actually reported during sync

The `sync_engine.sync()` function calls `_run_ffsubsync()` which uses the synchronous `run_ffsubsync_sync()`. This variant doesn't stream stderr and doesn't invoke any progress callback. The async `run_ffsubsync_with_progress()` exists but is never used.

**File:** `backend/app/services/ffsubsync_runner.py:194-308` (unused), `backend/app/services/sync_engine.py:119-130`
**Impact:** Progress bar will stay at 0% until completion, jumping to 100%.
**Fix:** Use the async progress-reporting version and wire up progress callbacks to the job manager.

---

### 22. `encoding.py` reads entire file into memory

In `encoding.py:9`:
```python
raw_data = f.read()  # reads entire file
```

For large subtitle files this is fine (subtitles are small), but `chardet.detect()` doesn't need the entire file. Reading 10KB is sufficient.

**File:** `backend/app/services/encoding.py:8-9`
**Fix:** `raw_data = f.read(10240)` for efficiency.

---

### 23. `alass_runner.py` has conflicting I/O patterns

The `run_alass()` function has a `read_stream` coroutine defined at line 83 that is never actually called. Instead, lines 111-121 manually read from stdout/stderr in a polling loop. The polling loop also has a race condition: after `process.returncode is None` becomes false, remaining data may not be fully read from the streams.

**File:** `backend/app/services/alass_runner.py:83-94,111-122`
**Impact:** May lose tail-end output from alass. The `read_stream` helper is dead code.
**Fix:** Remove the unused `read_stream` coroutine. Use `process.communicate()` properly or use the `asyncio.gather` pattern like `ffsubsync_runner.py` does.

---

### 24. Frontend file list data shape mismatch

The backend returns:
```json
{"path": "...", "items": [{"name": "...", "file_type": "video", ...}]}
```

But `file-browser.js:38` expects:
```javascript
data.files  // backend sends data.items
```

And line 50 checks `f.type === 'folder'` but the backend sends `file_type: "directory"`.

**File:** `frontend/js/file-browser.js:38,50-52`
**Impact:** File browser will show empty (all files undefined).
**Fix:** Use `data.items` instead of `data.files`, and check `file_type === 'directory'` instead of `type === 'folder'`.

---

### 25. Video player subtitle track iteration may fail

In `preview.js:116`:
```javascript
for (const cue of track.cues) {
```

`track.cues` may be `null` if the track hasn't loaded yet (tracks load asynchronously). This will throw `TypeError: track.cues is not iterable`.

**File:** `frontend/js/preview.js:116`
**Fix:** Guard with `if (!track.cues) return;`.

---

### 26. CSS grid-template-columns missing space

In `style.css:104`:
```css
grid-template-columns: 300px1fr;
```

Missing space between `300px` and `1fr`.

**File:** `frontend/css/style.css:104`
**Impact:** Layout broken -- the grid won't render as a two-column layout.
**Fix:** `grid-template-columns: 300px 1fr;`

Similarly at `style.css:597`:
```css
grid-template-rows: minmax(200px, 300px)1fr;
```

**Fix:** `grid-template-rows: minmax(200px, 300px) 1fr;`

---

### 27. Upload doesn't enforce `MAX_UPLOAD_SIZE` reliably

In `subtitles.py:29`:
```python
if file.size and file.size > settings.MAX_UPLOAD_SIZE:
```

`file.size` may be `None` (it's optional in the multipart spec and depends on the client sending `Content-Length`). Then at line 42:
```python
content = await file.read()
```

This reads the entire file into memory regardless. A malicious client could send a very large file without a `Content-Length` header.

**File:** `backend/app/routers/subtitles.py:29,42`
**Fix:** Read in chunks and enforce the limit:
```python
content = await file.read(settings.MAX_UPLOAD_SIZE + 1)
if len(content) > settings.MAX_UPLOAD_SIZE:
    raise HTTPException(status_code=413, detail="File too large")
```

---

## LOW Issues

### 28. Hardcoded `sys.path.insert` in all test files

Every test file contains:
```python
sys.path.insert(0, "/Users/jon/dev/auto-subs-sync/backend")
```

This is an absolute path that will break on any other machine or CI.

**File:** All test files in `backend/tests/`
**Fix:** Use relative imports, or configure `pytest.ini` with `pythonpath = backend` (pytest >= 7 supports this), or add a `conftest.py` that handles the path.

---

### 29. `config.py` uses deprecated `class Config` pattern

Pydantic v2 uses `model_config` instead of the inner `Config` class.

**File:** `backend/app/config.py:13-14`
**Fix:**
```python
model_config = {"env_file": ".env"}
```

---

### 30. `index.html` has missing spaces in SVG viewBox

Line 13:
```html
viewBox="0 0 2424"
```

Should be `viewBox="0 0 24 24"`.

**File:** `frontend/index.html:13`

---

### 31. Minor typo in `index.html:52`

```html
<p>Select a video fileto begin</p>
```

Missing space: "fileto" should be "file to".

**File:** `frontend/index.html:52`

---

### 32. Missing spaces in footer and time display

`index.html:187`: `0:00 /0:00` should be `0:00 / 0:00`
`index.html:197`: `Sync -Uses` should be `Sync - Uses`

**File:** `frontend/index.html:187,197`

---

### 33. `PROGRESS.md` has contradictory checklist

Lines 120-124 show integration tests as both completed and not-started:
```markdown
- [x] 6.2 Integration tests
  - [x] `test_sync_engine.py` - Sync engine (mocked)
  - [x] `test_api.py` - API endpoint tests
  - [ ] `test_sync_engine.py`
  - [ ] `test_api.py`
```

**File:** `PROGRESS.md:120-124`

---

### 34. `schemas.py:51` uses `.dict()` (Pydantic v1) vs `.model_dump()` (v2)

The `routers/sync.py:51` calls `job.dict()` but with `pydantic-settings>=2.1.0` in requirements, this should be `.model_dump()`. Same for `sync.py:98` with `job.result.dict()`.

**File:** `backend/app/routers/sync.py:51,98`

---

### 35. `requirements.txt` includes test dependencies

`pytest` and `httpx` are in `requirements.txt` rather than in a separate `requirements-dev.txt`. These get installed in the production Docker image.

**File:** `backend/requirements.txt:11-12`

---

### 36. No `conftest.py` for shared test fixtures

Tests repeat setup patterns (temp directories, settings patching). A `conftest.py` with shared fixtures would reduce duplication.

**File:** `backend/tests/`

---

### 37. `docker-compose.yml` uses deprecated `version` key

The `version: "3.8"` key is deprecated in modern Docker Compose.

**File:** `docker-compose.yml:1`

---

## Plan Compliance Summary

| Plan Item | Status | Notes |
|-----------|--------|-------|
| Phase 1: Scaffolding | Implemented | All files present |
| Phase 2: Sync Engines | Implemented | ffsubsync progress not wired up, blocking sync in async context |
| Phase 3: API Endpoints | Implemented | Missing exception handler registration, async/sync mismatch |
| Phase 4: Frontend | Implemented | Multiple broken API URLs, data shape mismatches, CSS bugs |
| Phase 5: Docker | Implemented | Matches plan |
| Phase 6: Tests | Implemented | Hardcoded paths, no conftest |
| WebSocket heartbeat | Partially | Frontend connects to wrong URL |
| Job persistence/crash recovery | Implemented | Re-runs cancelled jobs incorrectly |
| Error handling strategy | Implemented | Exception handler not registered globally |

### Missing from Plan
- **Subtitle upload for ASS/SSA conversion on upload path**: The upload endpoint accepts ASS/SSA files but doesn't convert them to SRT at upload time. The conversion only happens during sync.
- **`Retry-After` header** for 429 responses (Plan: "additional requests return HTTP 429 with retry-after header").
- **Exponential backoff cap** at 30s for WebSocket reconnect (plan says "max 30s", code caps at `maxReconnectAttempts=5`).

---

## Recommended Fix Priority

1. **Immediate (will prevent basic operation):**
   - #6 (dual JobManager instances)
   - #3 (missing await on async get_job)
   - #26 (CSS grid missing space -- layout broken)
   - #24 (frontend data shape mismatch -- file browser broken)
   - #9, #10 (frontend API URL and payload mismatches)
   - #8 (WebSocket wrong URL)
   - #4, #5 (JS runtime errors)

2. **Before deployment:**
   - #13 (blocking sync in async context)
   - #27 (upload size enforcement)
   - #7 (create_job race condition)
   - #11 (re-running cancelled jobs)
   - #12 (cleanup task not stored)
   - #15 (non-existent field)

3. **Quality improvements:**
   - #16, #17, #18, #19, #20, #21 (code architecture)
   - #28, #29, #35, #36 (test/build quality)
   - #30, #31, #32, #33 (cosmetic)
