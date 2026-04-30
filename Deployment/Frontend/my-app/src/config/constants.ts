/**
 * Application constants with environment variable support
 */

const BACKEND_HOST = import.meta.env.VITE_BACKEND_HOST || 'localhost:5001';
const BACKEND_PROTOCOL = import.meta.env.VITE_BACKEND_PROTOCOL || 'http';
const WS_PROTOCOL = BACKEND_PROTOCOL === 'https' ? 'wss' : 'ws';

export const API_BASE_URL = `${BACKEND_PROTOCOL}://${BACKEND_HOST}`;
export const WS_URL = `${WS_PROTOCOL}://${BACKEND_HOST}/ws/signals`;
export const RECONNECT_DELAY = Number(import.meta.env.VITE_RECONNECT_DELAY) || 3000;
export const ENABLE_DEBUG = import.meta.env.VITE_ENABLE_DEBUG === 'true';

export const PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY'];
export const PAIR_DECIMALS: Record<string, number> = {
  'EURUSD': 5,
  'GBPUSD': 5,
  'USDJPY': 3,
};
