/**
 * Event listener management utilities.
 * Provides centralized tracking and cleanup of event listeners.
 */

/**
 * Creates an event listener manager that tracks and can remove all registered listeners.
 * @returns {Object} An event manager with add, remove, and cleanup methods
 */
export function createEventManager() {
    const listeners = new Set();

    /**
     * Add an event listener and track it for cleanup.
     * @param {EventTarget} target - The event target (element, window, etc.)
     * @param {string} type - The event type
     * @param {Function} listener - The event listener function
     * @param {Object|boolean} [options] - Event listener options
     * @returns {Function} A function to remove this specific listener
     */
    function add(target, type, listener, options) {
        target.addEventListener(type, listener, options);
        const removeFn = () => {
            target.removeEventListener(type, listener, options);
            listeners.delete(removeFn);
        };
        listeners.add(removeFn);
        return removeFn;
    }

    /**
     * Remove all tracked event listeners.
     */
    function cleanup() {
        listeners.forEach(remove => remove());
        listeners.clear();
    }

    /**
     * Get the number of tracked listeners.
     * @returns {number} The number of tracked listeners
     */
    function count() {
        return listeners.size;
    }

    return { add, cleanup, count };
}

/**
 * Creates a debounced version of a function.
 * @param {Function} fn - The function to debounce
 * @param {number} delay - The debounce delay in milliseconds
 * @returns {Function} A debounced function
 */
export function debounce(fn, delay = 300) {
    let timeoutId = null;
    return function debounced(...args) {
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            timeoutId = null;
            fn.apply(this, args);
        }, delay);
    };
}

/**
 * Creates a throttled version of a function.
 * @param {Function} fn - The function to throttle
 * @param {number} limit - The minimum time between calls in milliseconds
 * @returns {Function} A throttled function
 */
export function throttle(fn, limit = 100) {
    let inThrottle = false;
    return function throttled(...args) {
        if (!inThrottle) {
            fn.apply(this, args);
            inThrottle = true;
            setTimeout(() => { inThrottle = false; }, limit);
        }
    };
}

/**
 * Adds an event listener that automatically removes itself after being called once.
 * @param {EventTarget} target - The event target
 * @param {string} type - The event type
 * @param {Function} listener - The event listener function
 * @param {Object|boolean} [options] - Event listener options
 */
export function addOnceListener(target, type, listener, options) {
    const wrapper = function onceWrapper(...args) {
        target.removeEventListener(type, wrapper, options);
        listener.apply(this, args);
    };
    target.addEventListener(type, wrapper, options);
}

/**
 * Safely removes an event listener, handling cases where the target may be null.
 * @param {EventTarget|null} target - The event target
 * @param {string} type - The event type
 * @param {Function} listener - The event listener function
 * @param {Object|boolean} [options] - Event listener options
 */
export function safeRemoveListener(target, type, listener, options) {
    if (target) {
        target.removeEventListener(type, listener, options);
    }
}
