const FILE_ICONS = {
    folder: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>`,
    video: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>`,
    subtitle: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/></svg>`,
    file: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>`
};

const VIDEO_EXTENSIONS = ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v'];
const SUBTITLE_EXTENSIONS = ['srt', 'ass', 'ssa', 'vtt', 'sub'];

function getFileType(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (VIDEO_EXTENSIONS.includes(ext)) return 'video';
    if (SUBTITLE_EXTENSIONS.includes(ext)) return 'subtitle';
    return 'file';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function initFileBrowser(state, api) {
    const browserEl = document.getElementById('file-browser');
    const breadcrumbEl = document.getElementById('breadcrumb');
    const refreshBtn = document.getElementById('refresh-files');

    let currentFiles = [];

    async function loadFiles(path = '') {
        browserEl.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        
        try {
            const data = await api.getFiles(path);
            currentFiles = data.items || [];
            state.setCurrentPath(data.path || path);
            renderFiles();
            renderBreadcrumb();
        } catch (error) {
            browserEl.innerHTML = `<div class="error-message">Failed to load files: ${error.message}</div>`;
        }
    }

    function renderFiles() {
        browserEl.innerHTML = '';
        
        const folders = currentFiles.filter(f => f.file_type === 'directory');
        const videos = currentFiles.filter(f => f.file_type === 'video');
        const others = currentFiles.filter(f => f.file_type !== 'directory' && f.file_type !== 'video');
        
        const sortedFiles = [...folders, ...videos, ...others];
        
        sortedFiles.forEach(file => {
            const item = createFileItem(file);
            browserEl.appendChild(item);
            
            if (file.file_type === 'video' && file.subtitles && file.subtitles.length > 0) {
                file.subtitles.forEach(sub => {
                    const subItem = createFileItem(sub, true);
                    browserEl.appendChild(subItem);
                });
            }
        });
        
        if (sortedFiles.length === 0) {
            browserEl.innerHTML = '<div class="no-selection"><p>No files found</p></div>';
        }
    }

    function createFileItem(file, isSub = false) {
        const item = document.createElement('div');
        const displayType = file.file_type === 'directory' ? 'folder' : (file.file_type || 'file');
        item.className = `file-item ${displayType}${isSub ? ' sub-file' : ''}`;
        
        const icon = FILE_ICONS[displayType] || FILE_ICONS.file;
        const isSelected = state.selectedVideo && state.selectedVideo.path === file.path;
        
        if (isSelected) {
            item.classList.add('selected');
        }
        
        item.innerHTML = `
            <span class="file-icon">${icon}</span>
            <span class="file-name">${file.name}</span>
            ${file.size ? `<span class="file-meta">${formatFileSize(file.size)}</span>` : ''}
        `;
        
        item.addEventListener('click', (e) => handleFileClick(file, e));
        item.addEventListener('dblclick', () => handleFileDoubleClick(file));
        
        return item;
    }

    async function handleFileClick(file, event) {
        if (file.file_type === 'video') {
            state.setSelectedVideo(file);
            state.setSelectedSubtitle(null);
            
            document.querySelectorAll('.file-item').forEach(el => el.classList.remove('selected'));
            event.currentTarget.classList.add('selected');
            
            // Fetch associated subtitles from API
            try {
                const response = await api.getAssociatedSubtitles(file.path);
                const subtitles = response.subtitles || [];
                state.setAssociatedSubtitles(subtitles);
                // Update the file object with subtitles for the event
                const fileWithSubs = { ...file, subtitles };
                window.dispatchEvent(new CustomEvent('videoSelected', { detail: fileWithSubs }));
            } catch (error) {
                console.error('Failed to load associated subtitles:', error);
                state.setAssociatedSubtitles([]);
                window.dispatchEvent(new CustomEvent('videoSelected', { detail: file }));
            }
        } else if (file.file_type === 'directory') {
            // Single click just selects, double click navigates
        }
    }

    function handleFileDoubleClick(file) {
        if (file.file_type === 'directory') {
            const newPath = state.currentPath ? `${state.currentPath}/${file.name}` : file.name;
            loadFiles(newPath);
        }
    }

    function renderBreadcrumb() {
        const parts = state.currentPath.split('/').filter(Boolean);
        let html = `<span class="breadcrumb-item" data-path="">Home</span>`;
        
        let cumulativePath = '';
        parts.forEach((part, index) => {
            cumulativePath = cumulativePath ? `${cumulativePath}/${part}` : part;
            html += `<span class="breadcrumb-separator">/</span>`;
            html += `<span class="breadcrumb-item" data-path="${cumulativePath}">${part}</span>`;
        });
        
        breadcrumbEl.innerHTML = html;
        
        breadcrumbEl.querySelectorAll('.breadcrumb-item').forEach(el => {
            el.addEventListener('click', () => {
                loadFiles(el.dataset.path);
            });
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadFiles(state.currentPath));
    }

    loadFiles();

    return {
        loadFiles,
        refresh: () => loadFiles(state.currentPath),
        getCurrentFiles: () => currentFiles
    };
}