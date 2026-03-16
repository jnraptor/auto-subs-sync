export function createStore(initialState) {
    let state = { ...initialState };
    const subscribers = new Map(); // key → Set of callbacks

    function get(key) {
        return state[key];
    }

    function set(key, value) {
        if (state[key] === value) return;
        const oldValue = state[key];
        state[key] = value;
        const subs = subscribers.get(key);
        if (subs) {
            subs.forEach(cb => cb(value, oldValue));
        }
    }

    function batch(updates) {
        Object.entries(updates).forEach(([key, value]) => set(key, value));
    }

    function subscribe(key, callback) {
        if (!subscribers.has(key)) {
            subscribers.set(key, new Set());
        }
        subscribers.get(key).add(callback);
        return function unsubscribe() {
            const subs = subscribers.get(key);
            if (subs) subs.delete(callback);
        };
    }

    function getState() {
        return { ...state };
    }

    function destroy() {
        subscribers.clear();
    }

    return { get, set, batch, subscribe, getState, destroy };
}

export function createInitialState() {
    return {
        currentPath: '',
        files: [],
        filesLoading: false,
        filesError: null,
        selectedVideo: null,
        associatedSubtitles: [],
        selectedSubtitle: null,
        uploadedSubtitle: null,
        engines: [],
        defaultEngine: 'ffsubsync',
        syncEngine: 'ffsubsync',
        audioTracks: [],
        audioTrack: null,
        manualOffset: 0,
        framerateAdjust: 'none',
        syncStatus: 'idle',
        syncProgress: 0,
        syncMessage: '',
        jobId: null,
        lastJobId: null,
        syncResult: null,
        apiConnected: null,
        wsState: 'disconnected',
        previewMode: null,
    };
}
