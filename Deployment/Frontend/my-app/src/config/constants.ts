/**
 * Application constants with environment variable support
 */

const DEFAULT_BACKEND_HOST = 'localhost:8001';
const DEFAULT_BACKEND_PROTOCOL = 'http';

const rawApiUrl = import.meta.env.VITE_API_URL;
const rawWsUrl = import.meta.env.VITE_WS_URL;
const envBackendHost = import.meta.env.VITE_BACKEND_HOST;
const envBackendProtocol = import.meta.env.VITE_BACKEND_PROTOCOL;

let BACKEND_HOST = envBackendHost || DEFAULT_BACKEND_HOST;
let BACKEND_PROTOCOL = envBackendProtocol || DEFAULT_BACKEND_PROTOCOL;

if (rawApiUrl) {
  try {
    const parsed = new URL(rawApiUrl);
    BACKEND_HOST = parsed.host;
    BACKEND_PROTOCOL = parsed.protocol.replace(':', '');
  } catch {
    // Ignore invalid API URL and fallback to explicit host values.
  }
}

const WS_PROTOCOL = BACKEND_PROTOCOL === 'https' ? 'wss' : 'ws';

export const API_BASE_URL = rawApiUrl || `${BACKEND_PROTOCOL}://${BACKEND_HOST}`;
export const WS_URL = rawWsUrl || `${WS_PROTOCOL}://${BACKEND_HOST}/ws/signals`;
export const RECONNECT_DELAY = Number(import.meta.env.VITE_RECONNECT_DELAY) || 3000;
export const ENABLE_DEBUG = import.meta.env.VITE_ENABLE_DEBUG === 'true';

export const PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY'];
export const PAIR_DECIMALS: Record<string, number> = {
  'EURUSD': 5,
  'GBPUSD': 5,
  'USDJPY': 3,
};
