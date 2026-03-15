# Frontend Rewrite Plan

## Context

The current frontend (`frontend/`) is a functional prototype with critical bugs and poor architecture: the download feature is broken (passes file path instead of job ID), subtitle preview only works when the video is paused, WebSocket connections leak, fetch calls have no timeouts, errors fail silently, and there's no cleanup of event listeners. The codebase needs a full rewrite with proper architecture while staying vanilla HTML/CSS/JS per the project's no-build-step philosophy.

---

## File Structure

```
frontend/
  index.html                        # Semantic HTML shell with ARIA attributes
  css/
    style.css                       # Single CSS file: variables, base, layout, components, utilities
  js/
    app.js                          # Entry point: bootstraps store, components, cleanup
    store.js                        # NEW — Reactive pub/sub state store
    api.js                          # Rewritten — Fetch with AbortController timeouts, ApiError class
    ws.js                           # NEW — WebSocket lifecycle manager (connect/disconnect/heartbeat/reconnect)
    components/
      file-browser.js               # File browser with keyboard navigation
      sync-controls.js              # Sync config form, progress, results, save/download
      preview.js                    # Video player with working subtitle overlay during playback
      header.js                     # NEW — Connection status indicator + health check
      toast.js                      # NEW — Toast notification system (replaces alert())
```

---

## Architecture

### State Management (`store.js`)
Reactive pub/sub store — components subscribe to specific keys and re-render only when their data changes. No more `window.dispatchEvent(CustomEvent)` for cross-component communication.

```
store.set(key, value)        → shallow equality check, notify subscribers of that key
store.get(key)               → read current value
store.subscribe(key, cb)     → returns unsubscribe function (tracked for cleanup)
store.batch({key: val, ...}) → atomic multi-key update
```

**State shape:**
- Navigation: `currentPath`, `files`, `filesLoading`, `filesError`
- Selection: `selectedVideo`, `associatedSubtitles`, `selectedSubtitle`, `uploadedSubtitle`
- Sync config: `engines`, `defaultEngine`, `syncEngine`, `audioTracks`, `audioTrack`, `manualOffset`, `framerateAdjust`
- Sync job: `syncStatus` (idle|syncing|completed|failed|cancelled), `syncProgress`, `syncMessage`, `jobId`, `lastJobId`, `syncResult`
- Connection: `apiConnected`, `wsState`

### Component Pattern
Every component follows: receive `store` + `api` → subscribe to keys → return `{ destroy() }` that cleans up all listeners and subscriptions.

```javascript
export function createComponentName(store, api) {
    let cleanupFns = [];

    // DOM references (cached once)
    const el = document.getElementById('...');

    // Subscribe to store
    cleanupFns.push(store.subscribe('key', (value) => { render(); }));

    // Event handlers (tracked for cleanup)
    function handleClick(e) { ... }
    el.addEventListener('click', handleClick);
    cleanupFns.push(() => el.removeEventListener('click', handleClick));

    // Render function
    function render() { ... }

    return {
        destroy() { cleanupFns.forEach(fn => fn()); cleanupFns = []; }
    };
}
```

### Communication Flow
```
User Action → Component Handler → api.call() or store.set()
                                       ↓              ↓
                                  API returns    Store notifies
                                       ↓         subscribers
                                  store.set()        ↓
                                  with result    Components re-render
```

---

## Backend API Contract Reference

All file paths in the API are relative to the backend's `MEDIA_PATH`. The app supports a `BASE_PATH` env var for reverse proxy deployments — the frontend detects this from `window.location.pathname`.

### Files Router (`/api/files`)
```
GET  /api/files?path=                        → { path, items: [{ name, path, is_dir, size, modified, file_type }] }
GET  /api/files/info?path=                   → { duration, video_codec, audio_tracks: [{ index, codec, language, channels, title }], file_path }
GET  /api/files/audio-tracks?path=           → { tracks: [{ index, codec, language, channels, title }] }
GET  /api/files/associated-subtitles?video_path= → { subtitles: [{ name, path, is_dir, size, modified, file_type }] }
```

