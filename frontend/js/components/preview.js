import * as api from '../api.js';
import { show, hide } from '../utils/dom.js';
import { logError } from '../utils/errors.js';

export function createPreview(store) {
    let cleanupFns = [];
    let animFrameId = null;
    let isExpanded = false;
    let pendingVideoPath = null;
    let pendingSubtitlePath = null;

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
    const previewPanelSection = document.getElementById('preview-panel-section');
    const previewToggleBtn = document.getElementById('preview-toggle-btn');

    function formatTime(seconds) {
        if (!isFinite(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function loadVideo(videoPath) {
        if (!videoEl) return;
        
        // If preview is collapsed, store the path for later
        if (!isExpanded) {
            pendingVideoPath = videoPath;
            return;
        }
        
        noVideoEl && noVideoEl.classList.add('hidden');
        playerWrapperEl && playerWrapperEl.classList.remove('hidden');
        videoEl.src = api.getVideoUrl(videoPath);
        videoEl.load();
    }

    function loadSubtitle(subtitlePath) {
        if (!videoEl) return;
        
        // If preview is collapsed, store the path for later
        if (!isExpanded) {
            pendingSubtitlePath = subtitlePath;
            return;
        }
        
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

        track.addEventListener('error', (e) => {
            logError(e, 'Subtitle track load error');
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
    function handleVideoError(e) {
        logError(e, 'Video load error');
        if (playerWrapperEl) playerWrapperEl.classList.add('video-error');
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

    // Preview panel toggle
    function handlePreviewToggle() {
        if (!previewPanelSection || !previewToggleBtn) return;
        
        isExpanded = !isExpanded;
        previewPanelSection.classList.toggle('collapsed', !isExpanded);
        previewToggleBtn.setAttribute('aria-expanded', isExpanded.toString());
        
        // Load pending content if expanding
        if (isExpanded) {
            if (pendingVideoPath) {
                loadVideo(pendingVideoPath);
                pendingVideoPath = null;
            }
            if (pendingSubtitlePath) {
                loadSubtitle(pendingSubtitlePath);
                pendingSubtitlePath = null;
            }
        } else {
            // Pause video when collapsing
            if (videoEl && !videoEl.paused) {
                videoEl.pause();
            }
        }
    }

    if (previewToggleBtn) {
        previewToggleBtn.addEventListener('click', handlePreviewToggle);
        cleanupFns.push(() => previewToggleBtn.removeEventListener('click', handlePreviewToggle));
    }

    // Subtitle toggle buttons
    function handleShowOriginal() {
        const sub = store.get('selectedSubtitle');
        if (showOriginalBtn) {
            showOriginalBtn.classList.add('active');
            showOriginalBtn.setAttribute('aria-pressed', 'true');
        }
        if (showSyncedBtn) {
            showSyncedBtn.classList.remove('active');
            showSyncedBtn.setAttribute('aria-pressed', 'false');
        }
        if (sub) loadSubtitle(sub.path);
        else loadSubtitle(null);
    }

    function handleShowSynced() {
        const result = store.get('syncResult');
        if (!result || !result.output_path) return;
        if (showSyncedBtn) {
            showSyncedBtn.classList.add('active');
            showSyncedBtn.setAttribute('aria-pressed', 'true');
        }
        if (showOriginalBtn) {
            showOriginalBtn.classList.remove('active');
            showOriginalBtn.setAttribute('aria-pressed', 'false');
        }
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
        
        // Store subtitle path for later if collapsed
        const subs = store.get('associatedSubtitles');
        if (subs && subs.length > 0) {
            pendingSubtitlePath = subs[0].path;
            if (isExpanded) {
                loadSubtitle(pendingSubtitlePath);
                pendingSubtitlePath = null;
            }
            subtitleToggleEl && subtitleToggleEl.classList.remove('hidden');
            showOriginalBtn && showOriginalBtn.classList.add('active');
            showSyncedBtn && showSyncedBtn.classList.remove('active');
        } else {
            pendingSubtitlePath = null;
            subtitleToggleEl && subtitleToggleEl.classList.add('hidden');
        }
        
        loadVideo(video.path);
    }));

    cleanupFns.push(store.subscribe('associatedSubtitles', (subs) => {
        if (subs && subs.length > 0) {
            subtitleToggleEl && subtitleToggleEl.classList.remove('hidden');
            showOriginalBtn && showOriginalBtn.classList.add('active');
            showSyncedBtn && showSyncedBtn.classList.remove('active');
            
            // Load subtitle if preview is expanded and we're in original mode
            if (isExpanded && showOriginalBtn && showOriginalBtn.classList.contains('active')) {
                loadSubtitle(subs[0].path);
            } else {
                pendingSubtitlePath = subs[0].path;
            }
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

    // Initialize collapsed state
    if (previewPanelSection) {
        isExpanded = !previewPanelSection.classList.contains('collapsed');
        previewToggleBtn && previewToggleBtn.setAttribute('aria-expanded', isExpanded.toString());
    }

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
