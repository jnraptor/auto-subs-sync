import * as api from '../api.js';
import { logError } from '../utils/errors.js';

export function createHeader(store) {
    const cleanupFns = [];

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

    // Health check polling with page visibility optimization
    let healthInterval = null;

    async function checkHealth() {
        try {
            await api.checkHealth();
            store.set('apiConnected', true);
        } catch (err) {
            logError(err, 'Health check failed');
            store.set('apiConnected', false);
        }
    }

    function startHealthCheck() {
        if (healthInterval) return;
        checkHealth();
        healthInterval = setInterval(checkHealth, 30000);
    }

    function stopHealthCheck() {
        if (healthInterval) {
            clearInterval(healthInterval);
            healthInterval = null;
        }
    }

    // Pause health checks when page is hidden to save resources
    function handleVisibilityChange() {
        if (document.hidden) {
            stopHealthCheck();
        } else {
            startHealthCheck();
        }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange);
    cleanupFns.push(() => {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        stopHealthCheck();
    });

    startHealthCheck();
    render();

    return {
        destroy() {
            cleanupFns.forEach(fn => fn());
            cleanupFns.length = 0;
        }
    };
}