### Sync Router (`/api/sync`)
```
GET    /api/sync/engines                     → { engines: ["ffsubsync", "alass", "manual"], default: "ffsubsync" }
POST   /api/sync                             → { job_id, status: "started" }  (429 if job running)
  Body: { video_path, subtitle_path, engine, options: { audio_track, framerate, offset_ms, source_fps, target_fps } }
GET    /api/sync/{job_id}                    → { id, status, progress, message, video_path, subtitle_path, engine, options, result, created_at, updated_at, logs }
DELETE /api/sync/{job_id}                    → { status: "cancelled" }
WS     /api/sync/{job_id}/ws                 → messages:
  Server sends: { type: "progress", percent: float, message: str }
  Server sends: { type: "complete", result: { success, output_path, error_message, logs } }
  Server sends: { type: "error", error: { code, message, details } }
  Server sends: { type: "pong" }
  Client sends: "ping" (text)
```

### Subtitles Router (`/api/subtitles`)
```
POST /api/subtitles/upload                   → { temp_id, filename, size }  (multipart/form-data, max 10MB, .srt/.ass/.ssa)
GET  /api/subtitles/download/{job_id}        → file download (application/x-subrip)
POST /api/subtitles/save/{job_id}?overwrite= → { status: "saved", path }
```

### Stream Router (`/api/stream`)
```
GET /api/stream/video?path=                  → video stream (supports Range requests for seeking)
GET /api/stream/subtitle?path=&format=vtt    → subtitle content (converts SRT→VTT when format=vtt)
```

### Health
```
GET /api/health                              → { status: "ok" }
```

### Error Format
All errors follow: `{ error: { code, message, details } }`

Error codes: `video_not_found`, `subtitle_not_found`, `subtitle_parse_error`, `unsupported_format`, `no_audio_stream`, `sync_failed`, `sync_timeout`, `engine_not_available`, `job_not_found`, `job_already_running`, `invalid_path`, `encoding_error`, `internal_error`

---

## Key Bugs Fixed

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Download passes file path instead of job_id | `state.lastSyncedFile` is a path, not a job_id | Store `lastJobId` from sync response, use it for download/save |
| Subtitle overlay only renders when paused | `preview.js` has `if (!videoPlayerEl.paused) return;` | `requestAnimationFrame` loop reads `activeCues` during playback |
| WebSocket orphaned connections | No terminal state tracking, reconnects after completion | `ws.js` tracks `isTerminal`, stops reconnecting after complete/error |
| No fetch timeouts | No AbortController | Every fetch uses AbortController with per-endpoint timeouts |
| Silent failures | Uses `alert()` or `console.error()` | Toast notification system with error/success/warning variants |
| Memory leaks | Event listeners on `window` never removed, `setInterval` never cleared | Every listener/subscription tracked in cleanup array, removed on `destroy()` |
| WS message format mismatch | Frontend reads `data.payload` but backend sends top-level `percent`/`message` | `ws.js` reads `data.percent` and `data.message` directly |
| Health check interval never cleared | `setInterval` has no cleanup | `header.js` cleanup clears the interval |

---

## Implementation Steps

### Step 1 — `js/store.js` (new file, ~70 lines)

Reactive pub/sub store. `createStore(initialState)` returns `{ get, set, batch, subscribe, getState, destroy }`.

- `set(key, value)`: Shallow equality check (`===`), skip if unchanged, notify subscribers of that key
- `subscribe(key, callback)`: Returns unsubscribe function. Callback receives `(newValue, oldValue)`
- `batch(updates)`: Takes object `{ key1: val1, key2: val2 }`, sets all values, notifies once per changed key
- `getState()`: Returns shallow copy of full state (for debugging)
- `destroy()`: Clears all subscriptions

**Initial state:**
```javascript
{
    currentPath: '',
    files: [],
    filesLoading: false,
    filesError: null,
    selectedVideo: null,
    associatedSubtitles: [],
    selectedSubtitle: null,
    uploadedSubtitle: null,        // { tempId, filename }
    engines: [],
    defaultEngine: 'ffsubsync',
    syncEngine: 'ffsubsync',
    audioTracks: [],
    audioTrack: null,
    manualOffset: 0,
    framerateAdjust: 'none',
    syncStatus: 'idle',            // idle | syncing | completed | failed | cancelled
    syncProgress: 0,
    syncMessage: '',
    jobId: null,
    lastJobId: null,
    syncResult: null,
    apiConnected: false,
    wsState: 'disconnected',       // disconnected | connecting | connected
}
```

