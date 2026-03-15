import * as api from '../api.js';

const UPLOAD_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="17 8 12 3 7 8"/>
    <line x1="12" y1="3" x2="12" y2="15"/>
</svg>`;

export function createSyncControls(store, wsManager, toast) {
    let cleanupFns = [];
    let wsUnsubscribers = [];

    // DOM refs
    const noSelectionEl = document.getElementById('no-selection');
    const configSectionEl = document.getElementById('config-section');
    const progressSectionEl = document.getElementById('progress-section');
    const resultSectionEl = document.getElementById('result-section');
    const selectedVideoEl = document.getElementById('selected-video');
    const videoNameEl = document.getElementById('video-name');

    const subtitleSourceEl = document.getElementById('subtitle-source');
    const syncEngineEl = document.getElementById('sync-engine');
    const audioTrackGroupEl = document.getElementById('audio-track-group');
    const audioTrackEl = document.getElementById('audio-track');
    const manualOptionsEl = document.getElementById('manual-options');
    const manualOffsetEl = document.getElementById('manual-offset');
    const framerateAdjustEl = document.getElementById('framerate-adjust');
    const syncBtnEl = document.getElementById('sync-btn');

    const progressFillEl = document.getElementById('progress-fill');
    const progressTextEl = document.getElementById('progress-text');
    const progressMessageEl = document.getElementById('progress-message');
    const progressSectionLive = document.getElementById('progress-section');
    const cancelBtnEl = document.getElementById('cancel-sync');

    const resultMessageEl = document.getElementById('result-message');
    const resultIconEl = document.querySelector('.result-icon');
    const previewResultBtn = document.getElementById('preview-result-btn');
    const downloadResultBtn = document.getElementById('download-result-btn');
    const saveResultBtn = document.getElementById('save-result-btn');
    const overwriteToggle = document.getElementById('overwrite-toggle');
    const newSyncBtn = document.getElementById('new-sync-btn');

    const uploadSubtitleBtn = document.getElementById('upload-subtitle-btn');
    const subtitleUploadInput = document.getElementById('subtitle-upload');

    function show(el) { el && el.classList.remove('hidden'); }
    function hide(el) { el && el.classList.add('hidden'); }

    function renderView() {
        const status = store.get('syncStatus');
        const video = store.get('selectedVideo');

        hide(noSelectionEl);
        hide(configSectionEl);
        hide(progressSectionEl);
        hide(resultSectionEl);
        if (selectedVideoEl) hide(selectedVideoEl);

        if (status === 'idle' && !video) {
            show(noSelectionEl);
        } else if (status === 'idle' && video) {
            show(selectedVideoEl);
            show(configSectionEl);
        } else if (status === 'syncing') {
            show(selectedVideoEl);
            show(progressSectionEl);
        } else {
            // completed | failed | cancelled
            show(selectedVideoEl);
            show(resultSectionEl);
        }
    }

    function renderVideoName() {
        const video = store.get('selectedVideo');
        if (videoNameEl && video) videoNameEl.textContent = video.name;
    }

    function renderEngines() {
        if (!syncEngineEl) return;
        const engines = store.get('engines');
        const current = store.get('syncEngine');
        if (!engines.length) return;

        syncEngineEl.innerHTML = '';
        engines.forEach(eng => {
            const opt = document.createElement('option');
            opt.value = eng;
            opt.textContent = eng === 'ffsubsync' ? 'FFsubsync (Recommended)'
                : eng === 'alass' ? 'Alass (Alternative)'
                : eng === 'manual' ? 'Manual Offset'
                : eng;
            syncEngineEl.appendChild(opt);
        });
        syncEngineEl.value = current;
        toggleEngineOptions(current);
    }

    function renderSubtitleSource() {
        if (!subtitleSourceEl) return;
        const subs = store.get('associatedSubtitles');
        const uploaded = store.get('uploadedSubtitle');

        subtitleSourceEl.innerHTML = '<option value="">Select subtitle...</option>';

        subs.forEach(sub => {
            const opt = document.createElement('option');
            opt.value = sub.path;
            opt.textContent = sub.name;
            subtitleSourceEl.appendChild(opt);
        });

        if (uploaded) {
            const opt = document.createElement('option');
            opt.value = `uploaded:${uploaded.tempId}`;
            opt.textContent = uploaded.filename;
            subtitleSourceEl.appendChild(opt);
            subtitleSourceEl.value = opt.value;
        } else if (subs.length === 1) {
            subtitleSourceEl.value = subs[0].path;
        }
    }

    function renderAudioTracks() {
        if (!audioTrackEl) return;
        const tracks = store.get('audioTracks');
        audioTrackEl.innerHTML = '<option value="">Auto-detect</option>';
        tracks.forEach((track, idx) => {
            const opt = document.createElement('option');
            opt.value = track.index;
            const label = track.title || track.language
                ? `Track ${idx + 1}${track.language ? ` (${track.language})` : ''}${track.title ? ` — ${track.title}` : ''}`
                : `Track ${idx + 1}`;
            opt.textContent = label;
            audioTrackEl.appendChild(opt);
        });
    }

    function renderProgress() {
        const progress = store.get('syncProgress');
        const message = store.get('syncMessage');
        const pct = Math.round((progress || 0) * 100);
        if (progressFillEl) progressFillEl.style.width = `${pct}%`;
        if (progressTextEl) progressTextEl.textContent = `${pct}%`;
        if (progressMessageEl) progressMessageEl.textContent = message || '';
        if (progressSectionLive) progressSectionLive.setAttribute('aria-valuenow', pct);
    }

    function renderResult() {
        const status = store.get('syncStatus');
        const result = store.get('syncResult');
        const success = status === 'completed' && result && result.success;

        if (resultIconEl) {
            resultIconEl.classList.toggle('success', success);
            resultIconEl.classList.toggle('error', !success);
        }

        if (resultMessageEl) {
            if (status === 'completed' && success) {
                resultMessageEl.textContent = 'Sync completed successfully!';
            } else if (status === 'completed') {
                resultMessageEl.textContent = result?.error_message || 'Sync failed.';
            } else if (status === 'failed') {
                resultMessageEl.textContent = store.get('syncMessage') || 'Sync failed.';
            } else if (status === 'cancelled') {
                resultMessageEl.textContent = 'Sync was cancelled.';
            }
        }

        // Show/hide download and save buttons based on success
        if (downloadResultBtn) downloadResultBtn.classList.toggle('hidden', !success);
        if (saveResultBtn) saveResultBtn.classList.toggle('hidden', !success);
    }

    function toggleEngineOptions(engine) {
        if (engine === 'manual') {
            show(manualOptionsEl);
            hide(audioTrackGroupEl);
        } else {
            hide(manualOptionsEl);
            show(audioTrackGroupEl);
        }
    }

    async function handleSync() {
        const video = store.get('selectedVideo');
        const engine = store.get('syncEngine');
        const subtitleValue = subtitleSourceEl ? subtitleSourceEl.value : '';

        if (!video) { toast.warning('Please select a video file'); return; }
        if (!subtitleValue && engine !== 'manual') { toast.warning('Please select a subtitle file'); return; }

        const audioTrack = audioTrackEl ? (audioTrackEl.value || null) : null;
        const manualOffset = manualOffsetEl ? (parseInt(manualOffsetEl.value) || 0) : 0;
        const framerateAdjust = framerateAdjustEl ? framerateAdjustEl.value : 'none';

        let sourceFps = null, targetFps = null;
        if (engine === 'manual' && framerateAdjust && framerateAdjust !== 'none') {
            const parts = framerateAdjust.split('-');
            if (parts.length === 2) {
                sourceFps = parseFloat(parts[0]) / 1000;
                targetFps = parseFloat(parts[1]) / 1000;
            }
        }

        const request = {
            video_path: video.path,
            subtitle_path: subtitleValue,
            engine,
            options: {
                audio_track: audioTrack ? parseInt(audioTrack) : null,
                offset_ms: engine === 'manual' ? manualOffset : null,
                source_fps: sourceFps,
                target_fps: targetFps,
            },
        };

        let response;
        try {
            response = await api.startSync(request);
        } catch (err) {
            if (err.status === 429) {
                toast.warning('A sync job is already running');
            } else {
                toast.error(`Failed to start sync: ${err.message}`);
            }
            return;
        }

        store.batch({
            jobId: response.job_id,
            lastJobId: response.job_id,
            syncStatus: 'syncing',
            syncProgress: 0,
            syncMessage: 'Starting...',
            syncResult: null,
        });

        // Clean up previous WS listeners
        wsUnsubscribers.forEach(fn => fn());
        wsUnsubscribers = [];

        wsUnsubscribers.push(wsManager.onStateChange(state => {
            store.set('wsState', state);
        }));

        wsUnsubscribers.push(wsManager.onProgress(data => {
            store.batch({
                syncProgress: (data.percent || 0) / 100,
                syncMessage: data.message || '',
            });
        }));

        wsUnsubscribers.push(wsManager.onComplete(result => {
            store.batch({
                syncStatus: 'completed',
                syncResult: result,
                syncProgress: 1.0,
                syncMessage: 'Complete',
                wsState: 'disconnected',
            });
            wsUnsubscribers.forEach(fn => fn());
            wsUnsubscribers = [];
            if (result && result.success) {
                toast.success('Sync completed successfully!');
            } else {
                toast.error(result?.error_message || 'Sync failed');
            }
        }));

        wsUnsubscribers.push(wsManager.onError(error => {
            store.batch({
                syncStatus: 'failed',
                syncMessage: error?.message || 'Unknown error',
                wsState: 'disconnected',
            });
            wsUnsubscribers.forEach(fn => fn());
            wsUnsubscribers = [];
            toast.error(error?.message || 'Sync failed');
        }));

        wsManager.connect(response.job_id);
    }

    async function handleCancel() {
        const jobId = store.get('jobId');
        wsManager.disconnect();
        wsUnsubscribers.forEach(fn => fn());
        wsUnsubscribers = [];

        if (jobId) {
            try { await api.cancelJob(jobId); } catch { /* ignore */ }
        }

        store.batch({
            syncStatus: 'cancelled',
            syncMessage: 'Cancelled',
            wsState: 'disconnected',
        });
    }

    async function handleDownload() {
        const jobId = store.get('lastJobId');
        if (!jobId) { toast.error('No job to download'); return; }
        try {
            await api.downloadSubtitle(jobId);
        } catch (err) {
            toast.error(`Download failed: ${err.message}`);
        }
    }

    async function handleSave() {
        const jobId = store.get('lastJobId');
        if (!jobId) { toast.error('No job to save'); return; }
        if (saveResultBtn) saveResultBtn.setAttribute('aria-busy', 'true');
        const overwrite = overwriteToggle?.checked ?? false;
        try {
            const result = await api.saveSubtitle(jobId, overwrite);
            const message = overwrite ? 'Overwritten at' : 'Saved to';
            toast.success(`${message} ${result.path}`);
        } catch (err) {
            toast.error(`Save failed: ${err.message}`);
        } finally {
            if (saveResultBtn) saveResultBtn.removeAttribute('aria-busy');
        }
    }

    function handlePreview() {
        // Signal preview component to show synced result
        store.set('previewMode', 'synced');
    }

    function handleNewSync() {
        store.batch({
            syncStatus: 'idle',
            syncProgress: 0,
            syncMessage: '',
            syncResult: null,
        });
        if (overwriteToggle) {
            overwriteToggle.checked = false;
        }
    }

    // Engine change
    function handleEngineChange() {
        const engine = syncEngineEl.value;
        store.set('syncEngine', engine);
        toggleEngineOptions(engine);
    }

    // Upload
    async function handleUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        uploadSubtitleBtn.setAttribute('aria-busy', 'true');
        uploadSubtitleBtn.disabled = true;

        try {
            const result = await api.uploadSubtitle(file);
            store.set('uploadedSubtitle', { tempId: result.temp_id, filename: result.filename });
            toast.success(`Uploaded: ${result.filename}`);
        } catch (err) {
            toast.error(`Upload failed: ${err.message}`);
        } finally {
            uploadSubtitleBtn.removeAttribute('aria-busy');
            uploadSubtitleBtn.disabled = false;
            subtitleUploadInput.value = '';
        }
    }

    // Wire up event handlers
    if (syncEngineEl) {
        syncEngineEl.addEventListener('change', handleEngineChange);
        cleanupFns.push(() => syncEngineEl.removeEventListener('change', handleEngineChange));
    }

    if (syncBtnEl) {
        syncBtnEl.addEventListener('click', handleSync);
        cleanupFns.push(() => syncBtnEl.removeEventListener('click', handleSync));
    }

    if (cancelBtnEl) {
        cancelBtnEl.addEventListener('click', handleCancel);
        cleanupFns.push(() => cancelBtnEl.removeEventListener('click', handleCancel));
    }

    if (downloadResultBtn) {
        downloadResultBtn.addEventListener('click', handleDownload);
        cleanupFns.push(() => downloadResultBtn.removeEventListener('click', handleDownload));
    }

    if (saveResultBtn) {
        saveResultBtn.addEventListener('click', handleSave);
        cleanupFns.push(() => saveResultBtn.removeEventListener('click', handleSave));
    }

    if (previewResultBtn) {
        previewResultBtn.addEventListener('click', handlePreview);
        cleanupFns.push(() => previewResultBtn.removeEventListener('click', handlePreview));
    }

    if (newSyncBtn) {
        newSyncBtn.addEventListener('click', handleNewSync);
        cleanupFns.push(() => newSyncBtn.removeEventListener('click', handleNewSync));
    }

    if (uploadSubtitleBtn && subtitleUploadInput) {
        const handleUploadBtnClick = () => subtitleUploadInput.click();
        uploadSubtitleBtn.addEventListener('click', handleUploadBtnClick);
        subtitleUploadInput.addEventListener('change', handleUpload);
        cleanupFns.push(() => {
            uploadSubtitleBtn.removeEventListener('click', handleUploadBtnClick);
            subtitleUploadInput.removeEventListener('change', handleUpload);
        });
    }

    // Store subscriptions
    cleanupFns.push(store.subscribe('syncStatus', () => { renderView(); renderResult(); }));
    cleanupFns.push(store.subscribe('selectedVideo', () => { renderView(); renderVideoName(); }));
    cleanupFns.push(store.subscribe('engines', renderEngines));
    cleanupFns.push(store.subscribe('syncEngine', () => toggleEngineOptions(store.get('syncEngine'))));
    cleanupFns.push(store.subscribe('associatedSubtitles', renderSubtitleSource));
    cleanupFns.push(store.subscribe('uploadedSubtitle', renderSubtitleSource));
    cleanupFns.push(store.subscribe('audioTracks', renderAudioTracks));
    cleanupFns.push(store.subscribe('syncProgress', renderProgress));
    cleanupFns.push(store.subscribe('syncMessage', renderProgress));
    cleanupFns.push(store.subscribe('syncResult', renderResult));

    // Initial render
    renderView();

    return {
        destroy() {
            wsUnsubscribers.forEach(fn => fn());
            wsUnsubscribers = [];
            cleanupFns.forEach(fn => fn());
            cleanupFns = [];
        }
    };
}
