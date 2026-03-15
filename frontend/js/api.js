export class ApiError extends Error {
    constructor(status, error) {
        super(error?.message || 'Unknown error');
        this.status = status;
        this.code = error?.code || 'unknown';
        this.details = error?.details || {};
    }
}

export function getBasePath() {
    const pathParts = window.location.pathname.split('/').filter(Boolean);
    if (pathParts.length > 0 && !pathParts[0].includes('.')) {
        return '/' + pathParts[0];
    }
    return '';
}

const BASE_PATH = getBasePath();
const API_PREFIX = BASE_PATH ? `${BASE_PATH}/api` : '/api';

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
    } catch (err) {
        if (err.name === 'AbortError') {
            throw new ApiError(0, { code: 'timeout', message: 'Request timed out' });
        }
        throw err;
    } finally {
        clearTimeout(timeoutId);
    }
}

async function fetchBlob(url, timeoutMs = 30000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) {
            const body = await response.json().catch(() => null);
            throw new ApiError(response.status, body?.error || { message: response.statusText });
        }
        return response.blob();
    } catch (err) {
        if (err.name === 'AbortError') {
            throw new ApiError(0, { code: 'timeout', message: 'Request timed out' });
        }
        throw err;
    } finally {
        clearTimeout(timeoutId);
    }
}

export function getFiles(path = '') {
    const url = path
        ? `${API_PREFIX}/files?path=${encodeURIComponent(path)}`
        : `${API_PREFIX}/files`;
    return fetchJSON(url, {}, 10000);
}

export function getFileInfo(path) {
    return fetchJSON(`${API_PREFIX}/files/info?path=${encodeURIComponent(path)}`, {}, 15000);
}

export function getAudioTracks(path) {
    return fetchJSON(`${API_PREFIX}/files/audio-tracks?path=${encodeURIComponent(path)}`, {}, 15000);
}

export function getAssociatedSubtitles(videoPath) {
    return fetchJSON(`${API_PREFIX}/files/associated-subtitles?video_path=${encodeURIComponent(videoPath)}`, {}, 10000);
}

export function getEngines() {
    return fetchJSON(`${API_PREFIX}/sync/engines`, {}, 5000);
}

export function startSync(request) {
    return fetchJSON(`${API_PREFIX}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
    }, 15000);
}

export function getJobStatus(jobId) {
    return fetchJSON(`${API_PREFIX}/sync/${jobId}`, {}, 10000);
}

export function cancelJob(jobId) {
    return fetchJSON(`${API_PREFIX}/sync/${jobId}`, { method: 'DELETE' }, 10000);
}

export async function uploadSubtitle(file) {
    const formData = new FormData();
    formData.append('file', file);
    return fetchJSON(`${API_PREFIX}/subtitles/upload`, {
        method: 'POST',
        body: formData,
        // No Content-Type header — browser sets it with boundary
    }, 30000);
}

export async function downloadSubtitle(jobId) {
    const blob = await fetchBlob(`${API_PREFIX}/subtitles/download/${jobId}`, 30000);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `synced_${jobId}.srt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

export function saveSubtitle(jobId, overwrite = false) {
    const url = `${API_PREFIX}/subtitles/save/${jobId}?overwrite=${overwrite}`;
    return fetchJSON(url, { method: 'POST' }, 15000);
}

export function checkHealth() {
    return fetchJSON(`${API_PREFIX}/health`, {}, 5000);
}

export function getVideoUrl(path) {
    return `${API_PREFIX}/stream/video?path=${encodeURIComponent(path)}`;
}

export function getSubtitleUrl(path, format = 'vtt') {
    return `${API_PREFIX}/stream/subtitle?path=${encodeURIComponent(path)}&format=${format}`;
}