---

### Step 2 — `js/api.js` (rewrite, ~160 lines)

API client with timeouts and structured error handling.

**Core utility:**
```javascript
class ApiError extends Error {
    constructor(status, error) {
        super(error?.message || 'Unknown error');
        this.status = status;
        this.code = error?.code || 'unknown';
        this.details = error?.details || {};
    }
}

async function fetchJSON(url, options = {}, timeoutMs = 15000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        if (!response.ok) {
            const body = await response.json().catch(() => null);
            throw new ApiError(response.status, body?.error || { message: response.statusText });
        }
        return response.json();
    } finally {
        clearTimeout(timeoutId);
    }
}
```

**Base path detection** (carried over from existing code):
```javascript
function getBasePath() {
    const pathParts = window.location.pathname.split('/').filter(Boolean);
    if (pathParts.length > 0 && !pathParts[0].includes('.')) {
        return '/' + pathParts[0];
    }
    return '';
}
```

**Exported functions with timeouts:**
- `getFiles(path)` — 10s
- `getFileInfo(path)` — 15s (ffprobe can be slow)
- `getAudioTracks(path)` — 15s
- `getAssociatedSubtitles(videoPath)` — 10s
- `getEngines()` — 5s
- `startSync(request)` — 15s
- `getJobStatus(jobId)` — 10s
- `cancelJob(jobId)` — 10s
- `uploadSubtitle(file)` — 30s (FormData, no explicit Content-Type header)
- `downloadSubtitle(jobId)` — 30s (returns blob via `fetchBlob()` helper, triggers browser download)
- `saveSubtitle(jobId, overwrite)` — 15s
- `checkHealth()` — 5s
- `getVideoUrl(path)` — returns URL string (no fetch)
- `getSubtitleUrl(path, format='vtt')` — returns URL string (no fetch)
- `getBasePath()` — exported for WebSocket URL construction

---

### Step 3 — `js/ws.js` (new file, ~110 lines)

WebSocket lifecycle manager with proper terminal state handling.

**`createWebSocketManager(basePath)`** returns `{ connect, disconnect, onProgress, onComplete, onError, onStateChange, destroy }`

**Internal state:** `socket`, `heartbeatTimer`, `reconnectTimer`, `reconnectAttempts`, `jobId`, `isTerminal`, `callbacks` (map of arrays)

**Behavior:**
- `connect(jobId)`: Close existing socket first. Build URL: `${ws/wss}://${host}${basePath}/api/sync/${jobId}/ws`. Set `isTerminal = false`, `reconnectAttempts = 0`. Open WebSocket.
- On `open`: Start heartbeat (send `"ping"` every 25s). Invoke `onStateChange` callbacks with `'connected'`.
- On `message`: Parse JSON. Route by `data.type`:
  - `'progress'`: Invoke callbacks with `{ percent: data.percent, message: data.message }` — note: backend sends `percent` at top level, NOT nested in `payload`
  - `'complete'`: Set `isTerminal = true`. Invoke callbacks with `data.result`. Close socket.
  - `'error'`: Set `isTerminal = true`. Invoke callbacks with `data.error`. Close socket.
  - `'pong'`: No-op.
- On `close`: Stop heartbeat. If NOT `isTerminal` and `reconnectAttempts < 5`: schedule reconnect with exponential backoff (`Math.min(1000 * 2^attempts, 30000)`). Invoke `onStateChange` with `'disconnected'`.
- `disconnect()`: Set `isTerminal = true`. Close socket. Clear all timers. Reset state.
- Each `onX(callback)` method returns an unsubscribe function.
- `destroy()`: Call `disconnect()`. Clear all callback arrays.

---

### Step 4 — `css/style.css` (rewrite, ~700 lines)

Keep the dark color scheme and visual language. Fix structural issues.

**New custom properties:**
```css
:root {
    /* Keep existing color palette */
    --focus-ring: 2px solid var(--accent-primary);
    --focus-offset: 2px;
    --space-xs: 0.25rem;
    --space-sm: 0.5rem;
    --space-md: 1rem;
    --space-lg: 1.5rem;
    --space-xl: 2rem;
    --sidebar-width: 300px;
}
```

