/**
 * Application constants with environment variable support
 */

export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:5001/ws/signals';
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
export const RECONNECT_DELAY = Number(import.meta.env.VITE_RECONNECT_DELAY) || 3000;
export const ENABLE_DEBUG = import.meta.env.VITE_ENABLE_DEBUG === 'true';
