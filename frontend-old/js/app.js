import { initFileBrowser } from './file-browser.js';
import { initSyncControls } from './sync-controls.js';
import { initPreview } from './preview.js';
import { initApi } from './api.js';

class AppState {
    constructor() {
        this.currentPath = '';
        this.selectedVideo = null;
        this.associatedSubtitles = [];
        this.selectedSubtitle = null;
        this.syncEngine = 'ffsubsync';
        this.audioTrack = null;
        this.syncProgress = 0;
        this.syncStatus = 'idle';
        this.lastSyncedFile = null;
        this.websocket = null;
    }

    setSelectedVideo(video) {this.selectedVideo = video;}
    setSelectedSubtitle(subtitle) {this.selectedSubtitle = subtitle;}
    setSyncEngine(engine) {this.syncEngine = engine;}
    setAudioTrack(track) {this.audioTrack = track;}
    setSyncProgress(progress) {this.syncProgress = progress;}
    setSyncStatus(status) {this.syncStatus = status;}
    setLastSyncedFile(file) {this.lastSyncedFile = file;}
    setAssociatedSubtitles(subtitles) {this.associatedSubtitles = subtitles;}
    setCurrentPath(path) {this.currentPath = path;}
}

const state = new AppState();
const components = {};

function init() {
    components.api = initApi(state);
    components.fileBrowser = initFileBrowser(state, components.api);
    components.syncControls = initSyncControls(state, components.api);
    components.preview = initPreview(state, components.api);
    
    components.api.onConnectionChange((connected) => {
        updateConnectionStatus(connected, false);
    });
    
    components.api.onSyncProgress((data) => {
        components.syncControls.updateProgress(data);
    });
    
    updateConnectionStatus(false, false);
}

let apiConnected = false;
let wsConnected = false;

function updateConnectionStatus(connected, isWebSocket = false) {
    const statusEl = document.getElementById('connection-status');
    if (!statusEl) return;
    
    const text = statusEl.querySelector('.status-text');
    
    if (isWebSocket) {
        wsConnected = connected;
    } else {
        apiConnected = connected;
    }
    
    statusEl.classList.remove('connected', 'disconnected', 'syncing');
    
    if (wsConnected) {
        statusEl.classList.add('syncing');
        text.textContent = 'Syncing';
    } else if (apiConnected) {
        statusEl.classList.add('connected');
        text.textContent = 'Ready';
    } else {
        statusEl.classList.add('disconnected');
        text.textContent = 'Disconnected';
    }
}

document.addEventListener('DOMContentLoaded', init);