**Key fixes:**
- Replace `max-height: calc(100vh - 300px)` on `.sync-controls` with flex-based sizing (`flex: 1; min-height: 0; overflow-y: auto`)
- Replace fixed preview dimensions with `aspect-ratio: 16/9; max-height: 50vh`
- Add `*:focus-visible { outline: var(--focus-ring); outline-offset: var(--focus-offset); }` for keyboard navigation
- Add toast styles: `.toast-container` fixed top-right, `.toast` with slide-in animation, color variants
- Add `.btn[aria-busy="true"]` spinner state (disable pointer-events, show inline spinner)
- Add `.sr-only` class for screen-reader-only text
- Keep responsive breakpoints: `>1024px` two-column, `768-1024px` single column with collapsed file browser, `<768px` tighter padding
- Firefox scrollbar support: `scrollbar-color` and `scrollbar-width`

---

### Step 5 — `js/components/toast.js` (new file, ~60 lines)

Toast notification system replacing `alert()`.

**`createToast()`** returns `{ success, error, warning, info, destroy }`

- `success(message, duration=4000)`: Green toast, auto-dismiss
- `error(message, duration=8000)`: Red toast, longer duration, dismiss button
- `warning(message, duration=6000)`: Yellow toast
- `info(message, duration=4000)`: Default blue toast
- Max 5 visible toasts; oldest removed when exceeded
- Each toast gets `role="alert"` for screen reader announcements
- Auto-remove from DOM after dismiss animation

---

### Step 6 — `index.html` (rewrite)

Same two-panel layout (file browser left, controls+preview right) with header and footer.

**Changes from current:**
- Add ARIA attributes throughout:
  - `role="navigation"` on breadcrumb
  - `role="listbox"` on file list container, `role="option"` on file items
  - `aria-live="polite"` on progress section
  - `aria-label` on all icon-only buttons (refresh, play/pause, upload)
- Add `<div id="toast-container" class="toast-container" aria-live="assertive"></div>` before `</body>`
- Add "Save to folder" button in result actions section (alongside existing Download)
- Use `<script type="module" src="js/app.js">` (ES modules for clean imports)
- Video player gets `aria-label="Video preview"`
- Subtitle overlay keeps `aria-hidden="true"` (decorative; the `<track>` element provides accessible subtitles)

---

### Step 7 — `js/app.js` (rewrite, ~70 lines)

Entry point that bootstraps everything.

```javascript
import { createStore } from './store.js';
import * as api from './api.js';
import { createWebSocketManager } from './ws.js';
import { createFileBrowser } from './components/file-browser.js';
import { createSyncControls } from './components/sync-controls.js';
import { createPreview } from './components/preview.js';
import { createHeader } from './components/header.js';
import { createToast } from './components/toast.js';

function init() {
    const store = createStore({ /* initial state */ });
    const wsManager = createWebSocketManager(api.getBasePath());
    const toast = createToast();

    // Fetch available engines on startup
    api.getEngines()
        .then(data => store.batch({ engines: data.engines, defaultEngine: data.default, syncEngine: data.default }))
        .catch(() => toast.warning('Could not load sync engines'));

    // Initialize components
    const components = [
        createHeader(store, api),
        createFileBrowser(store, api, toast),
        createSyncControls(store, api, wsManager, toast),
        createPreview(store, api),
    ];

    // Global unhandled promise rejection handler
    window.addEventListener('unhandledrejection', (e) => {
        console.error('Unhandled rejection:', e.reason);
        toast.error('An unexpected error occurred');
        e.preventDefault();
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        wsManager.destroy();
        components.forEach(c => c.destroy());
    });
}

document.addEventListener('DOMContentLoaded', init);
```

---

### Step 8 — `js/components/header.js` (new file, ~50 lines)

Connection status indicator and health check polling.

- Subscribes to `apiConnected`, `wsState`
- Runs `api.checkHealth()` every 30s; updates `store.set('apiConnected', true/false)`
- Renders status dot + text:
  - Green "Ready": `apiConnected && wsState !== 'connected'`
  - Yellow pulsing "Syncing": `wsState === 'connected'`
  - Red "Disconnected": `!apiConnected`
- Cleanup clears the health check interval

---

### Step 9 — `js/components/file-browser.js` (rewrite, ~180 lines)

**Subscribes to:** `currentPath`, `files`, `filesLoading`, `filesError`, `selectedVideo`

