export function initSyncControls(state, api) {
    const noSelectionEl = document.getElementById('no-selection');
    const selectedVideoEl = document.getElementById('selected-video');
    const videoNameEl = document.getElementById('video-name');
    const configSectionEl = document.getElementById('config-section');
    const progressSectionEl = document.getElementById('progress-section');
    const resultSectionEl = document.getElementById('result-section');
    const progressFillEl = document.getElementById('progress-fill');
    const progressTextEl = document.getElementById('progress-text');
    const progressMessageEl = document.getElementById('progress-message');
    
    const subtitleSourceEl = document.getElementById('subtitle-source');
    const syncEngineEl = document.getElementById('sync-engine');
    const audioTrackEl = document.getElementById('audio-track');
    const manualOptionsEl = document.getElementById('manual-options');
    const manualOffsetEl = document.getElementById('manual-offset');
    const framerateAdjustEl = document.getElementById('framerate-adjust');
    const syncBtnEl = document.getElementById('sync-btn');
    const cancelBtnEl = document.getElementById('cancel-sync');
    const previewResultBtn = document.getElementById('preview-result-btn');
    const downloadResultBtn = document.getElementById('download-result-btn');

    function showConfig(video) {
        noSelectionEl.classList.add('hidden');
        selectedVideoEl.classList.remove('hidden');
        configSectionEl.classList.remove('hidden');
        progressSectionEl.classList.add('hidden');
        resultSectionEl.classList.add('hidden');
        
        videoNameEl.textContent = video.name;
        
        populateSubtitleSource(video.subtitles || []);
        populateAudioTracks(video.audioTracks || []);
    }

    function hideConfig() {
        noSelectionEl.classList.remove('hidden');
        selectedVideoEl.classList.add('hidden');
        configSectionEl.classList.add('hidden');
        progressSectionEl.classList.add('hidden');
        resultSectionEl.classList.add('hidden');
    }

    function populateSubtitleSource(subtitles) {
        subtitleSourceEl.innerHTML = '<option value="">Select subtitle...</option>';
        
        subtitles.forEach((sub, index) => {
            const option = document.createElement('option');
            option.value = sub.path;
            option.textContent = sub.name;
            subtitleSourceEl.appendChild(option);
        });
        
        if (subtitles.length === 1) {
            subtitleSourceEl.value = subtitles[0].path;
            state.setSelectedSubtitle(subtitles[0]);
        }
    }

    function populateAudioTracks(tracks) {
        audioTrackEl.innerHTML = '<option value="">Auto-detect</option>';
        
        tracks.forEach((track, index) => {
            const option = document.createElement('option');
            option.value = track.index;
            option.textContent = track.name || `Track ${index + 1}${track.language ? ` (${track.language})` : ''}`;
            audioTrackEl.appendChild(option);
        });
    }

    function showProgress() {
        configSectionEl.classList.add('hidden');
        progressSectionEl.classList.remove('hidden');
        resultSectionEl.classList.add('hidden');
        
        updateProgress({ progress: 0, message: 'Initializing...' });
    }

    function updateProgress(data) {
        const progress = data.progress || 0;
        const message = data.message || '';
        
        progressFillEl.style.width = `${progress}%`;
        progressTextEl.textContent = `${Math.round(progress)}%`;
        progressMessageEl.textContent = message;
    }

    function showResult(success, message) {
        progressSectionEl.classList.add('hidden');
        resultSectionEl.classList.remove('hidden');
        
        const resultMessageEl = document.getElementById('result-message');
        const resultIcon = resultSectionEl.querySelector('.result-icon');
        
        resultMessageEl.textContent = message;
        
        if (success) {
            resultIcon.classList.remove('error');
            resultIcon.classList.add('success');
        } else {
            resultIcon.classList.remove('success');
            resultIcon.classList.add('error');
        }
    }

    async function handleSync() {
        const video = state.selectedVideo;
        const subtitlePath = subtitleSourceEl.value;
        const engine = syncEngineEl.value;
        const audioTrack = audioTrackEl.value;
        const manualOffset = parseInt(manualOffsetEl.value) || 0;
        const framerateAdjust = framerateAdjustEl.value;
        
        if (!video) {
            alert('Please select a video file');
            return;
        }
        
        if (!subtitlePath && engine !== 'manual') {
            alert('Please select a subtitle file');
            return;
        }
        
        state.setSyncStatus('syncing');
        showProgress();
        
        try {
            const result = await api.syncSubtitle({
                videoPath: video.path,
                subtitlePath: subtitlePath,
                engine: engine,
                audioTrack: audioTrack || null,
                manualOffset: manualOffset,
                framerateAdjust: framerateAdjust
            });
            
            state.setLastSyncedFile(result.outputPath);
            showResult(true, 'Sync completed successfully!');
        } catch (error) {
            showResult(false, `Sync failed: ${error.message}`);
        }
        
        state.setSyncStatus('idle');
    }

    function handleCancel() {
        api.cancelSync();
        state.setSyncStatus('idle');
        showConfig(state.selectedVideo);
    }

    if (syncEngineEl) {
        syncEngineEl.addEventListener('change', () => {
            const engine = syncEngineEl.value;
            state.setSyncEngine(engine);
            
            if (engine === 'manual') {
                manualOptionsEl.classList.remove('hidden');
                document.getElementById('audio-track-group').classList.add('hidden');
            } else {
                manualOptionsEl.classList.add('hidden');
                document.getElementById('audio-track-group').classList.remove('hidden');
            }
        });
    }

    if (subtitleSourceEl) {
        subtitleSourceEl.addEventListener('change', () => {
            const selectedPath = subtitleSourceEl.value;
            const sub = state.associatedSubtitles.find(s => s.path === selectedPath);
            state.setSelectedSubtitle(sub);
        });
    }

    if (syncBtnEl) {
        syncBtnEl.addEventListener('click', handleSync);
    }

    if (cancelBtnEl) {
        cancelBtnEl.addEventListener('click', handleCancel);
    }

    if (previewResultBtn) {
        previewResultBtn.addEventListener('click', () => {
            window.dispatchEvent(new CustomEvent('previewResult', {
                detail: {
                    video: state.selectedVideo,
                    syncedSubtitle: state.lastSyncedFile
                }
            }));
        });
    }

    if (downloadResultBtn) {
        downloadResultBtn.addEventListener('click', async () => {
            try {
                const blob = await api.downloadSubtitle(state.lastSyncedFile);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = state.lastSyncedFile.split('/').pop();
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } catch (error) {
                alert(`Failed to download: ${error.message}`);
            }
        });
    }

    window.addEventListener('videoSelected', (e) => {
        showConfig(e.detail);
    });

    return {
        showConfig,
        hideConfig,
        showProgress,
        updateProgress,
        showResult
    };
}