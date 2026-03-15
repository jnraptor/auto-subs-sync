// Auto-detect base path from URL - supports custom basedir via env var
const getBasePath = () => {
    const path = window.location.pathname;
    // Check if we're in a subdirectory (not at root)
    const pathParts = path.split('/').filter(Boolean);
    if (pathParts.length > 0 && !pathParts[0].includes('.')) {
        // We're in a subdirectory like /auto-subs-sync/
        return '/' + pathParts[0];
    }
    return '';
};

const BASE_PATH = getBasePath();
const API_PREFIX = BASE_PATH ? `${BASE_PATH}/api` : '/api';

let websocket = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 5;
let reconnectDelay = 1000;
let connectionCallbacks = [];
let progressCallbacks = [];
let heartbeatInterval = null;
let currentJobId = null;

export function initApi(state) {
    // WebSocket connection is established per-job, not globally
    
    // Check API health on init and periodically
    async function checkHealth() {
        try {
            const response = await fetch(`${API_PREFIX}/health`);
            const connected = response.ok;
            notifyConnectionChange(connected);
            return connected;
        } catch (error) {
            notifyConnectionChange(false);
            return false;
        }
    }
    
    // Check health initially and every 30 seconds
    checkHealth();
    setInterval(checkHealth, 30000);

    async function fetchWithAuth(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: response.statusText }));
            throw new Error(error.message || 'Request failed');
        }

        return response.json();
    }

    function connectWebSocket(jobId) {
        if (!jobId) {
            console.error('No job ID provided for WebSocket connection');
            return;
        }
        
        currentJobId = jobId;
        
        if (websocket) {
            websocket.close();
        }

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}${API_PREFIX}/sync/${jobId}/ws`;
        websocket = new WebSocket(wsUrl);

        websocket.onopen = () => {
            reconnectAttempts = 0;
            notifyConnectionChange(true, true);
            startHeartbeat();
        };

        websocket.onclose = () => {
            notifyConnectionChange(false, true);
            stopHeartbeat();
            scheduleReconnect();
        };

        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };
    }

    function scheduleReconnect() {
        if (reconnectAttempts >= maxReconnectAttempts) {
            console.log('Max reconnect attempts reached');
            return;
        }

        reconnectAttempts++;
        const delay = Math.min(reconnectDelay * Math.pow(2, reconnectAttempts - 1), 30000);
        
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
        
        setTimeout(() => connectWebSocket(currentJobId), delay);
    }

    function startHeartbeat() {
        stopHeartbeat();
        heartbeatInterval = setInterval(() => {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send('ping');
            }
        }, 30000);
    }

    function stopHeartbeat() {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
    }

    function handleMessage(data) {
        switch (data.type) {
            case 'pong':
                break;
            case 'progress':
                notifyProgress(data.payload);
                break;
            case 'complete':
                notifyProgress({ progress:100, message: 'Complete' });
                break;
            case 'error':
                notifyProgress({ progress: 0, message: `Error: ${data.message}` });
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    function notifyConnectionChange(connected, isWebSocket = false) {
        connectionCallbacks.forEach(cb => cb(connected, isWebSocket));
    }

    function notifyProgress(data) {
        progressCallbacks.forEach(cb => cb(data));
    }

    function onConnectionChange(callback) {
        connectionCallbacks.push(callback);
    }

    function onSyncProgress(callback) {
        progressCallbacks.push(callback);
    }

    async function getFiles(path = '') {
        const url = path ? `${API_PREFIX}/files?path=${encodeURIComponent(path)}` : `${API_PREFIX}/files`;
        return fetchWithAuth(url);
    }

    async function getAssociatedSubtitles(videoPath) {
        const url = `${API_PREFIX}/files/associated-subtitles?video_path=${encodeURIComponent(videoPath)}`;
        return fetchWithAuth(url);
    }

    async function syncSubtitle(options) {
        const payload = {
            video_path: options.videoPath,
            subtitle_path: options.subtitlePath,
            engine: options.engine,
            options: {
                audio_track: options.audioTrack || 0,
                offset_ms: options.manualOffset || null,
                framerate: options.framerateAdjust && options.framerateAdjust !== 'none' ? parseFloat(options.framerateAdjust) : null
            }
        };
        const response = await fetchWithAuth(`${API_PREFIX}/sync`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        // Connect WebSocket for this job
        connectWebSocket(response.job_id);
        return response;
    }

    function cancelSync() {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({ type: 'cancel' }));
        }
    }

    async function downloadSubtitle(jobId) {
        const response = await fetch(`${API_PREFIX}/subtitles/download/${jobId}`);
        if (!response.ok) {
            throw new Error('Download failed');
        }
        return response.blob();
    }

    async function uploadSubtitle(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_PREFIX}/subtitles/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: response.statusText }));
            throw new Error(error.message || 'Upload failed');
        }
        
        return response.json();
    }

    function getVideoUrl(path) {
        return `${API_PREFIX}/stream/video?path=${encodeURIComponent(path)}`;
    }

    function getSubtitleUrl(path) {
        return `${API_PREFIX}/stream/subtitle?path=${encodeURIComponent(path)}&format=vtt`;
    }

    return {
        onConnectionChange,
        onSyncProgress,
        getFiles,
        getAssociatedSubtitles,
        syncSubtitle,
        cancelSync,
        downloadSubtitle,
        uploadSubtitle,
        getVideoUrl,
        getSubtitleUrl,
        reconnect: connectWebSocket
    };
}