**Key functions:**
- `loadFiles(path)`: Sets `filesLoading: true, filesError: null` via batch. Calls `api.getFiles(path)`. On success: batch-set `files`, `currentPath`, `filesLoading: false`. On error: set `filesError` + show toast.
- `render()`: Sort files (directories first, then videos, then subtitles, then other). Render each as a clickable item with type icon. Highlight selected video. Show nested subtitles under their parent video.
- `renderBreadcrumb()`: Build clickable breadcrumb segments from `currentPath`.
- `handleFileClick(file)`:
  - **Directory**: Navigate immediately (single click, not double-click like current)
  - **Video**: Set `selectedVideo` in store. Fetch associated subtitles + audio tracks in parallel:
    ```javascript
    const [subsResult, tracksResult] = await Promise.allSettled([
        api.getAssociatedSubtitles(file.path),
        api.getAudioTracks(file.path)
    ]);
    store.batch({
        associatedSubtitles: subsResult.status === 'fulfilled' ? subsResult.value.subtitles : [],
        audioTracks: tracksResult.status === 'fulfilled' ? tracksResult.value.tracks : [],
        selectedSubtitle: null,
        uploadedSubtitle: null,
    });
    ```
  - **Subtitle**: Set `selectedSubtitle` in store (quick-select)
- `handleKeyDown(e)`: Arrow up/down to navigate file list, Enter to activate. Roving tabindex pattern: only the focused item has `tabindex="0"`, others have `tabindex="-1"`.
- Loading state: Show spinner in file list area
- Error state: Show error message with retry button

---

### Step 10 — `js/components/sync-controls.js` (rewrite, ~280 lines)

Largest component. Handles sync configuration, execution, progress, and results.

**Subscribes to:** `selectedVideo`, `associatedSubtitles`, `syncEngine`, `syncStatus`, `syncProgress`, `syncMessage`, `syncResult`, `engines`, `audioTracks`, `uploadedSubtitle`

**UI sections (show/hide based on `syncStatus`):**
1. **No selection** (`syncStatus === 'idle' && !selectedVideo`): "Select a video" prompt
2. **Config form** (`syncStatus === 'idle' && selectedVideo`):
   - Selected video display
   - Subtitle source dropdown (populated from `associatedSubtitles` + uploaded if present)
   - Upload button (with `aria-busy` during upload)
   - Engine dropdown (populated from `engines` API, not hardcoded)
   - Audio track dropdown (populated from `audioTracks`, hidden when engine is `manual`)
   - Manual offset (ms) input + framerate dropdown (shown only when engine is `manual`)
   - "Sync" button
3. **Progress** (`syncStatus === 'syncing'`):
   - Progress bar (width from `syncProgress`, `aria-valuenow` for accessibility)
   - Progress message text
   - Cancel button
4. **Results** (`syncStatus === 'completed' || 'failed' || 'cancelled'`):
   - Success/failure icon + message
   - "Preview" button (dispatches to preview component via `store.set`)
   - "Download" button → `api.downloadSubtitle(store.get('lastJobId'))` ← FIXES THE BUG
   - "Save to folder" button → `api.saveSubtitle(store.get('lastJobId'), false)` (new feature)
   - "New sync" button → resets to config form

**Sync flow:**
1. Validate: video selected, subtitle chosen (except manual mode which only needs offset/framerate)
2. Build request body matching `SyncRequest` schema:
   ```javascript
   {
       video_path: selectedVideo.path,
       subtitle_path: resolveSubtitlePath(),  // handle uploaded:{tempId} format
       engine: store.get('syncEngine'),
       options: {
           audio_track: store.get('audioTrack'),
           offset_ms: engine === 'manual' ? store.get('manualOffset') : null,
           source_fps: engine === 'manual' ? parsedSourceFps : null,
           target_fps: engine === 'manual' ? parsedTargetFps : null,
       }
   }
   ```
3. Call `api.startSync(request)`. On success: `store.batch({ jobId: response.job_id, lastJobId: response.job_id, syncStatus: 'syncing', syncProgress: 0 })`
4. Connect WebSocket: `wsManager.connect(response.job_id)`
5. Register WebSocket callbacks (updating store, which triggers reactive re-renders):
   - `onProgress` → `store.batch({ syncProgress: data.percent, syncMessage: data.message })`
   - `onComplete` → `store.batch({ syncStatus: 'completed', syncResult: data, syncProgress: 1.0, syncMessage: 'Complete' })`
   - `onError` → `store.batch({ syncStatus: 'failed', syncMessage: data.message })` + `toast.error(data.message)`
