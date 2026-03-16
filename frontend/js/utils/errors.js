/**
 * Error handling utilities.
 * Provides consistent error handling and recovery patterns.
 */

/**
 * Error types for classification.
 */
export const ErrorType = {
    NETWORK: 'network',
    TIMEOUT: 'timeout',
    API: 'api',
    VALIDATION: 'validation',
    UNKNOWN: 'unknown',
};

/**
 * Classifies an error into a known error type.
 * @param {Error|Object} error - The error to classify
 * @returns {string} The error type
 */
export function classifyError(error) {
    if (!error) return ErrorType.UNKNOWN;
    
    if (error.name === 'AbortError') return ErrorType.TIMEOUT;
    if (error.constructor.name === 'ApiError') return ErrorType.API;
    if (error.message?.includes('network') || error.message?.includes('fetch')) return ErrorType.NETWORK;
    if (error.message?.includes('timeout')) return ErrorType.TIMEOUT;
    
    return ErrorType.UNKNOWN;
}

/**
 * Creates a user-friendly error message.
 * @param {Error|Object} error - The error
 * @returns {string} The user-friendly message
 */
export function getErrorMessage(error) {
    if (!error) return 'An unknown error occurred';
    
    if (error.constructor.name === 'ApiError') {
        return error.message || 'API request failed';
    }
    
    switch (classifyError(error)) {
        case ErrorType.TIMEOUT:
            return 'Request timed out. Please try again.';
        case ErrorType.NETWORK:
            return 'Network error. Please check your connection.';
        case ErrorType.API:
            return error.message || 'Server error occurred';
        default:
            return error.message || 'An unexpected error occurred';
    }
}

/**
 * Logs an error with context for debugging.
 * @param {Error|Object} error - The error
 * @param {string} [context] - Optional context about where the error occurred
 */
export function logError(error, context) {
    const errorType = classifyError(error);
    const message = getErrorMessage(error);
    
    console.error(`[Error: ${errorType}] ${context || 'Unknown context'}: ${message}`, error);
}

/**
 * Handles an error with optional retry logic.
 * @param {Error|Object} error - The error
 * @param {Function} [retryFn] - Optional function to retry
 * @param {number} [maxRetries=3] - Maximum retry attempts
 * @returns {Promise<boolean>} Whether the error was handled successfully
 */
export async function handleError(error, retryFn, maxRetries = 3) {
    logError(error, 'handleError');
    
    if (!retryFn) {
        return false;
    }
    
    const errorType = classifyError(error);
    
    // Only retry network and timeout errors
    if (errorType !== ErrorType.NETWORK && errorType !== ErrorType.TIMEOUT) {
        return false;
    }
    
    let attempts = 0;
    while (attempts < maxRetries) {
        attempts++;
        try {
            await retryFn();
            return true;
        } catch (retryError) {
            logError(retryError, `Retry attempt ${attempts}`);
        }
    }
    
    return false;
}

/**
 * Creates an error handler with automatic retry and exponential backoff.
 * @param {Function} operation - The operation to execute
 * @param {Function} [onError] - Optional error callback
 * @param {number} [maxRetries=3] - Maximum retry attempts
 * @param {number} [baseDelay=1000] - Base delay between retries in ms
 * @returns {Promise<any>} The result of the operation
 */
export async function withRetry(operation, onError, maxRetries = 3, baseDelay = 1000) {
    let attempts = 0;
    
    while (attempts < maxRetries) {
        try {
            return await operation();
        } catch (error) {
            attempts++;
            logError(error, `Attempt ${attempts}/${maxRetries}`);
            
            if (attempts >= maxRetries) {
                if (onError) onError(error);
                throw error;
            }
            
            // Exponential backoff with jitter
            const delay = baseDelay * Math.pow(2, attempts - 1) + Math.random() * 500;
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}

/**
 * Wraps a function to handle errors gracefully.
 * @param {Function} fn - The function to wrap
 * @param {Function} [fallback] - Optional fallback function on error
 * @returns {Function} The wrapped function
 */
export function wrapErrorHandler(fn, fallback) {
    return async function wrapped(...args) {
        try {
            return await fn.apply(this, args);
        } catch (error) {
            logError(error, fn.name || 'anonymous');
            if (fallback) {
                return fallback.apply(this, [error, ...args]);
            }
            throw error;
        }
    };
}

/**
 * Validates that a value is not null or undefined.
 * @param {any} value - The value to validate
 * @param {string} name - The name of the value for error messages
 * @throws {Error} If value is null or undefined
 */
export function validateRequired(value, name) {
    if (value === null || value === undefined) {
        const error = new Error(`${name} is required`);
        error.type = ErrorType.VALIDATION;
        throw error;
    }
}

/**
 * Validates that a string is a valid path.
 * @param {string} path - The path to validate
 * @returns {boolean} Whether the path is valid
 */
export function isValidPath(path) {
    if (path === null || typeof path !== 'string') return false;
    // Basic validation: no null bytes, no excessive length
    if (path.includes('\0')) return false;
    if (path.length > 1000) return false;
    return true;
}

/**
 * Sanitizes a path string.
 * @param {string} path - The path to sanitize
 * @returns {string} The sanitized path
 */
export function sanitizePath(path) {
    if (!path) return '';
    // Remove null bytes and trim whitespace
    return path.replace(/\0/g, '').trim();
}