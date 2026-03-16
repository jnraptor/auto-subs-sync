export function createWebSocketManager(basePath) {
    let socket = null;
    let heartbeatTimer = null;
    let reconnectTimer = null;
    let reconnectAttempts = 0;
    let jobId = null;
    let isTerminal = false;
    let isPageVisible = true;

    const MAX_RECONNECT_ATTEMPTS = 5;
    const BASE_DELAY = 1000;
    const MAX_DELAY = 30000;
    const HEARTBEAT_INTERVAL = 25000;

    const callbacks = {
        progress: [],
        complete: [],
        error: [],
        stateChange: [],
    };

    function clearTimers() {
        if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
        if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    }

    function notifyStateChange(state) {
        callbacks.stateChange.forEach(cb => cb(state));
    }

    function startHeartbeat() {
        clearInterval(heartbeatTimer);
        heartbeatTimer = setInterval(() => {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send('ping');
            }
        }, HEARTBEAT_INTERVAL);
    }

    /**
     * Calculate reconnect delay with exponential backoff and jitter.
     * @param {number} attempt - The current attempt number
     * @returns {number} Delay in milliseconds
     */
    function calculateBackoff(attempt) {
        const exponentialDelay = BASE_DELAY * Math.pow(2, attempt);
        const jitter = Math.random() * 0.3 * exponentialDelay; // 30% jitter
        return Math.min(exponentialDelay + jitter, MAX_DELAY);
    }

    function connect(newJobId) {
        // Close any existing socket first
        if (socket) {
            socket.onclose = null;
            socket.close();
            socket = null;
        }
        clearTimers();

        jobId = newJobId;
        isTerminal = false;
        reconnectAttempts = 0;

        notifyStateChange('connecting');

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}${basePath}/api/sync/${jobId}/ws`;
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            reconnectAttempts = 0;
            startHeartbeat();
            notifyStateChange('connected');
        };

        socket.onmessage = (event) => {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch (e) {
                console.warn('Failed to parse WebSocket message:', e);
                return;
            }
            switch (data.type) {
                case 'progress':
                    callbacks.progress.forEach(cb => cb({ percent: data.percent, message: data.message }));
                    break;
                case 'complete':
                    isTerminal = true;
                    callbacks.complete.forEach(cb => cb(data.result));
                    socket.close();
                    break;
                case 'error':
                    isTerminal = true;
                    callbacks.error.forEach(cb => cb(data.error));
                    socket.close();
                    break;
                case 'pong':
                    break;
                default:
                    console.warn('Unknown WebSocket message type:', data.type);
            }
        };

        socket.onclose = () => {
            clearInterval(heartbeatTimer);
            heartbeatTimer = null;
            notifyStateChange('disconnected');

            if (!isTerminal && reconnectAttempts < MAX_RECONNECT_ATTEMPTS && isPageVisible) {
                const delay = calculateBackoff(reconnectAttempts);
                reconnectAttempts++;
                reconnectTimer = setTimeout(() => connect(jobId), delay);
            }
        };

        socket.onerror = (e) => {
            console.warn('WebSocket error:', e);
            // onclose will fire after onerror; handle reconnect there
        };
    }

    function disconnect() {
        isTerminal = true;
        clearTimers();
        if (socket) {
            socket.onclose = null;
            socket.close();
            socket = null;
        }
        notifyStateChange('disconnected');
    }

    /**
     * Handle page visibility changes to pause/resume reconnection attempts.
     */
    function handleVisibilityChange() {
        isPageVisible = !document.hidden;
        
        if (isPageVisible && !isTerminal && socket?.readyState !== WebSocket.OPEN) {
            // Resume reconnection when page becomes visible
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                connect(jobId);
            }
        }
    }

    // Register visibility change listener
    document.addEventListener('visibilitychange', handleVisibilityChange);

    function onProgress(callback) {
        callbacks.progress.push(callback);
        return () => { callbacks.progress = callbacks.progress.filter(cb => cb !== callback); };
    }

    function onComplete(callback) {
        callbacks.complete.push(callback);
        return () => { callbacks.complete = callbacks.complete.filter(cb => cb !== callback); };
    }

    function onError(callback) {
        callbacks.error.push(callback);
        return () => { callbacks.error = callbacks.error.filter(cb => cb !== callback); };
    }

    function onStateChange(callback) {
        callbacks.stateChange.push(callback);
        return () => { callbacks.stateChange = callbacks.stateChange.filter(cb => cb !== callback); };
    }

    function destroy() {
        disconnect();
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        callbacks.progress = [];
        callbacks.complete = [];
        callbacks.error = [];
        callbacks.stateChange = [];
    }

    return { connect, disconnect, onProgress, onComplete, onError, onStateChange, destroy };
}
