import { createStore, createInitialState } from './store.js';
import * as api from './api.js';
import { createWebSocketManager } from './ws.js';
import { createToast } from './components/toast.js';
import { createHeader } from './components/header.js';
import { createFileBrowser } from './components/file-browser.js';
import { createSyncControls } from './components/sync-controls.js';
import { createPreview } from './components/preview.js';

function init() {
    const store = createStore(createInitialState());
    const wsManager = createWebSocketManager(api.getBasePath());
    const toast = createToast();

    // Fetch available engines on startup
    api.getEngines()
        .then(data => store.batch({
            engines: data.engines,
            defaultEngine: data.default,
            syncEngine: data.default,
        }))
        .catch(() => toast.warning('Could not load sync engines'));

    const components = [
        createHeader(store),
        createFileBrowser(store, toast),
        createSyncControls(store, wsManager, toast),
        createPreview(store),
    ];

    window.addEventListener('unhandledrejection', (e) => {
        console.error('Unhandled rejection:', e.reason);
        toast.error('An unexpected error occurred');
        e.preventDefault();
    });

    window.addEventListener('beforeunload', () => {
        wsManager.destroy();
        components.forEach(c => c.destroy());
        store.destroy();
    });
}

document.addEventListener('DOMContentLoaded', init);
