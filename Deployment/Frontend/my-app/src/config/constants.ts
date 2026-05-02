export const API_BASE_URL = 'http://127.0.0.1:8001';
export const WS_URL = 'ws://127.0.0.1:8001/ws/signals';

export const RECONNECT_DELAY = 3000;
export const ENABLE_DEBUG = true;

export const PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY'];

export const PAIR_DECIMALS: Record<string, number> = {
  EURUSD: 5,
  GBPUSD: 5,
  USDJPY: 3,
};