6. Handle 429 → `toast.warning('A sync job is already running')`

**Upload flow:**
1. Set upload button `aria-busy="true"`
2. Call `api.uploadSubtitle(file)`
3. On success: `store.set('uploadedSubtitle', { tempId: response.temp_id, filename: response.filename })`
4. Add to subtitle dropdown as `uploaded:{tempId}` with filename display
5. Auto-select the uploaded subtitle
6. On error: `toast.error('Upload failed: ' + err.message)`
7. Reset button state

---

### Step 11 — `js/components/preview.js` (rewrite, ~170 lines)

Video player with subtitle overlay that works during playback.

**Subscribes to:** `selectedVideo`, `selectedSubtitle`, `syncResult`, `syncStatus`

**Key functions:**
- `loadVideo(videoPath)`: Set `<video>` src to `api.getVideoUrl(videoPath)`. Show player, hide placeholder.
- `loadSubtitle(subtitlePath)`: Remove existing `<track>` element. Create new `<track kind="subtitles" src="...">`. Set `track.mode = 'hidden'` (we render our own overlay). Wait for `track.oncuechange` to be available.
- `startOverlayLoop()`: Called on video `play` event.
  ```javascript
  function updateOverlay() {
      const track = videoEl.textTracks[0];
      if (track && track.activeCues && track.activeCues.length > 0) {
          const text = Array.from(track.activeCues).map(c => c.text).join('<br>');
          overlayEl.innerHTML = text;
          overlayEl.classList.remove('hidden');
      } else {
          overlayEl.classList.add('hidden');
      }
      animFrameId = requestAnimationFrame(updateOverlay);
  }
  animFrameId = requestAnimationFrame(updateOverlay);
  ```
- `stopOverlayLoop()`: Called on video `pause`/`ended`. Cancel animation frame but do NOT clear overlay (keeps showing current subtitle while paused).
- `handleToggle(showSynced)`:
  - Original: Load subtitle from `store.get('selectedSubtitle').path`
  - Synced: Load subtitle from sync result via `api.getSubtitleUrl(syncResult.output_path, 'vtt')`
  - Toggle button active states

**Player controls:**
- Play/pause button with icon swap
- Seek bar (range input, updates on `timeupdate`)
- Time display (MM:SS / MM:SS)
- Subtitle toggle buttons (Original | Synced) — synced only shown after successful sync

**Error handling:**
- Video `error` event: Show error message in player area, hide controls
- Track load failure: Show toast, fall back to no subtitles

---

### Step 12 — Integration Testing

Full end-to-end verification:

1. **Browse files**: Navigate folders via file browser, verify breadcrumb updates, click video selects it
2. **Subtitle detection**: Selecting a video auto-populates associated subtitles in dropdown
3. **Upload subtitle**: Upload .srt/.ass file, verify it appears in dropdown and is auto-selected
4. **Run sync**: Start ffsubsync sync, verify progress bar animates via WebSocket, verify completion toast
5. **429 handling**: Start a second sync while one is running, verify warning toast
6. **Cancel sync**: Start sync, cancel mid-progress, verify job stops and UI resets to config
7. **Preview during playback**: Play video with synced subtitles, verify overlay shows cues while video is playing (not just paused)
8. **Subtitle toggle**: Switch between original and synced subtitles in preview
9. **Download**: Click download, verify browser downloads the .srt file (using `lastJobId`)
10. **Save**: Click "Save to folder", verify success toast with saved path
11. **Error handling**: Disconnect network, verify toast shows error and status goes to "Disconnected"
12. **Keyboard navigation**: Tab through file browser, arrow keys to navigate, Enter to select, Tab to sync controls
13. **Responsive**: Verify layout at desktop (>1024px), tablet (768-1024px), mobile (<768px)
14. **Cleanup**: Navigate away, verify no console errors about leaked listeners or WebSocket connections
15. **Base path**: Test with `BASE_PATH` set to verify reverse proxy deployment works
