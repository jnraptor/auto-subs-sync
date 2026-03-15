import * as api from '../api.js';

const FILE_ICONS = {
    folder: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>`,
    video:  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>`,
    subtitle: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/></svg>`,
    file:   `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>`,
};

function formatFileSize(bytes) {
    if (!bytes) return '';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function createFileBrowser(store, toast) {
    let cleanupFns = [];

    const browserEl = document.getElementById('file-browser');
    const breadcrumbEl = document.getElementById('breadcrumb');
    const refreshBtn = document.getElementById('refresh-files');

    // Roving tabindex state
    let focusedIndex = 0;
    let fileItems = [];

    async function loadFiles(path = '') {
        store.batch({ filesLoading: true, filesError: null });
        try {
            const data = await api.getFiles(path);
            store.batch({
                files: data.items || [],
                currentPath: data.path || path,
                filesLoading: false,
            });
        } catch (err) {
            store.batch({ filesLoading: false, filesError: err.message });
            toast.error(`Failed to load files: ${err.message}`);
        }
    }

    function render() {
        const files = store.get('files');
        const loading = store.get('filesLoading');
        const error = store.get('filesError');
        const selectedVideo = store.get('selectedVideo');

        if (loading) {
            browserEl.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            fileItems = [];
            return;
        }

        if (error) {
            browserEl.innerHTML = `
                <div class="error-state">
                    <p class="error-message">${error}</p>
                    <button class="btn btn-secondary btn-sm" id="retry-load">Retry</button>
                </div>`;
            const retryBtn = document.getElementById('retry-load');
            if (retryBtn) retryBtn.addEventListener('click', () => loadFiles(store.get('currentPath')));
            fileItems = [];
            return;
        }

        if (!files.length) {
            browserEl.innerHTML = '<div class="no-selection"><p>No files found</p></div>';
            fileItems = [];
            return;
        }

        // Sort: directories → videos → subtitles → others
        const dirs = files.filter(f => f.file_type === 'directory');
        const videos = files.filter(f => f.file_type === 'video');
        const subs = files.filter(f => f.file_type === 'subtitle');
        const others = files.filter(f => !['directory', 'video', 'subtitle'].includes(f.file_type));
        const sorted = [...dirs, ...videos, ...subs, ...others];

        browserEl.setAttribute('role', 'listbox');
        browserEl.setAttribute('aria-label', 'File list');
        browserEl.innerHTML = '';
        fileItems = [];

        sorted.forEach((file, idx) => {
            const item = createFileItem(file, idx === 0, selectedVideo);
            browserEl.appendChild(item);
            fileItems.push({ el: item, file });
        });

        updateRovingTabindex(0);
    }

    function createFileItem(file, isFirst, selectedVideo) {
        const type = file.file_type === 'directory' ? 'folder' : (file.file_type || 'file');
        const icon = FILE_ICONS[type] || FILE_ICONS.file;
        const isSelected = selectedVideo && selectedVideo.path === file.path;

        const item = document.createElement('div');
        item.className = `file-item ${type}${isSelected ? ' selected' : ''}`;
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', isSelected ? 'true' : 'false');
        item.setAttribute('tabindex', isFirst ? '0' : '-1');
        item.dataset.path = file.path;
        item.dataset.type = file.file_type;

        item.innerHTML = `
            <span class="file-icon" aria-hidden="true">${icon}</span>
            <span class="file-name">${file.name}</span>
            ${file.size ? `<span class="file-meta">${formatFileSize(file.size)}</span>` : ''}
        `;

        function handleClick() { handleFileClick(file); }
        item.addEventListener('click', handleClick);
        cleanupFns.push(() => item.removeEventListener('click', handleClick));

        return item;
    }

    async function handleFileClick(file) {
        if (file.file_type === 'directory') {
            const newPath = store.get('currentPath')
                ? `${store.get('currentPath')}/${file.name}`
                : file.name;
            loadFiles(file.path || newPath);
        } else if (file.file_type === 'video') {
            store.set('selectedVideo', file);
            store.batch({
                associatedSubtitles: [],
                selectedSubtitle: null,
                uploadedSubtitle: null,
                audioTracks: [],
                audioTrack: null,
            });

            const [subsResult, tracksResult] = await Promise.allSettled([
                api.getAssociatedSubtitles(file.path),
                api.getAudioTracks(file.path),
            ]);

            store.batch({
                associatedSubtitles: subsResult.status === 'fulfilled' ? (subsResult.value.subtitles || []) : [],
                audioTracks: tracksResult.status === 'fulfilled' ? (tracksResult.value.tracks || []) : [],
            });
        } else if (file.file_type === 'subtitle') {
            store.set('selectedSubtitle', file);
        }
    }

    function renderBreadcrumb() {
        const currentPath = store.get('currentPath');
        const parts = currentPath ? currentPath.split('/').filter(Boolean) : [];

        breadcrumbEl.innerHTML = '';
        breadcrumbEl.setAttribute('role', 'navigation');
        breadcrumbEl.setAttribute('aria-label', 'File path');

        const homeSpan = document.createElement('button');
        homeSpan.className = 'breadcrumb-item';
        homeSpan.textContent = 'Home';
        homeSpan.setAttribute('aria-label', 'Navigate to root');
        homeSpan.addEventListener('click', () => loadFiles(''));
        breadcrumbEl.appendChild(homeSpan);

        let cumulativePath = '';
        parts.forEach(part => {
            cumulativePath = cumulativePath ? `${cumulativePath}/${part}` : part;
            const sep = document.createElement('span');
            sep.className = 'breadcrumb-separator';
            sep.setAttribute('aria-hidden', 'true');
            sep.textContent = '/';
            breadcrumbEl.appendChild(sep);

            const pathCopy = cumulativePath;
            const btn = document.createElement('button');
            btn.className = 'breadcrumb-item';
            btn.textContent = part;
            btn.addEventListener('click', () => loadFiles(pathCopy));
            breadcrumbEl.appendChild(btn);
        });
    }

    function updateRovingTabindex(newIndex) {
        if (!fileItems.length) return;
        if (fileItems[focusedIndex]) fileItems[focusedIndex].el.setAttribute('tabindex', '-1');
        focusedIndex = Math.max(0, Math.min(newIndex, fileItems.length - 1));
        if (fileItems[focusedIndex]) fileItems[focusedIndex].el.setAttribute('tabindex', '0');
    }

    function handleKeyDown(e) {
        if (!fileItems.length) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            updateRovingTabindex(focusedIndex + 1);
            fileItems[focusedIndex].el.focus();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            updateRovingTabindex(focusedIndex - 1);
            fileItems[focusedIndex].el.focus();
        } else if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            if (fileItems[focusedIndex]) handleFileClick(fileItems[focusedIndex].file);
        }
    }

    browserEl.addEventListener('keydown', handleKeyDown);
    cleanupFns.push(() => browserEl.removeEventListener('keydown', handleKeyDown));

    // Update focused index when an item is clicked
    browserEl.addEventListener('focus', (e) => {
        const item = e.target.closest('.file-item');
        if (!item) return;
        const idx = fileItems.findIndex(f => f.el === item);
        if (idx !== -1) updateRovingTabindex(idx);
    }, true);

    // Subscribe to store
    cleanupFns.push(store.subscribe('files', render));
    cleanupFns.push(store.subscribe('filesLoading', render));
    cleanupFns.push(store.subscribe('filesError', render));
    cleanupFns.push(store.subscribe('selectedVideo', render));
    cleanupFns.push(store.subscribe('currentPath', renderBreadcrumb));

    // Refresh button
    function handleRefresh() { loadFiles(store.get('currentPath')); }
    if (refreshBtn) {
        refreshBtn.addEventListener('click', handleRefresh);
        cleanupFns.push(() => refreshBtn.removeEventListener('click', handleRefresh));
    }

    // Initial load
    loadFiles();

    return {
        destroy() {
            cleanupFns.forEach(fn => fn());
            cleanupFns = [];
        }
    };
}
