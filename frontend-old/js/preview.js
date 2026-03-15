export function initPreview(state, api) {
    const noVideoEl = document.getElementById('no-video');
    const playerWrapperEl = document.getElementById('video-player-wrapper');
    const videoPlayerEl = document.getElementById('video-player');
    const subtitleTrackEl = document.getElementById('subtitle-track');
    const subtitleOverlayEl = document.getElementById('subtitle-overlay');
    const playPauseBtn = document.getElementById('play-pause');
    const seekBarEl = document.getElementById('seek-bar');
    const timeDisplayEl = document.getElementById('time-display');
    const subtitleToggleEl = document.getElementById('subtitle-toggle');
    const showOriginalBtn = document.getElementById('show-original');
    const showSyncedBtn = document.getElementById('show-synced');
    
    let currentCues = [];
    let showingSynced = false;

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    async function loadVideo(videoPath) {
        noVideoEl.classList.add('hidden');
        playerWrapperEl.classList.remove('hidden');
        
        videoPlayerEl.src = api.getVideoUrl(videoPath);
        videoPlayerEl.load();
    }

    function loadSubtitle(subtitleUrl, isSynced = false) {
        subtitleTrackEl.src = subtitleUrl;
        videoPlayerEl.textTracks[0].mode = 'hidden';
    }

    function updateSubtitleOverlay(cues) {
        currentCues = cues;
        renderSubtitleOverlay();
    }

    function renderSubtitleOverlay() {
        if (!videoPlayerEl.paused) return;
        
        const currentTime = videoPlayerEl.currentTime;
        const activeCues = currentCues.filter(cue => 
            currentTime >= cue.startTime && currentTime <= cue.endTime
        );
        
        if (activeCues.length > 0) {
            subtitleOverlayEl.innerHTML = `<span class="subtitle-text">${activeCues.map(c => c.text).join('<br>')}</span>`;
        } else {
            subtitleOverlayEl.innerHTML = '';
        }
    }

    function togglePlayPause() {
        if (videoPlayerEl.paused) {
            videoPlayerEl.play();
        } else {
            videoPlayerEl.pause();
        }
    }

    function updatePlayPauseButton() {
        const playIcon = document.getElementById('play-icon');
        const pauseIcon = document.getElementById('pause-icon');
        
        if (videoPlayerEl.paused) {
            playIcon.classList.remove('hidden');
            pauseIcon.classList.add('hidden');
        } else {
            playIcon.classList.add('hidden');
            pauseIcon.classList.remove('hidden');
        }
    }

    function updateSeekBar() {
        const duration = videoPlayerEl.duration || 0;
        const currentTime = videoPlayerEl.currentTime || 0;
        const percentage = duration ? (currentTime / duration) * 100 : 0;
        
        seekBarEl.value = percentage;
        timeDisplayEl.textContent = `${formatTime(currentTime)} / ${formatTime(duration)}`;
    }

    function handleSeek(e) {
        const duration = videoPlayerEl.duration;
        const percentage = e.target.value;
        videoPlayerEl.currentTime = (percentage /100) * duration;
    }

    if (playPauseBtn) {
        playPauseBtn.addEventListener('click', togglePlayPause);
    }

    if (seekBarEl) {
        seekBarEl.addEventListener('input', handleSeek);
    }

    if (videoPlayerEl) {
        videoPlayerEl.addEventListener('play', updatePlayPauseButton);
        videoPlayerEl.addEventListener('pause', updatePlayPauseButton);
        videoPlayerEl.addEventListener('timeupdate', () => {
            updateSeekBar();
            updateSubtitleFromTrack();
        });
        videoPlayerEl.addEventListener('loadedmetadata', updateSeekBar);
    }

    function updateSubtitleFromTrack() {
        if (!videoPlayerEl.textTracks || !videoPlayerEl.textTracks[0]) return;
        
        const track = videoPlayerEl.textTracks[0];
        const currentTime = videoPlayerEl.currentTime;
        
        if (!track.cues) return;
        
        for (const cue of track.cues) {
            if (currentTime >= cue.startTime && currentTime <= cue.endTime) {
                subtitleOverlayEl.innerHTML = `<span class="subtitle-text">${cue.text}</span>`;
                return;
            }
        }
        subtitleOverlayEl.innerHTML = '';
    }

    if (showOriginalBtn) {
        showOriginalBtn.addEventListener('click', () => {
            showingSynced = false;
            showOriginalBtn.classList.add('active');
            showSyncedBtn.classList.remove('active');
            
            if (state.selectedSubtitle) {
                loadSubtitle(api.getSubtitleUrl(state.selectedSubtitle.path), false);
            }
        });
    }

    if (showSyncedBtn) {
        showSyncedBtn.addEventListener('click', () => {
            showingSynced = true;
            showSyncedBtn.classList.add('active');
            showOriginalBtn.classList.remove('active');
            
            if (state.lastSyncedFile) {
                loadSubtitle(api.getSubtitleUrl(state.lastSyncedFile), true);
            }
        });
    }

    window.addEventListener('videoSelected', async (e) => {
        const video = e.detail;
        await loadVideo(video.path);
        
        if (video.subtitles && video.subtitles.length > 0) {
            subtitleToggleEl.classList.remove('hidden');
            loadSubtitle(api.getSubtitleUrl(video.subtitles[0].path));
        } else {
            subtitleToggleEl.classList.add('hidden');
        }
    });

    window.addEventListener('previewResult', async (e) => {
        const { video, syncedSubtitle } = e.detail;
        
        if (syncedSubtitle) {
            showingSynced = true;
            showSyncedBtn.classList.add('active');
            showOriginalBtn.classList.remove('active');
            subtitleToggleEl.classList.remove('hidden');
            
            loadSubtitle(api.getSubtitleUrl(syncedSubtitle), true);
        }
    });

    return {
        loadVideo,
        loadSubtitle,
        togglePlayPause,
        updateSeekBar
    };
}