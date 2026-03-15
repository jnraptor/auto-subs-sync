import * as api from '../api.js';

export function createPreview(store) {
    let cleanupFns = [];
    let animFrameId = null;

    const noVideoEl = document.getElementById('no-video');
    const playerWrapperEl = document.getElementById('video-player-wrapper');
    const videoEl = document.getElementById('video-player');
    const overlayEl = document.getElementById('subtitle-overlay');
    const playPauseBtn = document.getElementById('play-pause');
    const playIcon = document.getElementById('play-icon');
    const pauseIcon = document.getElementById('pause-icon');
    const seekBarEl = document.getElementById('seek-bar');
    const timeDisplayEl = document.getElementById('time-display');
    const subtitleToggleEl = document.getElementById('subtitle-toggle');
    const showOriginalBtn = document.getElementById('show-original');
    const showSyncedBtn = document.getElementById('show-synced');

    function formatTime(seconds) {
        if (!isFinite(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function loadVideo(videoPath) {
        if (!videoEl) return;
        noVideoEl && noVideoEl.classList.add('hidden');
        playerWrapperEl && playerWrapperEl.classList.remove('hidden');
        videoEl.src = api.getVideoUrl(videoPath);
        videoEl.load();
    }

    function loadSubtitle(subtitlePath) {
        if (!videoEl) return;
        // Remove existing tracks
        while (videoEl.textTracks.length > 0) {
            const track = videoEl.querySelector('track');
            if (track) track.parentNode.removeChild(track);
            else break;
        }

        if (!subtitlePath) {
            stopOverlayLoop();
            if (overlayEl) overlayEl.innerHTML = '';
            return;
        }

        const track = document.createElement('track');
        track.kind = 'subtitles';
        track.srclang = 'en';
        track.label = 'Subtitles';
        track.src = api.getSubtitleUrl(subtitlePath, 'vtt');
        track.default = true;
        videoEl.appendChild(track);

        // Hide native rendering — we use our own overlay
        track.addEventListener('load', () => {
            if (videoEl.textTracks[0]) videoEl.textTracks[0].mode = 'hidden';
        });

        track.addEventListener('error', () => {
            // Non-fatal — subtitle simply won't display
        });
    }

    function loadSubtitleUrl(url) {
        if (!videoEl) return;
        while (videoEl.querySelector('track')) {
            videoEl.removeChild(videoEl.querySelector('track'));
        }
        const track = document.createElement('track');
        track.kind = 'subtitles';
        track.srclang = 'en';
        track.label = 'Subtitles';
        track.src = url;
        track.default = true;
        videoEl.appendChild(track);
        track.addEventListener('load', () => {
            if (videoEl.textTracks[0]) videoEl.textTracks[0].mode = 'hidden';
        });
    }

    function startOverlayLoop() {
        if (animFrameId) return;
        function updateOverlay() {
            if (!videoEl) return;
            const track = videoEl.textTracks[0];
            if (track && track.activeCues && track.activeCues.length > 0) {
                const text = Array.from(track.activeCues).map(c => c.text).join('<br>');
                if (overlayEl) {
                    overlayEl.innerHTML = `<span class="subtitle-text">${text}</span>`;
                    overlayEl.classList.remove('hidden');
                }
            } else {
                if (overlayEl) overlayEl.classList.add('hidden');
            }
            animFrameId = requestAnimationFrame(updateOverlay);
        }
        animFrameId = requestAnimationFrame(updateOverlay);
    }

    function stopOverlayLoop() {
        if (animFrameId) {
            cancelAnimationFrame(animFrameId);
            animFrameId = null;
        }
        // Keep last cue visible while paused — don't clear overlay
    }

    function updatePlayPauseButton() {
        if (!videoEl) return;
        if (videoEl.paused) {
            playIcon && playIcon.classList.remove('hidden');
            pauseIcon && pauseIcon.classList.add('hidden');
        } else {
            playIcon && playIcon.classList.add('hidden');
            pauseIcon && pauseIcon.classList.remove('hidden');
        }
    }

    function updateSeekBar() {
        if (!videoEl) return;
        const duration = videoEl.duration || 0;
        const currentTime = videoEl.currentTime || 0;
        const pct = duration ? (currentTime / duration) * 100 : 0;
        if (seekBarEl) seekBarEl.value = pct;
        if (timeDisplayEl) timeDisplayEl.textContent = `${formatTime(currentTime)} / ${formatTime(duration)}`;
    }

    // Video event handlers
    function handlePlay() { updatePlayPauseButton(); startOverlayLoop(); }
    function handlePause() { updatePlayPauseButton(); stopOverlayLoop(); }
    function handleEnded() { updatePlayPauseButton(); stopOverlayLoop(); }
    function handleTimeUpdate() { updateSeekBar(); }
    function handleLoadedMetadata() { updateSeekBar(); }
    function handleVideoError() {
        playerWrapperEl && playerWrapperEl.classList.add('video-error');
    }

    if (videoEl) {
        videoEl.addEventListener('play', handlePlay);
        videoEl.addEventListener('pause', handlePause);
        videoEl.addEventListener('ended', handleEnded);
        videoEl.addEventListener('timeupdate', handleTimeUpdate);
        videoEl.addEventListener('loadedmetadata', handleLoadedMetadata);
        videoEl.addEventListener('error', handleVideoError);
        cleanupFns.push(() => {
            videoEl.removeEventListener('play', handlePlay);
            videoEl.removeEventListener('pause', handlePause);
            videoEl.removeEventListener('ended', handleEnded);
            videoEl.removeEventListener('timeupdate', handleTimeUpdate);
            videoEl.removeEventListener('loadedmetadata', handleLoadedMetadata);
            videoEl.removeEventListener('error', handleVideoError);
        });
    }

    function handlePlayPause() {
        if (!videoEl) return;
        if (videoEl.paused) videoEl.play(); else videoEl.pause();
    }

    function handleSeek(e) {
        if (!videoEl || !videoEl.duration) return;
        videoEl.currentTime = (e.target.value / 100) * videoEl.duration;
    }

    if (playPauseBtn) {
        playPauseBtn.addEventListener('click', handlePlayPause);
        cleanupFns.push(() => playPauseBtn.removeEventListener('click', handlePlayPause));
    }

    if (seekBarEl) {
        seekBarEl.addEventListener('input', handleSeek);
        cleanupFns.push(() => seekBarEl.removeEventListener('input', handleSeek));
    }

    // Subtitle toggle buttons
    function handleShowOriginal() {
        const sub = store.get('selectedSubtitle');
        showOriginalBtn && showOriginalBtn.classList.add('active');
        showSyncedBtn && showSyncedBtn.classList.remove('active');
        if (sub) loadSubtitle(sub.path);
        else loadSubtitle(null);
    }

    function handleShowSynced() {
        const result = store.get('syncResult');
        if (!result || !result.output_path) return;
        showSyncedBtn && showSyncedBtn.classList.add('active');
        showOriginalBtn && showOriginalBtn.classList.remove('active');
        loadSubtitleUrl(api.getSubtitleUrl(result.output_path, 'vtt'));
    }

    if (showOriginalBtn) {
        showOriginalBtn.addEventListener('click', handleShowOriginal);
        cleanupFns.push(() => showOriginalBtn.removeEventListener('click', handleShowOriginal));
    }

    if (showSyncedBtn) {
        showSyncedBtn.addEventListener('click', handleShowSynced);
        cleanupFns.push(() => showSyncedBtn.removeEventListener('click', handleShowSynced));
    }

    // Store subscriptions
    cleanupFns.push(store.subscribe('selectedVideo', (video) => {
        if (!video) return;
        loadVideo(video.path);
        // Load first associated subtitle if available
        const subs = store.get('associatedSubtitles');
        if (subs && subs.length > 0) {
            loadSubtitle(subs[0].path);
            subtitleToggleEl && subtitleToggleEl.classList.remove('hidden');
            showOriginalBtn && showOriginalBtn.classList.add('active');
            showSyncedBtn && showSyncedBtn.classList.remove('active');
        } else {
            subtitleToggleEl && subtitleToggleEl.classList.add('hidden');
        }
    }));

    cleanupFns.push(store.subscribe('associatedSubtitles', (subs) => {
        if (subs && subs.length > 0) {
            subtitleToggleEl && subtitleToggleEl.classList.remove('hidden');
        }
    }));

    cleanupFns.push(store.subscribe('syncStatus', (status) => {
        if (status === 'completed') {
            const result = store.get('syncResult');
            if (result && result.success && result.output_path) {
                showSyncedBtn && showSyncedBtn.classList.remove('hidden');
            }
        }
    }));

    // When preview mode is set to 'synced' (from sync-controls), switch to synced view
    cleanupFns.push(store.subscribe('previewMode', (mode) => {
        if (mode === 'synced') {
            handleShowSynced();
            store.set('previewMode', null);
        }
    }));

    return {
        destroy() {
            stopOverlayLoop();
            cleanupFns.forEach(fn => fn());
            cleanupFns = [];
        }
    };
}
