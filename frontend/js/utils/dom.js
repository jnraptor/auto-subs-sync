/**
 * DOM manipulation utilities.
 * Provides safe and consistent DOM operations.
 */

/**
 * Safely sets the innerHTML of an element, with optional sanitization.
 * @param {Element} element - The element to update
 * @param {string} html - The HTML string to set
 * @param {boolean} [sanitize=true] - Whether to sanitize the HTML
 */
export function setInnerHTML(element, html, sanitize = true) {
    if (!element) return;
    if (sanitize && typeof html === 'string') {
        // Basic sanitization: remove script tags and event handlers
        const sanitized = html
            .replace(/<script\b[^<]*(?:\s<\/script>|>)/gi, '')
            .replace(/on\w+="[^"]*"/g, '')
            .replace(/on\w+='[^']*'/g, '');
        element.innerHTML = sanitized;
    } else {
        element.innerHTML = html || '';
    }
}

/**
 * Safely sets text content of an element.
 * @param {Element} element - The element to update
 * @param {string} text - The text to set
 */
export function setTextContent(element, text) {
    if (!element) return;
    element.textContent = text ?? '';
}

/**
 * Creates an element with optional attributes and children.
 * @param {string} tagName - The tag name
 * @param {Object} [attributes] - Attributes to set
 * @param {Array|string} [children] - Child elements or text content
 * @returns {Element} The created element
 */
export function createElement(tagName, attributes = {}, children = []) {
    const element = document.createElement(tagName);
    
    for (const [key, value] of Object.entries(attributes)) {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'textContent') {
            element.textContent = value;
        } else if (key === 'innerHTML') {
            setInnerHTML(element, value);
        } else if (key.startsWith('data-')) {
            element.setAttribute(key, value);
        } else if (value !== undefined && value !== null) {
            element.setAttribute(key, value);
        }
    }
    
    if (Array.isArray(children)) {
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Element) {
                element.appendChild(child);
            }
        });
    } else if (typeof children === 'string') {
        element.textContent = children;
    }
    
    return element;
}

/**
 * Safely adds a class to an element.
 * @param {Element} element - The element
 * @param {string} className - The class to add
 */
export function addClass(element, className) {
    if (!element) return;
    element.classList.add(className);
}

/**
 * Safely removes a class from an element.
 * @param {Element} element - The element
 * @param {string} className - The class to remove
 */
export function removeClass(element, className) {
    if (!element) return;
    element.classList.remove(className);
}

/**
 * Safely toggles a class on an element.
 * @param {Element} element - The element
 * @param {string} className - The class to toggle
 * @param {boolean} [force] - Force state (true = add, false = remove)
 */
export function toggleClass(element, className, force) {
    if (!element) return;
    element.classList.toggle(className, force);
}

/**
 * Safely sets an attribute on an element.
 * @param {Element} element - The element
 * @param {string} name - The attribute name
 * @param {string} value - The attribute value
 */
export function setAttribute(element, name, value) {
    if (!element) return;
    if (value === undefined || value === null) {
        element.removeAttribute(name);
    } else {
        element.setAttribute(name, value);
    }
}

/**
 * Safely removes an attribute from an element.
 * @param {Element} element - The element
 * @param {string} name - The attribute name
 */
export function removeAttribute(element, name) {
    if (!element) return;
    element.removeAttribute(name);
}

/**
 * Safely shows an element by removing the 'hidden' class.
 * @param {Element} element - The element to show
 */
export function show(element) {
    if (!element) return;
    element.classList.remove('hidden');
}

/**
 * Safely hides an element by adding the 'hidden' class.
 * @param {Element} element - The element to hide
 */
export function hide(element) {
    if (!element) return;
    element.classList.add('hidden');
}

/**
 * Creates a debounced search input handler.
 * @param {HTMLInputElement} input - The search input element
 * @param {Function} handler - The search handler function
 * @param {number} delay - The debounce delay
 * @returns {Function} Cleanup function
 */
export function setupSearchInput(input, handler, delay = 300) {
    if (!input) return () => {};
    
    let timeoutId = null;
    const cleanup = () => {
        if (timeoutId) clearTimeout(timeoutId);
    };
    
    input.addEventListener('input', (e) => {
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            handler(e.target.value);
        }, delay);
    });
    
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            cleanup();
            input.value = '';
            handler('');
            input.blur();
        }
    });
    
    return cleanup;
}

/**
 * Parses a file size string to bytes.
 * @param {string} sizeStr - The size string (e.g., "1.5 MB")
 * @returns {number} The size in bytes
 */
export function parseFileSize(sizeStr) {
    if (!sizeStr) return 0;
    const match = sizeStr.match(/^([\d.]+)\s*(B|KB|MB|GB)$/i);
    if (!match) return 0;
    
    const value = parseFloat(match[1]);
    const unit = match[2].toUpperCase();
    
    const factors = { B: 1, KB: 1024, MB: 1024 * 1024, GB: 1024 * 1024 * 1024 };
    return Math.round(value * factors[unit]);
}

/**
 * Formats bytes to a human-readable string.
 * @param {number} bytes - The size in bytes
 * @returns {string} The formatted size string
 */
export function formatFileSize(bytes) {
    if (!bytes || bytes <= 0) return '';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}