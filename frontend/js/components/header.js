import * as api from '../api.js';

export function createHeader(store) {
    let cleanupFns = [];

    const statusEl = document.getElementById('connection-status');
    const statusDotEl = statusEl ? statusEl.querySelector('.status-dot') : null;
    const statusTextEl = statusEl ? statusEl.querySelector('.status-text') : null;

    function render() {
        if (!statusEl) return;
        const connected = store.get('apiConnected');
        const wsState = store.get('wsState');

        statusEl.classList.remove('connected', 'disconnected', 'syncing');

        if (wsState === 'connected') {
            statusEl.classList.add('syncing');
            if (statusTextEl) statusTextEl.textContent = 'Syncing';
        } else if (connected) {
            statusEl.classList.add('connected');
            if (statusTextEl) statusTextEl.textContent = 'Ready';
        } else if (connected === false) {
            statusEl.classList.add('disconnected');
            if (statusTextEl) statusTextEl.textContent = 'Disconnected';
        }
        // If connected is undefined/null (initial state), keep "Checking..."
    }

    cleanupFns.push(store.subscribe('apiConnected', render));
    cleanupFns.push(store.subscribe('wsState', render));

    // Health check polling
    async function checkHealth() {
        try {
            await api.checkHealth();
            store.set('apiConnected', true);
        } catch {
            store.set('apiConnected', false);
        }
    }

    checkHealth();
    const healthInterval = setInterval(checkHealth, 30000);
    cleanupFns.push(() => clearInterval(healthInterval));

    render();

    return {
        destroy() {
            cleanupFns.forEach(fn => fn());
            cleanupFns = [];
        }
    };
}
