export function createWebSocketManager(basePath) {
    let socket = null;
    let heartbeatTimer = null;
    let reconnectTimer = null;
    let reconnectAttempts = 0;
    let jobId = null;
    let isTerminal = false;

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
        }, 25000);
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
            }
        };

        socket.onclose = () => {
            clearInterval(heartbeatTimer);
            heartbeatTimer = null;
            notifyStateChange('disconnected');

            if (!isTerminal && reconnectAttempts < 5) {
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                reconnectAttempts++;
                reconnectTimer = setTimeout(() => connect(jobId), delay);
            }
        };

        socket.onerror = () => {
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
        callbacks.progress = [];
        callbacks.complete = [];
        callbacks.error = [];
        callbacks.stateChange = [];
    }

    return { connect, disconnect, onProgress, onComplete, onError, onStateChange, destroy };
}
