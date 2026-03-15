export function createToast() {
    const container = document.getElementById('toast-container');
    const MAX_TOASTS = 5;

    function show(message, type, duration) {
        // Enforce max toast limit
        while (container.children.length >= MAX_TOASTS) {
            container.removeChild(container.firstChild);
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');

        const text = document.createElement('span');
        text.className = 'toast-message';
        text.textContent = message;

        const closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.setAttribute('aria-label', 'Dismiss notification');
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', () => dismiss(toast));

        toast.appendChild(text);
        toast.appendChild(closeBtn);
        container.appendChild(toast);

        // Trigger slide-in animation
        requestAnimationFrame(() => toast.classList.add('toast-visible'));

        const timerId = setTimeout(() => dismiss(toast), duration);
        toast._timerId = timerId;
    }

    function dismiss(toast) {
        if (!toast.parentNode) return;
        clearTimeout(toast._timerId);
        toast.classList.remove('toast-visible');
        toast.classList.add('toast-hiding');
        toast.addEventListener('animationend', () => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, { once: true });
    }

    function success(message, duration = 4000) { show(message, 'success', duration); }
    function error(message, duration = 8000) { show(message, 'error', duration); }
    function warning(message, duration = 6000) { show(message, 'warning', duration); }
    function info(message, duration = 4000) { show(message, 'info', duration); }

    function destroy() {
        while (container.firstChild) container.removeChild(container.firstChild);
    }

    return { success, error, warning, info, destroy };
}
